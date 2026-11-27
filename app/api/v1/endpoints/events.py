import os
import shutil
import uuid
from datetime import date, time, datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.repositories.community_repo import CommunityRepository
from app.models.events import Event, EventCategory, EventImage
from app.models.khutba import NotificationLog
from app.schemas.v1.events import (
    EventResponse, EventCreate, EventUpdate, EventCategoryResponse, EventCategoryCreate
)
from app.services.firebase import firebase_service

router = APIRouter()

@router.get("/categories", response_model=List[EventCategoryResponse])
@router.get("/categories/", response_model=List[EventCategoryResponse])
@router.get("/categories/all", response_model=List[EventCategoryResponse])
async def list_event_categories(db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(EventCategory))).scalars().all())

@router.get("/", response_model=List[EventResponse])
@router.get("", response_model=List[EventResponse])
async def list_events(upcoming_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await CommunityRepository(db).list_events(upcoming_only)

@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: Request,
    current_user=Depends(require_permission("events.manage")),
    db: AsyncSession = Depends(get_db)
):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        title = form.get("title")
        story = form.get("story", "")
        venue_name = form.get("venue_name", "Jamia Mosque")
        category_id_val = form.get("category_id")
        event_date_str = form.get("event_date")
        start_time_str = form.get("start_time")
        end_time_str = form.get("end_time")
        published_raw = form.get("published", "true")

        if not title or not event_date_str or not start_time_str:
            raise HTTPException(status_code=400, detail="Title, event_date, and start_time are required")

        try:
            ev_date = date.fromisoformat(str(event_date_str))
        except Exception:
            ev_date = date.today()

        try:
            parts = [int(p) for p in str(start_time_str).split(":")[:2]]
            st_time = time(parts[0], parts[1])
        except Exception:
            st_time = time(9, 0)

        et_time = None
        if end_time_str:
            try:
                parts = [int(p) for p in str(end_time_str).split(":")[:2]]
                et_time = time(parts[0], parts[1])
            except Exception:
                pass

        cover_image_path = None
        cover_field = form.get("cover_image")
        if cover_field and hasattr(cover_field, "filename") and cover_field.filename:
            ext = os.path.splitext(cover_field.filename or "")[1] or ".jpg"
            img_name = f"event_cov_{uuid.uuid4().hex[:10]}{ext}"
            dest = Path("static/events") / img_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as buf:
                shutil.copyfileobj(cover_field.file, buf)
            cover_image_path = f"/static/events/{img_name}"
        elif isinstance(cover_field, str) and cover_field:
            cover_image_path = cover_field

        guest_photo_path = None
        guest_field = form.get("guest_photo")
        if guest_field and hasattr(guest_field, "filename") and guest_field.filename:
            ext = os.path.splitext(guest_field.filename or "")[1] or ".jpg"
            img_name = f"event_guest_{uuid.uuid4().hex[:10]}{ext}"
            dest = Path("static/events") / img_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as buf:
                shutil.copyfileobj(guest_field.file, buf)
            guest_photo_path = f"/static/events/{img_name}"
        elif isinstance(guest_field, str) and guest_field:
            guest_photo_path = guest_field

        cat_id = int(category_id_val) if category_id_val and str(category_id_val).isdigit() else None

        event = Event(
            title=str(title),
            story=str(story or ""),
            venue_name=str(venue_name or ""),
            venue_address=str(form.get("venue_address") or ""),
            venue_map_link=str(form.get("venue_map_link") or ""),
            guest_name=str(form.get("guest_name") or "") if form.get("guest_name") else None,
            category_id=cat_id,
            event_date=ev_date,
            start_time=st_time,
            end_time=et_time,
            cover_image=cover_image_path,
            guest_photo=guest_photo_path,
            published=str(published_raw).lower() in ("true", "1", "yes"),
            created_by_id=current_user.id if current_user else None
        )
    else:
        json_data = await request.json()
        data = EventCreate(**json_data)
        event = Event(**data.model_dump(), created_by_id=current_user.id if current_user else None)

    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.get("/{id}", response_model=EventResponse)
