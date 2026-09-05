from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.models.users import User, UserPaymentAccount
from app.models.transactions import Transaction
from app.schemas.users import UserResponse, UserPaymentAccountResponse

async def get_user_response(db: AsyncSession, user: User) -> UserResponse:
    """
    Build a complete UserResponse including computed stats:
    - total_donations: count of completed transactions
    - total_impact: sum of amounts for completed transactions
    - payment_accounts: user payment accounts
    Safely handles async session attributes and matches both user_id and donor phone.
    """
    # 1. Match on user_id and phone_number (in case guest donation used same phone)
    phone_filters = []
    if user.phone_number:
        clean = user.phone_number.replace("+", "").replace(" ", "").replace("-", "").strip()
        if len(clean) >= 9:
            last9 = clean[-9:]
            phone_filters.append(Transaction.account_number.contains(last9))
            
    condition = or_(
        Transaction.user_id == user.id,
        *phone_filters
    ) if phone_filters else (Transaction.user_id == user.id)

    res = await db.execute(
        select(
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.amount), 0.0)
        ).filter(
            condition,
            Transaction.payment_status == "Completed"
        )
    )
    row = res.first()
    total_count = int(row[0] or 0) if row else 0
    total_amount = float(row[1] or 0.0) if row else 0.0

    # 2. Safely query user payment accounts
    accs_res = await db.execute(
        select(UserPaymentAccount)
        .filter(UserPaymentAccount.user_id == user.id)
        .order_by(UserPaymentAccount.created_at.desc())
    )
    payment_accounts = accs_res.scalars().all()

    # 3. Ensure profile image URL uses PNG for DiceBear if SVG was set
    photo_url = user.profile_image_url
    if photo_url and "api.dicebear.com" in photo_url and "/svg" in photo_url:
        photo_url = photo_url.replace("/svg", "/png")

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        phone_number=user.phone_number,
        fcm_token=user.fcm_token,
        is_active=user.is_active,
        is_admin=user.is_admin,
        firebase_uid=user.firebase_uid,
        profile_image_url=photo_url,
        bio=user.bio,
        address=user.address,
        default_donation_account=user.default_donation_account,
        payment_accounts=[UserPaymentAccountResponse.model_validate(a) for a in payment_accounts],
        total_donations=total_count,
        total_impact=round(total_amount, 2),
        ss_login=user.ss_login
    )
