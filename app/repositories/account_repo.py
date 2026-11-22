import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.transactions import BankAccount, Transfer

class BankAccountRepository(BaseRepository[BankAccount]):
    def __init__(self, db: AsyncSession):
        super().__init__(BankAccount, db)

    async def list_active(self) -> List[BankAccount]:
        stmt = select(BankAccount).where(BankAccount.is_active.is_(True)).order_by(BankAccount.account_name)
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_by_number(self, acc_number: str) -> Optional[BankAccount]:
        stmt = select(BankAccount).where(BankAccount.account_number == acc_number)
        return (await self.db.execute(stmt)).scalars().first()

class TransferRepository(BaseRepository[Transfer]):
    def __init__(self, db: AsyncSession):
        super().__init__(Transfer, db)

    async def list_transfers(self, skip: int = 0, limit: int = 50) -> List[Transfer]:
        stmt = select(Transfer).order_by(Transfer.created_at.desc()).offset(skip).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())

