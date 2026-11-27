import uuid
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, delete
from app.repositories.base import BaseRepository
from app.models.transactions import Transaction

class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Transaction, db)

    async def get_by_reference(self, ref: str) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.transaction_reference == ref)
        return (await self.db.execute(stmt)).scalars().first()

    async def get_by_receipt(self, receipt: str) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.mpesa_receipt == receipt)
        return (await self.db.execute(stmt)).scalars().first()

    async def search(
        self, skip: int = 0, limit: int = 20, donation_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None, payment_method: Optional[str] = None,
        search_query: Optional[str] = None, user_id: Optional[uuid.UUID] = None,
        phone_number: Optional[str] = None
    ) -> Tuple[List[Transaction], int]:
        stmt = select(Transaction)
        count_stmt = select(func.count(Transaction.id))
        if user_id:
            user_cond = (Transaction.user_id == user_id)
            if phone_number:
                clean = phone_number.replace("+", "").replace(" ", "").replace("-", "").strip()
                if len(clean) >= 9:
                    user_cond = or_(user_cond, Transaction.account_number.contains(clean[-9:]))
            stmt, count_stmt = stmt.where(user_cond), count_stmt.where(user_cond)
        if donation_id:
            stmt, count_stmt = stmt.where(Transaction.donation_id == donation_id), count_stmt.where(Transaction.donation_id == donation_id)
        if status:
            stmt, count_stmt = stmt.where(Transaction.payment_status == status), count_stmt.where(Transaction.payment_status == status)
        if payment_method:
            stmt, count_stmt = stmt.where(Transaction.payment_method == payment_method), count_stmt.where(Transaction.payment_method == payment_method)
        if search_query:
            cond = or_(
                Transaction.transaction_reference.ilike(f"%{search_query}%"),
                Transaction.account_name.ilike(f"%{search_query}%"),
                Transaction.mpesa_receipt.ilike(f"%{search_query}%"),
            )
            stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        result = await self.db.execute(stmt.order_by(Transaction.donated_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def bulk_delete(self, ids: List[uuid.UUID]) -> int:
        stmt = delete(Transaction).where(Transaction.id.in_(ids))
        result = await self.db.execute(stmt)
        return result.rowcount or 0

