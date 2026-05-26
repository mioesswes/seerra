from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import GameStatus, LedgerEntryType, TicketStatus, WithdrawalMethod, WithdrawalStatus
from app.db.base import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False)


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    balance_stars: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="wallet")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entry_type: Mapped[LedgerEntryType] = mapped_column(Enum(LedgerEntryType))
    amount: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    accepted_by_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    stake: Mapped[int] = mapped_column(Integer)
    status: Mapped[GameStatus] = mapped_column(Enum(GameStatus), default=GameStatus.SEARCHING)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    search_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow() + timedelta(minutes=1)
    )
    player_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deck: Mapped[list[dict]] = mapped_column(JSON, default=list)
    player_cards: Mapped[list[dict]] = mapped_column(JSON, default=list)
    opponent_cards: Mapped[list[dict]] = mapped_column(JSON, default=list)
    pending_player_cards: Mapped[list[dict]] = mapped_column(JSON, default=list)
    player_stopped: Mapped[bool] = mapped_column(Boolean, default=False)
    opponent_stopped: Mapped[bool] = mapped_column(Boolean, default=False)
    user_main_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_cards_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    admin_chat_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Deposit(Base):
    __tablename__ = "deposits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    telegram_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    invoice_payload: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    method: Mapped[WithdrawalMethod] = mapped_column(Enum(WithdrawalMethod))
    requisites: Mapped[str] = mapped_column(Text)
    status: Mapped[WithdrawalStatus] = mapped_column(Enum(WithdrawalStatus), default=WithdrawalStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus), default=TicketStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    sender_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sender_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(255))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
