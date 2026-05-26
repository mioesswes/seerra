from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import GameStatus, LedgerEntryType
from app.db.models import GameSession, LedgerEntry, User, Wallet


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(self, telegram_id: int, username: str | None, first_name: str | None) -> User:
        stmt: Select[tuple[User]] = select(User).where(User.telegram_id == telegram_id)
        user = await self.session.scalar(stmt)
        if user:
            user.username = username
            user.first_name = first_name
            await self.session.flush()
            return user

        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        self.session.add(user)
        await self.session.flush()
        self.session.add(Wallet(user_id=user.id))
        await self.session.flush()
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def get_wallet(self, user_id: int) -> Wallet:
        wallet = await self.session.scalar(select(Wallet).where(Wallet.user_id == user_id))
        return wallet

    async def add_balance(self, user_id: int, amount: int, entry_type: LedgerEntryType, note: str) -> Wallet:
        wallet = await self.get_wallet(user_id)
        wallet.balance_stars += amount
        self.session.add(LedgerEntry(user_id=user_id, entry_type=entry_type, amount=amount, note=note))
        await self.session.flush()
        return wallet

    async def remove_balance(self, user_id: int, amount: int, entry_type: LedgerEntryType, note: str) -> Wallet:
        wallet = await self.get_wallet(user_id)
        if wallet.balance_stars < amount:
            raise ValueError("Недостаточно средств")
        wallet.balance_stars -= amount
        self.session.add(LedgerEntry(user_id=user_id, entry_type=entry_type, amount=-amount, note=note))
        await self.session.flush()
        return wallet

    async def stats(self, user_id: int) -> dict[str, int]:
        games_total = await self.session.scalar(
            select(func.count(GameSession.id)).where(GameSession.user_id == user_id, GameSession.status.in_([
                GameStatus.PLAYER_WON, GameStatus.PLAYER_LOST, GameStatus.FINISHED
            ]))
        )
        gross_wins = await self.session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.user_id == user_id, LedgerEntry.entry_type == LedgerEntryType.WIN
            )
        )
        max_win = await self.session.scalar(
            select(func.coalesce(func.max(LedgerEntry.amount), 0)).where(
                LedgerEntry.user_id == user_id, LedgerEntry.entry_type == LedgerEntryType.WIN
            )
        )
        max_bet = await self.session.scalar(
            select(func.coalesce(func.max(GameSession.stake), 0)).where(GameSession.user_id == user_id)
        )
        return {
            "games_total": games_total or 0,
            "gross_wins": gross_wins or 0,
            "max_win": max_win or 0,
            "max_bet": max_bet or 0,
        }
