from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import LedgerEntryType, WithdrawalMethod, WithdrawalStatus
from app.db.models import WithdrawalRequest
from app.services.users import UserService


class WithdrawalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserService(session)

    async def create(self, user_id: int, amount: int, method: WithdrawalMethod, requisites: str) -> WithdrawalRequest:
        if amount < 250:
            raise ValueError("Вывод доступен от 250 ⭐")
        wallet = await self.users.get_wallet(user_id)
        if wallet.balance_stars < amount:
            raise ValueError("Недостаточно средств")
        await self.users.remove_balance(user_id, amount, LedgerEntryType.WITHDRAWAL_HOLD, "Создание заявки на вывод")
        request = WithdrawalRequest(user_id=user_id, amount=amount, method=method, requisites=requisites)
        self.session.add(request)
        await self.session.flush()
        return request

    async def mark_done(self, withdrawal_id: int) -> WithdrawalRequest | None:
        item = await self.session.scalar(select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id))
        if not item:
            return None
        item.status = WithdrawalStatus.COMPLETED
        await self.session.flush()
        return item

