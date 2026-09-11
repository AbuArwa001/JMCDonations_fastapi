import uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import get_db
from app.models.donations import Donation, SavedDonation
from app.models.categories import Category
from app.models.transactions import Transaction
from app.models.ratings import Rating
from app.models.users import User
from app.schemas.donations import (
    DonationCreate,
    DonationUpdate,
    DonationResponse,
    SavedDonationResponse,
)
from app.schemas.transactions import TransactionResponse
from app.api.dependencies.auth import (
    get_current_active_user,
    get_current_admin_user,
)

router = APIRouter()

def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    return re.sub(r'[\s_-]+', '-', s)

async def build_donation_response(db: AsyncSession, donation: Donation) -> DonationResponse:
    # 1. Total collected & distinct supporter count (distinct registered donors + anonymous/guest donors)
    tx_stats_res = await db.execute(
        select(
            func.coalesce(func.sum(Transaction.amount), 0.0).label("collected"),
            func.count(func.distinct(Transaction.user_id)).label("reg_donors"),
            func.count(case((Transaction.user_id.is_(None), 1))).label("anon_donors"),
        ).filter(
            Transaction.donation_id == donation.id,
            Transaction.payment_status == "Completed",
        )
    )
    tx_stats = tx_stats_res.one()
    collected = float(tx_stats.collected or 0.0)
    donors = int(tx_stats.reg_donors or 0) + int(tx_stats.anon_donors or 0)

    # 2. Average rating
    rating_res = await db.execute(
        select(func.coalesce(func.avg(Rating.rating), 0.0))
        .filter(Rating.donation_id == donation.id)
    )
    avg_rating = round(float(rating_res.scalar() or 0.0), 2)

    # 3. Remaining days & expired check
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    remaining_days = (donation.end_date.date() - now.date()).days if donation.end_date else 0
    is_expired = remaining_days < 0

    # 4. Resolve category name
    cat_name = None
    if donation.category_id:
        cat_res = await db.execute(select(Category.category_name).filter(Category.id == donation.category_id))
        cat_name = cat_res.scalar()

    resp = DonationResponse.model_validate(donation)
    resp.collected_amount = collected
    resp.donor_count = donors
    resp.average_rating = avg_rating
    resp.remaining_days = remaining_days
    resp.is_expired = is_expired
    resp.category_name = cat_name
    return resp


