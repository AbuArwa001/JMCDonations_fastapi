import re
import uuid
from datetime import date, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.events import Event, EventCategory, EventImage
from app.models.khutba import NotificationLog
from app.models.users import User
from app.schemas.content import (
    EventCreate, EventUpdate, EventResponse,
    EventCategoryCreate, EventCategoryUpdate, EventCategoryResponse,
    EventImageCreate, EventImageResponse
)
from app.api.dependencies.auth import get_current_admin_user
from app.services.firebase import firebase_service
from app.services.aws import upload_file_to_s3

router = APIRouter()


def _send_event_fcm(event: Event) -> None:
    """Broadcast FCM notification for an Event to all JamiaGive users."""
    title = f"Upcoming Event: {event.title}"
    body = f"{event.venue_name} on {event.event_date}. Tap for details."
    data = {
        "type": "event",
        "event_id": str(event.id),
        "title": str(event.title),
        "event_date": str(event.event_date),
    }
    image_url = event.cover_image
    firebase_service.send_topic_notification("all_users", title, body, data=data, image_url=image_url)
    firebase_service.send_topic_notification("events", title, body, data=data, image_url=image_url)

def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    return re.sub(r'[\s_-]+', '-', s)

# ==================== Event Categories ====================

@router.get("/categories", response_model=List[EventCategoryResponse])
async def list_event_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EventCategory).order_by(EventCategory.name))
    return result.scalars().all()

@router.post("/categories", response_model=EventCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_event_category(
    cat_in: EventCategoryCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    base_slug = cat_in.slug or slugify(cat_in.name)
    slug = base_slug
    counter = 1
    while True:
        existing = await db.execute(select(EventCategory).filter(EventCategory.slug == slug))
        if not existing.scalars().first():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    db_cat = EventCategory(name=cat_in.name, slug=slug)
    db.add(db_cat)
    await db.commit()
    await db.refresh(db_cat)
    return db_cat

@router.get("/categories/{category_id}", response_model=EventCategoryResponse)
async def get_event_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EventCategory).filter(EventCategory.id == category_id))
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event category not found")
    return cat

@router.patch("/categories/{category_id}", response_model=EventCategoryResponse)
@router.put("/categories/{category_id}", response_model=EventCategoryResponse)
async def update_event_category(
    category_id: int,
    cat_in: EventCategoryUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(EventCategory).filter(EventCategory.id == category_id))
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event category not found")

    update_data = cat_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cat, field, value)

    await db.commit()
    await db.refresh(cat)
    return cat

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_category(
    category_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(EventCategory).filter(EventCategory.id == category_id))
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event category not found")

    await db.delete(cat)
    await db.commit()

# ==================== Events ====================

