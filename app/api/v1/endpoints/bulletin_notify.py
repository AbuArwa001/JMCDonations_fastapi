from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_permission
from app.models.bulletins import FridayBulletin
from app.services.notification_dispatcher import dispatch_broadcast

router = APIRouter()

async def auto_notify_bulletin(db: AsyncSession, b: FridayBulletin):
    try:
        title = f"New Friday Bulletin: {b.title}"
        body = f"Issue #{b.issue_number or ''} is now available to read."
        cover = f"https://donations-api.jamiamosque.co.ke{b.cover_image_path}" if b.cover_image_path else None
        await dispatch_broadcast(
            db=db,
            title=title,
            body=body,
            topic="bulletins",
            data={"type": "bulletin", "bulletin_id": str(b.id), "title": str(b.title)},
            image_url=cover,
            notification_type="bulletin",
        )
    except Exception:
        pass

@router.post("/{id}/notify")
@router.post("/{id}/notify/")
async def notify_bulletin(
    id: int,
    current_user=Depends(require_permission("bulletins.manage")),
    db: AsyncSession = Depends(get_db)
):
    b = await db.get(FridayBulletin, id)
    if not b:
        raise HTTPException(status_code=404, detail="Bulletin not found")

    title = f"New Friday Bulletin: {b.title}"
    body = f"Issue #{b.issue_number or ''} is now available to read."
    cover = f"https://donations-api.jamiamosque.co.ke{b.cover_image_path}" if b.cover_image_path else None

    count = await dispatch_broadcast(
        db=db,
        title=title,
        body=body,
        topic="bulletins",
        data={"type": "bulletin", "bulletin_id": str(b.id), "title": str(b.title)},
        image_url=cover,
        notification_type="bulletin",
    )
    return {"status": "broadcasted", "bulletin_id": id, "success_count": count}
