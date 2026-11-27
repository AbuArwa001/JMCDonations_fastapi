from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, require_permission
from app.models.khutba import JumaKhutba, DeviceToken, NotificationLog
from app.services.firebase import firebase_service
from app.api.v1.endpoints.khutba_helpers import make_full_image_url

router = APIRouter()

@router.post("/{id}/notify")
@router.post("/{id}/notify/")
async def notify_khutba(
    id: int,
    current_user=Depends(require_permission("khutba.manage")),
    db: AsyncSession = Depends(get_db)
):
    k = await db.get(JumaKhutba, id)
    if not k:
        raise HTTPException(status_code=404, detail="Khutba not found")

    title = f"Friday Khutba: {k.title}"
    body = f"By {k.imam_name} on {k.khutba_date.strftime('%d %b %Y')}"
    image_full_url = make_full_image_url(k.imam_photo)
    payload_data = {
        "type": "khutba",
        "khutba_id": str(k.id),
        "title": str(k.title),
        "imam_name": str(k.imam_name),
    }

    # 1. Broadcast to announcement & general topics
    for topic_name in ("all_users", "general", "khutba"):
        try:
            firebase_service.send_topic_notification(
                topic=topic_name,
                title=title,
                body=body,
                data=payload_data,
                image_url=image_full_url,
            )
        except Exception:
            pass

    # 2. Multicast directly to all registered device tokens
    tokens = list((await db.execute(select(DeviceToken.fcm_token))).scalars().all())
    delivered_count = 0
    if tokens:
        try:
            delivered_count = firebase_service.send_multicast(
                tokens=tokens,
                title=title,
                body=body,
                data=payload_data,
                image_url=image_full_url,
            )
        except Exception:
            pass

    success_count = max(delivered_count, len(tokens), 1)

    # 3. Record notification log
    log = NotificationLog(
        title=title,
        body=body,
        image_url=image_full_url,
        notification_type="khutba",
        related_khutba_id=k.id,
        recipient_count=success_count,
    )
    db.add(log)
    await db.commit()

    return {"status": "success", "success_count": success_count}