@router.get("/", response_model=List[EventResponse])
async def list_events(
    category_id: Optional[int] = None,
    published_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    query = select(Event).options(selectinload(Event.gallery_images))
    if category_id is not None:
        query = query.filter(Event.category_id == category_id)
    if published_only:
        query = query.filter(Event.published == True)
    query = query.order_by(Event.event_date.desc(), Event.start_time.desc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    title: str = Form(...),
    story: str = Form(...),
    event_date: date = Form(...),
    start_time: time = Form(...),
    venue_name: str = Form(...),
    category_id: Optional[int] = Form(None),
    end_time: Optional[time] = Form(None),
    venue_address: Optional[str] = Form(None),
    venue_map_link: Optional[str] = Form(None),
    guest_name: Optional[str] = Form(None),
    published: bool = Form(True),
    cover_image: Optional[UploadFile] = File(None),
    guest_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    cover_image_url = None
    if cover_image:
        cover_object_name = f"events/cover_{uuid.uuid4().hex}_{cover_image.filename}"
        try:
            cover_image_url = upload_file_to_s3(cover_image.file, cover_object_name, content_type=cover_image.content_type)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload cover image: {str(e)}")

    guest_photo_url = None
    if guest_photo:
        guest_object_name = f"events/guest_{uuid.uuid4().hex}_{guest_photo.filename}"
        try:
            guest_photo_url = upload_file_to_s3(guest_photo.file, guest_object_name, content_type=guest_photo.content_type)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload guest photo: {str(e)}")

    db_event = Event(
        title=title,
        story=story,
        event_date=event_date,
        start_time=start_time,
        venue_name=venue_name,
        category_id=category_id,
        end_time=end_time,
        venue_address=venue_address,
        venue_map_link=venue_map_link,
        guest_name=guest_name,
        published=published,
        cover_image=cover_image_url,
        guest_photo=guest_photo_url,
        created_by_id=current_user.id
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    # Reload with relations
    res = await db.execute(select(Event).options(selectinload(Event.gallery_images)).filter(Event.id == db_event.id))
    db_event = res.scalars().first()

    # Auto-broadcast to JamiaGive users on creation
    if db_event and db_event.published:
        _send_event_fcm(db_event)
        log = NotificationLog(
            title=f"Upcoming Event: {db_event.title}",
            body=f"{db_event.venue_name} on {db_event.event_date}",
            image_url=db_event.cover_image,
            notification_type="event",
            related_event_id=db_event.id,
            recipient_count=1,
        )
        db.add(log)
        await db.commit()

    return db_event

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Event).options(selectinload(Event.gallery_images)).filter(Event.id == event_id)
    )
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event

@router.patch("/{event_id}", response_model=EventResponse)
@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    title: Optional[str] = Form(None),
    story: Optional[str] = Form(None),
    event_date: Optional[date] = Form(None),
    start_time: Optional[time] = Form(None),
    venue_name: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    end_time: Optional[time] = Form(None),
    venue_address: Optional[str] = Form(None),
    venue_map_link: Optional[str] = Form(None),
    guest_name: Optional[str] = Form(None),
    published: Optional[bool] = Form(None),
    cover_image: Optional[UploadFile] = File(None),
    guest_photo: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Event).options(selectinload(Event.gallery_images)).filter(Event.id == event_id)
    )
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    update_data = {}
    if title is not None: update_data['title'] = title
    if story is not None: update_data['story'] = story
    if event_date is not None: update_data['event_date'] = event_date
    if start_time is not None: update_data['start_time'] = start_time
    if venue_name is not None: update_data['venue_name'] = venue_name
    if category_id is not None: update_data['category_id'] = category_id
    if end_time is not None: update_data['end_time'] = end_time
    if venue_address is not None: update_data['venue_address'] = venue_address
    if venue_map_link is not None: update_data['venue_map_link'] = venue_map_link
    if guest_name is not None: update_data['guest_name'] = guest_name
    if published is not None: update_data['published'] = published

    if cover_image:
        cover_object_name = f"events/cover_{uuid.uuid4().hex}_{cover_image.filename}"
        try:
            update_data['cover_image'] = upload_file_to_s3(cover_image.file, cover_object_name, content_type=cover_image.content_type)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload cover image: {str(e)}")

    if guest_photo:
        guest_object_name = f"events/guest_{uuid.uuid4().hex}_{guest_photo.filename}"
        try:
            update_data['guest_photo'] = upload_file_to_s3(guest_photo.file, guest_object_name, content_type=guest_photo.content_type)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload guest photo: {str(e)}")

    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).filter(Event.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await db.delete(event)
    await db.commit()

@router.post("/{event_id}/notify")
async def notify_event(
    event_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually broadcast a push notification for an event to all JamiaGive users."""
    result = await db.execute(select(Event).filter(Event.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    _send_event_fcm(event)

    log = NotificationLog(
        title=f"Upcoming Event: {event.title}",
        body=f"{event.venue_name} on {event.event_date}",
        image_url=event.cover_image,
        notification_type="event",
        related_event_id=event.id,
        recipient_count=1,
    )
    db.add(log)
    await db.commit()

    return {"status": "success", "message": "Notification broadcast initiated", "event_id": event_id}

# ==================== Gallery Images ====================

@router.post("/images", response_model=EventImageResponse, status_code=status.HTTP_201_CREATED)
async def add_event_image(
    image_in: EventImageCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_img = EventImage(**image_in.model_dump())
    db.add(db_img)
    await db.commit()
    await db.refresh(db_img)
    return db_img

@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_image(
    image_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(EventImage).filter(EventImage.id == image_id))
    img = res.scalars().first()
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    await db.delete(img)
    await db.commit()