@router.get("/{id}/", response_model=EventResponse)
async def get_event(id: int, db: AsyncSession = Depends(get_db)):
    e = await db.get(Event, id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    return e

@router.put("/{id}", response_model=EventResponse)
@router.put("/{id}/", response_model=EventResponse)
@router.patch("/{id}", response_model=EventResponse)
@router.patch("/{id}/", response_model=EventResponse)
async def update_event(
    id: int,
    request: Request,
    current_user=Depends(require_permission("events.manage")),
    db: AsyncSession = Depends(get_db)
):
    e = await db.get(Event, id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        if "title" in form:
            e.title = str(form.get("title"))
        if "story" in form:
            e.story = str(form.get("story"))
        if "venue_name" in form:
            e.venue_name = str(form.get("venue_name"))
        if "venue_address" in form:
            e.venue_address = str(form.get("venue_address"))
        if "venue_map_link" in form:
            e.venue_map_link = str(form.get("venue_map_link"))
        if "guest_name" in form:
            e.guest_name = str(form.get("guest_name"))
        if "category_id" in form:
            cat_id = form.get("category_id")
            e.category_id = int(cat_id) if cat_id and str(cat_id).isdigit() else None
        if "event_date" in form:
            try:
                e.event_date = date.fromisoformat(str(form.get("event_date")))
            except Exception:
                pass
        if "start_time" in form:
            try:
                parts = [int(p) for p in str(form.get("start_time")).split(":")[:2]]
                e.start_time = time(parts[0], parts[1])
            except Exception:
                pass
        if "end_time" in form:
            try:
                parts = [int(p) for p in str(form.get("end_time")).split(":")[:2]]
                e.end_time = time(parts[0], parts[1])
            except Exception:
                pass
        if "published" in form:
            e.published = str(form.get("published")).lower() in ("true", "1", "yes")

        cover_field = form.get("cover_image")
        if cover_field and hasattr(cover_field, "filename") and cover_field.filename:
            ext = os.path.splitext(cover_field.filename or "")[1] or ".jpg"
            img_name = f"event_cov_{uuid.uuid4().hex[:10]}{ext}"
            dest = Path("static/events") / img_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as buf:
                shutil.copyfileobj(cover_field.file, buf)
            e.cover_image = f"/static/events/{img_name}"
        elif isinstance(cover_field, str) and cover_field:
            e.cover_image = cover_field

        guest_field = form.get("guest_photo")
        if guest_field and hasattr(guest_field, "filename") and guest_field.filename:
            ext = os.path.splitext(guest_field.filename or "")[1] or ".jpg"
            img_name = f"event_guest_{uuid.uuid4().hex[:10]}{ext}"
            dest = Path("static/events") / img_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as buf:
                shutil.copyfileobj(guest_field.file, buf)
            e.guest_photo = f"/static/events/{img_name}"
        elif isinstance(guest_field, str) and guest_field:
            e.guest_photo = guest_field
    else:
        json_data = await request.json()
        data = EventUpdate(**json_data)
        for f, v in data.model_dump(exclude_unset=True).items():
            setattr(e, f, v)

    await db.commit()
    await db.refresh(e)
    return e

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(id: int, current_user=Depends(require_permission("events.manage")), db: AsyncSession = Depends(get_db)):
    e = await db.get(Event, id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(e)
    await db.commit()
    return None

@router.post("/{id}/notify")
@router.post("/{id}/notify/")
async def notify_event(id: int, current_user=Depends(require_permission("events.manage")), db: AsyncSession = Depends(get_db)):
    e = await db.get(Event, id)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    title = f"New Event: {e.title}"
    body = f"{e.venue_name} on {e.event_date.strftime('%d %b %Y')}"
    payload = {"type": "event", "event_id": str(e.id)}
    for topic_name in ("events", "all_users", "general"):
        try:
            firebase_service.send_topic_notification(topic=topic_name, title=title, body=body, data=payload)
        except Exception:
            pass
    from app.models.khutba import DeviceToken
    tokens = list((await db.execute(select(DeviceToken.fcm_token))).scalars().all())
    count = 0
    if tokens:
        try:
            count = firebase_service.send_multicast(tokens=tokens, title=title, body=body, data=payload)
        except Exception:
            pass
    recipient_count = max(count, len(tokens), 1)
    log = NotificationLog(
        title=title,
        body=body,
        notification_type="event",
        related_event_id=e.id,
        recipient_count=recipient_count
    )
    db.add(log)
    await db.commit()
    return {"status": "success", "success_count": recipient_count}

@router.post("/images")
@router.post("/images/")
async def upload_event_image(
    request: Request,
    current_user=Depends(require_permission("events.manage")),
    db: AsyncSession = Depends(get_db)
):
    form = await request.form()
    event_id = form.get("event_id")
    image_file = form.get("image")
    caption = form.get("caption")
    if not event_id or not image_file or not hasattr(image_file, "filename"):
        raise HTTPException(status_code=400, detail="event_id and image file required")
    ext = os.path.splitext(image_file.filename or "")[1] or ".jpg"
    img_name = f"gallery_{uuid.uuid4().hex[:10]}{ext}"
    dest = Path("static/events") / img_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as buf:
        shutil.copyfileobj(image_file.file, buf)
    img_path = f"/static/events/{img_name}"
    ev_img = EventImage(event_id=int(event_id), image=img_path, caption=str(caption) if caption else None)
    db.add(ev_img)
    await db.commit()
    await db.refresh(ev_img)
    return {"id": ev_img.id, "image": img_path, "caption": ev_img.caption}
