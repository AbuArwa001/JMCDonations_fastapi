import os, uuid, shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_active_user
from app.services.user_service import get_user_response
from app.models.users import User, UserNotificationState
from app.schemas.v1.users import UserResponse, UserUpdate, NotificationStateResponse, NotificationStateUpdate

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    return await get_user_response(db, current_user)

@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(user_in: UserUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    for field, val in user_in.model_dump(exclude_unset=True).items():
        setattr(current_user, field, val)
    await db.commit()
    return await get_user_response(db, current_user)

@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(file: UploadFile = File(...), current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1] or ".png"
    name = f"{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    dest = Path("static/avatars") / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    current_user.profile_image_url = f"/static/avatars/{name}"
    await db.commit()
    return await get_user_response(db, current_user)

@router.get("/me/notifications", response_model=NotificationStateResponse)
async def get_user_notifications(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    st = await db.get(UserNotificationState, current_user.id)
    return NotificationStateResponse(deleted_ids=st.deleted_ids if st else [], read_ids=st.read_ids if st else [])

@router.patch("/me/notifications", response_model=NotificationStateResponse)
async def update_user_notifications(req: NotificationStateUpdate, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    st = await db.get(UserNotificationState, current_user.id)
    if not st:
        st = UserNotificationState(user_id=current_user.id, read_ids=req.notification_ids, deleted_ids=[])
        db.add(st)
    else:
        st.read_ids = list(set((st.read_ids or []) + req.notification_ids))
    await db.commit()
    return NotificationStateResponse(deleted_ids=st.deleted_ids or [], read_ids=st.read_ids or [])

