from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.models.khutba import JumaKhutba
from app.api.v1.endpoints.khutba_helpers import make_full_image_url
from app.services.notification_dispatcher import dispatch_broadcast

router = APIRouter()

async def auto_notify_khutba(db: AsyncSession, k: JumaKhutba):
    try:
        title = f"Friday Khutba: {k.title}"
        body = f"By {k.imam_name} on {k.khutba_date.strftime('%d %b %Y')}"
        image_full_url = make_full_image_url(k.imam_photo)
        payload = {"type": "khutba", "khutba_id": str(k.id), "title": str(k.title)}
        await dispatch_broadcast(
            db=db, title=title, body=body, topic="all_users",
            data=payload, image_url=image_full_url, notification_type="khutba",
            related_id_field="related_khutba_id", related_id_val=k.id,
        )
    except Exception:
        pass

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

    count = await dispatch_broadcast(
        db=db,
        title=title,
        body=body,
        topic="all_users",
        data=payload_data,
        image_url=image_full_url,
        notification_type="khutba",
        related_id_field="related_khutba_id",
        related_id_val=k.id,
    )

    return {"status": "success", "success_count": count}
