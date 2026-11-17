from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
import uuid

from app.db.session import get_db
from app.models.users import User, UserPaymentAccount, UserNotificationState
from app.models.transactions import Transaction
from app.schemas.users import (
    UserResponse, UserUpdate,
    UserPaymentAccountCreate, UserPaymentAccountUpdate, UserPaymentAccountResponse,
    NotificationStateResponse, NotificationStateUpdate, NotificationSyncRequest
)
from app.api.dependencies.auth import require_permission, get_current_active_user, get_current_admin_user
from app.services.user_service import get_user_response

router = APIRouter()

# ==================== User Profile ====================

@router.get("/me", response_model=UserResponse)
async def read_user_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current logged in user details with dynamically calculated donation metrics.
    """
    return await get_user_response(db, current_user)

@router.patch("/me", response_model=UserResponse)
@router.put("/me", response_model=UserResponse)
async def update_user_me(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update profile details of current user.
    Accepts both JSON and Multipart Form Data (with optional profile_image file).
    """
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        profile_file = form.get("profile_image")
        if profile_file and hasattr(profile_file, "read"):
            upload_dir = Path("static/avatars")
            upload_dir.mkdir(parents=True, exist_ok=True)
            ext = "jpg"
            if hasattr(profile_file, "filename") and profile_file.filename and "." in profile_file.filename:
                ext = profile_file.filename.split(".")[-1]
            filename = f"{current_user.id}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
            dest_path = upload_dir / filename
            content = await profile_file.read()
            with open(dest_path, "wb") as f:
                f.write(content)
            current_user.profile_image_url = f"/static/avatars/{filename}"

        allowed_fields = [
            "full_name", "phone_number", "bio", "address",
            "default_donation_account", "profile_image_url", "fcm_token"
        ]
        for key in allowed_fields:
            if key in form and form[key]:
                setattr(current_user, key, form[key])
    else:
        try:
            body = await request.json()
            user_update = UserUpdate.model_validate(body)
            update_data = user_update.model_dump(exclude_unset=True)
            if "email" in update_data and update_data["email"]:
                new_email = str(update_data["email"]).strip().lower()
                if new_email != current_user.email:
                    email_check = await db.execute(
                        select(User).filter(User.email == new_email, User.id != current_user.id)
                    )
                    if email_check.scalars().first():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email is already registered to another account"
                        )
                    current_user.email = new_email
                    if current_user.firebase_uid:
                        try:
                            from firebase_admin import auth as fb_auth
                            fb_auth.update_user(current_user.firebase_uid, email=new_email)
                        except Exception as fb_err:
                            pass
            for field, value in update_data.items():
                if field != "email":
                    setattr(current_user, field, value)
        except HTTPException:
            raise
        except Exception:
            pass
        
    await db.commit()
    await db.refresh(current_user)
    return await get_user_response(db, current_user)

# ==================== User Notifications State ====================

