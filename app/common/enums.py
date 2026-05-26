from __future__ import annotations

from enum import Enum


class LedgerEntryType(str, Enum):
    TOPUP = "topup"
    BET_HOLD = "bet_hold"
    BET_REFUND = "bet_refund"
    WIN = "win"
    WITHDRAWAL_HOLD = "withdrawal_hold"
    WITHDRAWAL_REFUND = "withdrawal_refund"
    ADMIN_CREDIT = "admin_credit"
    ADMIN_DEBIT = "admin_debit"


class GameStatus(str, Enum):
    SEARCHING = "searching"
    WAITING_OPPONENT_SETUP = "waiting_opponent_setup"
    ACTIVE = "active"
    PLAYER_WON = "player_won"
    PLAYER_LOST = "player_lost"
    CANCELED = "canceled"
    FINISHED = "finished"


class TicketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class WithdrawalStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELED = "canceled"


class WithdrawalMethod(str, Enum):
    STARS = "stars"
    USDT = "usdt"
    TON = "ton"
    SBP = "sbp"

