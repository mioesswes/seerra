from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import TicketStatus
from app.db.models import Ticket, TicketMessage


class TicketService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_open_ticket(self, user_id: int) -> Ticket | None:
        return await self.session.scalar(
            select(Ticket)
            .where(Ticket.user_id == user_id, Ticket.status == TicketStatus.OPEN)
            .order_by(Ticket.id.desc())
        )

    async def get_by_id(self, ticket_id: int) -> Ticket | None:
        return await self.session.scalar(select(Ticket).where(Ticket.id == ticket_id))

    async def create_ticket(self, user_id: int, text: str | None, media: list[dict]) -> Ticket:
        existing = await self.get_open_ticket(user_id)
        if existing:
            raise ValueError("У пользователя уже есть открытый тикет")
        ticket = Ticket(user_id=user_id)
        self.session.add(ticket)
        await self.session.flush()
        self.session.add(TicketMessage(ticket_id=ticket.id, sender_user_id=user_id, text=text, media=media))
        await self.session.flush()
        return ticket

    async def append_user_message(self, ticket_id: int, user_id: int, text: str | None, media: list[dict]) -> None:
        self.session.add(TicketMessage(ticket_id=ticket_id, sender_user_id=user_id, text=text, media=media))
        await self.session.flush()

    async def append_admin_message(self, ticket_id: int, admin_id: int, text: str | None) -> None:
        self.session.add(TicketMessage(ticket_id=ticket_id, sender_admin_id=admin_id, text=text, media=[]))
        await self.session.flush()

    async def list_user_tickets(self, user_id: int) -> list[Ticket]:
        result = await self.session.scalars(select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.id.desc()))
        return list(result)

    async def history(self, ticket_id: int) -> list[TicketMessage]:
        result = await self.session.scalars(
            select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.id.asc())
        )
        return list(result)