@router.get("/me/notifications/state", response_model=NotificationStateResponse)
async def get_my_notification_state(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get lists of deleted and read notification IDs for current user across all devices.
    """
    res = await db.execute(
        select(UserNotificationState).filter(UserNotificationState.user_id == current_user.id)
    )
    rows = res.scalars().all()
    deleted_ids = [r.notification_id for r in rows if r.is_deleted]
    read_ids = [r.notification_id for r in rows if r.is_read and not r.is_deleted]
    return NotificationStateResponse(deleted_ids=deleted_ids, read_ids=read_ids)

@router.post("/me/notifications/delete")
async def mark_notifications_deleted(
    payload: NotificationStateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark one or more notifications as deleted for current user permanently.
    """
    for nid in payload.notification_ids:
        nid_str = str(nid).strip()
        if not nid_str:
            continue
        res = await db.execute(
            select(UserNotificationState).filter(
                UserNotificationState.user_id == current_user.id,
                UserNotificationState.notification_id == nid_str
            )
        )
        state = res.scalars().first()
        if state:
            state.is_deleted = True
            state.is_read = True
        else:
            db.add(UserNotificationState(
                user_id=current_user.id,
                notification_id=nid_str,
                is_deleted=True,
                is_read=True
            ))
    await db.commit()
    return {"status": "success", "count": len(payload.notification_ids)}

@router.post("/me/notifications/read")
async def mark_notifications_read(
    payload: NotificationStateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark one or more notifications as read for current user.
    """
    for nid in payload.notification_ids:
        nid_str = str(nid).strip()
        if not nid_str:
            continue
        res = await db.execute(
            select(UserNotificationState).filter(
                UserNotificationState.user_id == current_user.id,
                UserNotificationState.notification_id == nid_str
            )
        )
        state = res.scalars().first()
        if state:
            state.is_read = True
        else:
            db.add(UserNotificationState(
                user_id=current_user.id,
                notification_id=nid_str,
                is_read=True,
                is_deleted=False
            ))
    await db.commit()
    return {"status": "success", "count": len(payload.notification_ids)}

@router.post("/me/notifications/sync", response_model=NotificationStateResponse)
async def sync_notifications_state(
    payload: NotificationSyncRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bi-directionally sync read and deleted notifications state.
    Merges client state into server, and returns unified state.
    """
    res = await db.execute(
        select(UserNotificationState).filter(UserNotificationState.user_id == current_user.id)
    )
    existing = {r.notification_id: r for r in res.scalars().all()}

    for nid in payload.deleted_ids:
        nid_str = str(nid).strip()
        if not nid_str:
            continue
        if nid_str in existing:
            existing[nid_str].is_deleted = True
            existing[nid_str].is_read = True
        else:
            obj = UserNotificationState(
                user_id=current_user.id,
                notification_id=nid_str,
                is_deleted=True,
                is_read=True
            )
            db.add(obj)
            existing[nid_str] = obj

    for nid in payload.read_ids:
        nid_str = str(nid).strip()
        if not nid_str:
            continue
        if nid_str in existing:
            existing[nid_str].is_read = True
        else:
            obj = UserNotificationState(
                user_id=current_user.id,
                notification_id=nid_str,
                is_read=True,
                is_deleted=False
            )
            db.add(obj)
            existing[nid_str] = obj

    await db.commit()

    all_deleted = [nid for nid, obj in existing.items() if obj.is_deleted]
    all_read = [nid for nid, obj in existing.items() if obj.is_read and not obj.is_deleted]
    return NotificationStateResponse(deleted_ids=all_deleted, read_ids=all_read)

@router.post("/me/notifications/clear-all")
@router.delete("/me/notifications/clear-all")
async def clear_all_notifications(
    payload: Optional[NotificationStateUpdate] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all current transactions and any specified notifications for this user as deleted.
    """
    res = await db.execute(
        select(Transaction.id).filter(Transaction.user_id == current_user.id)
    )
    tx_ids = set(str(r[0]) for r in res.all())
    if payload and payload.notification_ids:
        tx_ids.update(str(nid).strip() for nid in payload.notification_ids if str(nid).strip())

    res_states = await db.execute(
        select(UserNotificationState).filter(UserNotificationState.user_id == current_user.id)
    )
    existing = {r.notification_id: r for r in res_states.scalars().all()}

    for nid in tx_ids:
        if nid in existing:
            existing[nid].is_deleted = True
            existing[nid].is_read = True
        else:
            db.add(UserNotificationState(
                user_id=current_user.id,
                notification_id=nid,
                is_deleted=True,
                is_read=True
            ))
    await db.commit()
    return {"status": "success", "cleared_count": len(tx_ids)}

@router.post("/avatar", response_model=UserResponse)
@router.post("/me/avatar", response_model=UserResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and set avatar for the currently authenticated user.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image (JPEG, PNG, WebP)"
        )

    upload_dir = Path("static/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{current_user.id}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
    dest_path = upload_dir / filename

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    current_user.profile_image_url = f"/static/avatars/{filename}"
    await db.commit()
    await db.refresh(current_user)
    return await get_user_response(db, current_user)


# ==================== User Payment Accounts ====================

@router.get("/payment-accounts", response_model=List[UserPaymentAccountResponse])
async def list_my_payment_accounts(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all payment accounts belonging to the authenticated user.
    """
    result = await db.execute(
        select(UserPaymentAccount)
        .filter(UserPaymentAccount.user_id == current_user.id)
        .order_by(UserPaymentAccount.created_at.desc())
    )
    return result.scalars().all()

@router.post("/payment-accounts", response_model=UserPaymentAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_account(
    acc_in: UserPaymentAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new payment account (M-Pesa, Card, Bank) for current user.
    """
    db_acc = UserPaymentAccount(
        **acc_in.model_dump(),
        user_id=current_user.id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(db_acc)
    await db.commit()
    await db.refresh(db_acc)
    return db_acc

@router.get("/payment-accounts/{account_id}", response_model=UserPaymentAccountResponse)
async def get_payment_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserPaymentAccount).filter(
            UserPaymentAccount.id == account_id,
            UserPaymentAccount.user_id == current_user.id
        )
    )
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment account not found")
    return acc

@router.patch("/payment-accounts/{account_id}", response_model=UserPaymentAccountResponse)
@router.put("/payment-accounts/{account_id}", response_model=UserPaymentAccountResponse)
async def update_payment_account(
    account_id: uuid.UUID,
    acc_in: UserPaymentAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserPaymentAccount).filter(
            UserPaymentAccount.id == account_id,
            UserPaymentAccount.user_id == current_user.id
        )
    )
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment account not found")

    update_data = acc_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(acc, field, value)

    acc.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(acc)
    return acc

@router.delete("/payment-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserPaymentAccount).filter(
            UserPaymentAccount.id == account_id,
            UserPaymentAccount.user_id == current_user.id
        )
    )
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment account not found")

    await db.delete(acc)
    await db.commit()

# ==================== User Management (Admin / Detail) ====================

@router.get("/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage"))
):
    """
    List all users (Admin only).
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve user by UUID.
    """
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this user"
        )
        
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return await get_user_response(db, user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("users.manage"))
):
    """
    Delete a user account (Admin only).
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()
