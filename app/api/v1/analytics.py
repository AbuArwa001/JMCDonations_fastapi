import uuid
import io
import csv
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from app.db.session import get_db
from app.models.transactions import Transaction
from app.models.donations import Donation
from app.models.categories import Category
from app.models.users import User
from app.schemas.analytics import (
    DashboardSummaryResponse, CategoryBreakdownResponse,
    DriveProgressResponse, PendingCashResponse, DonationTrendItem
)
from app.api.dependencies.auth import get_current_admin_user

router = APIRouter()

@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated dashboard summary metrics (Admin only).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # 1. Total all-time completed
    total_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(Transaction.payment_status == "Completed")
    )
    total_collected = float(total_res.scalar() or 0.0)

    # 2. Total week completed
    week_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(Transaction.payment_status == "Completed", Transaction.donated_at >= week_ago)
    )
    total_week = float(week_res.scalar() or 0.0)

    # 3. Total month completed
    month_res = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(Transaction.payment_status == "Completed", Transaction.donated_at >= month_ago)
    )
    total_month = float(month_res.scalar() or 0.0)

    # 4. Active drives count
    drives_res = await db.execute(
        select(func.count(Donation.id))
        .filter(Donation.status == "Active", Donation.is_deleted == False)
    )
    active_drives = int(drives_res.scalar() or 0)

    # 5. Trends for last 7 days
    trends: List[DonationTrendItem] = []
    for i in range(7):
        target_day = (now - timedelta(days=6 - i)).date()
        day_start = datetime(target_day.year, target_day.month, target_day.day, 0, 0, 0)
        day_end = datetime(target_day.year, target_day.month, target_day.day, 23, 59, 59)
        day_res = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0))
            .filter(
                Transaction.payment_status == "Completed",
                Transaction.donated_at >= day_start,
                Transaction.donated_at <= day_end
            )
        )
        day_amount = float(day_res.scalar() or 0.0)
        trends.append(DonationTrendItem(
            name=target_day.strftime("%a"),
            amount=day_amount
        ))

    return DashboardSummaryResponse(
        total_collected=round(total_collected, 2),
        total_collected_week=round(total_week, 2),
        total_collected_month=round(total_month, 2),
        active_drives=active_drives,
        donation_trends=trends
    )


@router.get("/categories", response_model=List[CategoryBreakdownResponse])
async def get_category_breakdown(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get donation funding breakdown by category (Admin only).
    """
    cats_res = await db.execute(select(Category))
    categories = cats_res.scalars().all()

    breakdown = []
    for cat in categories:
        amt_res = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0))
            .join(Donation, Donation.id == Transaction.donation_id)
            .filter(
                Donation.category_id == cat.id,
                Transaction.payment_status == "Completed"
            )
        )
        cat_amount = float(amt_res.scalar() or 0.0)
        breakdown.append(CategoryBreakdownResponse(
            category_name=cat.category_name,
            total_amount=round(cat_amount, 2),
            color=cat.color
        ))

    return breakdown


@router.get("/donations/{donation_id}/progress", response_model=DriveProgressResponse)
async def get_drive_progress(
    donation_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get progress metrics for a single donation drive (Admin only).
    """
    d_res = await db.execute(select(Donation).filter(Donation.id == donation_id))
    donation = d_res.scalars().first()
    if not donation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation drive not found")

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

    return DriveProgressResponse(
        donation=donation.title,
        total_collected=round(collected, 2),
        unique_donors=donors,
        target=float(donation.target_amount)
    )


@router.get("/cash/pending", response_model=List[PendingCashResponse])
async def get_pending_cash_transactions(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List pending cash transactions awaiting admin verification (Admin only).
    """
    query = (
        select(Transaction, Donation.title)
        .join(Donation, Donation.id == Transaction.donation_id)
        .filter(
            Transaction.payment_method.ilike("%Cash%"),
            Transaction.payment_status == "Pending"
        )
    )
    result = await db.execute(query)
    items = []
    for tx, title in result.all():
        items.append(PendingCashResponse(
            id=tx.id,
            amount=float(tx.amount),
            donation=title
        ))
    return items


@router.get("/trends", response_model=List[DonationTrendItem])
async def get_donation_trends(
    period: str = Query("week", pattern="^(week|month|year)$"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get donation trends for 'week', 'month', or 'year' (Admin only).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days_range = 7 if period == "week" else (30 if period == "month" else 365)
    trends: List[DonationTrendItem] = []

    if period in ["week", "month"]:
        date_format = "%a" if period == "week" else "%d %b"
        for i in range(days_range):
            target_day = (now - timedelta(days=(days_range - 1) - i)).date()
            day_start = datetime(target_day.year, target_day.month, target_day.day, 0, 0, 0)
            day_end = datetime(target_day.year, target_day.month, target_day.day, 23, 59, 59)
            res = await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0.0))
                .filter(
                    Transaction.payment_status == "Completed",
                    Transaction.donated_at >= day_start,
                    Transaction.donated_at <= day_end
                )
            )
            trends.append(DonationTrendItem(
                name=target_day.strftime(date_format),
                amount=float(res.scalar() or 0.0)
            ))
    else:
        # Group by 12 months for year
        for m in range(12):
            month_date = now - timedelta(days=(11 - m) * 30)
            m_start = datetime(month_date.year, month_date.month, 1, 0, 0, 0)
            # end of month calculation
            if month_date.month == 12:
                m_end = datetime(month_date.year + 1, 1, 1, 0, 0, 0)
            else:
                m_end = datetime(month_date.year, month_date.month + 1, 1, 0, 0, 0)

            res = await db.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0.0))
                .filter(
                    Transaction.payment_status == "Completed",
                    Transaction.donated_at >= m_start,
                    Transaction.donated_at < m_end
                )
            )
            trends.append(DonationTrendItem(
                name=month_date.strftime("%b"),
                amount=float(res.scalar() or 0.0)
            ))

    return trends


@router.get("/export")
async def export_transactions_csv(
    drive_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export transactions as a CSV spreadsheet (Admin only).
    """
    query = (
        select(Transaction, Donation.title)
        .join(Donation, Donation.id == Transaction.donation_id)
        .order_by(Transaction.donated_at.desc())
    )
    if drive_id:
        query = query.filter(Transaction.donation_id == drive_id)

    result = await db.execute(query)
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Donation", "Amount", "Payment Status", "Payment Method", "Date", "Reference"])

    for tx, title in rows:
        writer.writerow([
            str(tx.id),
            title,
            float(tx.amount),
            tx.payment_status,
            tx.payment_method,
            tx.donated_at.strftime("%Y-%m-%d %H:%M:%S") if tx.donated_at else "",
            tx.transaction_reference or ""
        ])

    csv_data = output.getvalue()
    output.close()

    filename = f"transactions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