@router.get("/", response_model=List[DonationResponse])
async def list_donations(
    skip: int = 0,
    limit: int = 100,
    page: Optional[int] = None,
    category_id: Optional[uuid.UUID] = None,
    category_name: Optional[str] = None,
    category__category_name: Optional[str] = Query(None, include_in_schema=False),
    category: Optional[str] = Query(None, include_in_schema=False),
    status: Optional[str] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = None,
    include_deleted: bool = False,
    deleted_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    List donation drives with filtering, search, ordering, and pagination.
    """
    if page and page > 0:
        skip = (page - 1) * limit

    query = select(Donation)

    if deleted_only:
        query = query.filter(Donation.is_deleted == True)
    elif not include_deleted:
        query = query.filter(Donation.is_deleted == False)

    # Resolve category filter from any parameter alias
    cat_filter = category_id
    cat_name_filter = category_name or category__category_name or category
    joined_category = False

    if cat_name_filter and not cat_filter:
        try:
            cat_filter = uuid.UUID(str(cat_name_filter).strip())
        except ValueError:
            cat_filter = None

    if cat_filter:
        query = query.filter(Donation.category_id == cat_filter)
    elif cat_name_filter and str(cat_name_filter).strip().lower() != "all":
        query = query.join(Category, Donation.category_id == Category.id)
        joined_category = True
        query = query.filter(Category.category_name.ilike(str(cat_name_filter).strip()))

    if status:
        query = query.filter(Donation.status == status)
    if is_featured is not None:
        query = query.filter(Donation.is_featured == is_featured)

    if search and search.strip():
        terms = [t for t in search.strip().split() if t]
        if not joined_category:
            query = query.outerjoin(Category, Donation.category_id == Category.id)
            joined_category = True
        for term in terms:
            search_pattern = f"%{term}%"
            query = query.filter(
                or_(
                    Donation.title.ilike(search_pattern),
                    Donation.description.ilike(search_pattern),
                    Donation.account_name.ilike(search_pattern),
                    Donation.paybill_number.ilike(search_pattern),
                    Category.category_name.ilike(search_pattern),
                )
            )

    # Ordering
    if ordering:
        if ordering == "target_amount":
            query = query.order_by(Donation.target_amount.asc())
        elif ordering == "-target_amount":
            query = query.order_by(Donation.target_amount.desc())
        elif ordering == "created_at":
            query = query.order_by(Donation.created_at.asc())
        elif ordering == "-created_at":
            query = query.order_by(Donation.created_at.desc())
        else:
            query = query.order_by(Donation.created_at.desc())
    else:
        query = query.order_by(Donation.created_at.desc())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    donations = result.scalars().all()

    return [await build_donation_response(db, d) for d in donations]


@router.post("/", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
async def create_donation(
    donation_in: DonationCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new donation drive (Admin only).
    """
    base_slug = slugify(donation_in.title)
    slug = base_slug
    counter = 1
    while True:
        existing = await db.execute(select(Donation).filter(Donation.slug == slug))
        if not existing.scalars().first():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    donation_data = donation_in.model_dump()
    db_donation = Donation(
        **donation_data,
        slug=slug,
        created_by_id=current_user.id,
        is_deleted=False,
        status="Active"
    )
    db.add(db_donation)
    await db.commit()
    await db.refresh(db_donation)
    return await build_donation_response(db, db_donation)


@router.get("/saved", response_model=List[SavedDonationResponse])
async def get_my_saved_donations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all donations saved by the authenticated user.
    """
    query = (
        select(SavedDonation)
        .options(selectinload(SavedDonation.donation))
        .filter(SavedDonation.user_id == current_user.id)
        .order_by(SavedDonation.saved_at.desc())
    )
    result = await db.execute(query)
    saved_items = result.scalars().all()

    output = []
    for item in saved_items:
        d_resp = await build_donation_response(db, item.donation) if item.donation else None
        output.append(SavedDonationResponse(
            id=item.id,
            user_id=item.user_id,
            donation_id=item.donation_id,
            donation=d_resp,
            saved_at=item.saved_at
        ))
    return output


@router.get("/saved_ids", response_model=List[uuid.UUID])
async def get_my_saved_donation_ids(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List UUIDs of all donations saved by current user.
    """
    result = await db.execute(
        select(SavedDonation.donation_id).filter(SavedDonation.user_id == current_user.id)
    )
    return [r[0] for r in result.all()]


@router.get("/users/history", response_model=List[TransactionResponse])
async def get_my_donation_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all transactions made by current user across all donations.
    """
    result = await db.execute(
        select(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.donated_at.desc())
    )
    return result.scalars().all()


@router.get("/{donation_id}", response_model=DonationResponse)
async def get_donation(
    donation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve donation details by UUID.
    """
    result = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = result.scalars().first()
    if not donation or donation.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    return await build_donation_response(db, donation)


@router.patch("/{donation_id}", response_model=DonationResponse)
@router.put("/{donation_id}", response_model=DonationResponse)
async def update_donation(
    donation_id: uuid.UUID,
    donation_in: DonationUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update donation details (Admin only).
    """
    result = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = result.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    update_data = donation_in.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"] != donation.title:
        donation.slug = slugify(update_data["title"])

    for field, value in update_data.items():
        setattr(donation, field, value)

    donation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(donation)
    return await build_donation_response(db, donation)


@router.post("/{donation_id}/images", response_model=DonationResponse)
@router.post("/{donation_id}/images/", response_model=DonationResponse)
@router.patch("/{donation_id}/images", response_model=DonationResponse)
@router.patch("/{donation_id}/images/", response_model=DonationResponse)
async def upload_donation_images(
    donation_id: uuid.UUID,
    files: Optional[List[UploadFile]] = File(None),
    uploaded_images: Optional[List[UploadFile]] = File(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload one or more images for a donation drive gallery (Admin only).
    """
    result = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = result.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    incoming_files: List[UploadFile] = []
    if files:
        incoming_files.extend(files)
    if uploaded_images:
        incoming_files.extend(uploaded_images)

    if not incoming_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image files provided."
        )

    upload_dir = Path("static/donations")
    upload_dir.mkdir(parents=True, exist_ok=True)

    current_images = list(donation.image_urls or [])
    for idx, f in enumerate(incoming_files):
        if not f.content_type or not f.content_type.startswith("image/"):
            continue
        ext = f.filename.split(".")[-1] if f.filename and "." in f.filename else "jpg"
        timestamp = int(datetime.now(timezone.utc).timestamp())
        filename = f"{donation_id}_{timestamp}_{idx}_{uuid.uuid4().hex[:6]}.{ext}"
        dest_path = upload_dir / filename

        content = await f.read()
        with open(dest_path, "wb") as out_file:
            out_file.write(content)

        relative_url = f"/static/donations/{filename}"
        current_images.append(relative_url)

    donation.image_urls = current_images
    flag_modified(donation, "image_urls")
    donation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(donation)
    return await build_donation_response(db, donation)


@router.delete("/{donation_id}/images", response_model=DonationResponse)
@router.delete("/{donation_id}/images/", response_model=DonationResponse)
async def delete_donation_image(
    donation_id: uuid.UUID,
    image_url: str = Query(..., description="URL or path of image to delete from donation gallery"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific gallery image from a donation drive (Admin only).
    """
    result = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = result.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    current_images = list(donation.image_urls or [])
    target = image_url.strip()

    # Match by exact URL, relative path, or filename
    matched = None
    for img in current_images:
        if img == target or target in img or img in target:
            matched = img
            break

    if not matched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found in donation drive")

    current_images.remove(matched)
    donation.image_urls = current_images
    flag_modified(donation, "image_urls")
    donation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Clean up file on disk if stored locally
    try:
        clean_path = matched.lstrip("/")
        local_file = Path(clean_path)
        if local_file.exists() and "static/donations" in clean_path:
            local_file.unlink()
    except Exception:
        pass

    await db.commit()
    await db.refresh(donation)
    return await build_donation_response(db, donation)


@router.delete("/{donation_id}", status_code=status.HTTP_200_OK)
async def delete_donation(
    donation_id: uuid.UUID,
    permanent: bool = Query(False, description="Set True for permanent deletion; False for soft delete"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a donation drive (Admin only).
    - Default: Soft delete (sets is_deleted=True, deleted_at=timestamp).
    - permanent=true: Permanently deletes record from database.
    """
    result = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = result.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    if permanent:
        await db.delete(donation)
        await db.commit()
        return {
            "status": "success",
            "message": "Donation permanently deleted",
            "donation_id": str(donation_id),
            "permanent": True
        }
    else:
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        donation.is_deleted = True
        donation.deleted_at = now_utc
        await db.commit()
        return {
            "status": "success",
            "message": "Donation soft deleted",
            "donation_id": str(donation_id),
            "is_deleted": True,
            "deleted_at": donation.deleted_at,
            "permanent": False
        }


@router.delete("/{donation_id}/permanent", status_code=status.HTTP_200_OK)
async def permanent_delete_donation(
    donation_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Explicit permanent deletion of a donation record (Admin only).
    """
    result = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = result.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    await db.delete(donation)
    await db.commit()
    return {
        "status": "success",
        "message": "Donation permanently deleted",
        "donation_id": str(donation_id)
    }


@router.post("/{donation_id}/restore", response_model=DonationResponse)
async def restore_donation(
    donation_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Restore a soft-deleted donation (Admin only).
    """
    result = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = result.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    if not donation.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Donation is not deleted")

    donation.is_deleted = False
    donation.deleted_at = None
    donation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(donation)
    return await build_donation_response(db, donation)


@router.post("/{donation_id}/save", response_model=SavedDonationResponse, status_code=status.HTTP_201_CREATED)
async def save_donation(
    donation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Save a donation to authenticated user's favorites.
    """
    d_res = await db.execute(select(Donation).filter(Donation.id == donation_id, Donation.is_deleted == False))
    donation = d_res.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    existing_res = await db.execute(
        select(SavedDonation).filter(
            SavedDonation.user_id == current_user.id,
            SavedDonation.donation_id == donation_id
        )
    )
    existing = existing_res.scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already saved")

    saved_obj = SavedDonation(
        user_id=current_user.id,
        donation_id=donation.id,
        saved_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(saved_obj)
    await db.commit()
    await db.refresh(saved_obj)

    d_resp = await build_donation_response(db, donation)
    return SavedDonationResponse(
        id=saved_obj.id,
        user_id=saved_obj.user_id,
        donation_id=saved_obj.donation_id,
        donation=d_resp,
        saved_at=saved_obj.saved_at
    )


@router.delete("/{donation_id}/unsave", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_donation(
    donation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a donation from authenticated user's favorites.
    """
    res = await db.execute(
        select(SavedDonation).filter(
            SavedDonation.user_id == current_user.id,
            SavedDonation.donation_id == donation_id
        )
    )
    saved_obj = res.scalars().first()
    if not saved_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found in saved list")

    await db.delete(saved_obj)
    await db.commit()
