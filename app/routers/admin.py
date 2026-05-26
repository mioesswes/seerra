from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.common.locks import game_action_locks
from app.common.enums import GameStatus, LedgerEntryType, WithdrawalStatus
from app.config import get_settings
from app.db.models import GameSession, LedgerEntry, Ticket, User, WithdrawalRequest
from app.db.session import SessionLocal
from app.keyboards.inline import admin_game_keyboard, admin_panel_keyboard, processing_keyboard
from app.services.games import GameService
from app.services.tickets import TicketService
from app.services.users import UserService
from app.services.withdrawals import WithdrawalService

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_ids


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("Панель администратора", reply_markup=admin_panel_keyboard())


@router.message(Command("credit"))
async def admin_credit(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("Формат: /credit <telegram_id> <amount>")
        return
    telegram_id = int(parts[1])
    amount = int(parts[2])
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer("Пользователь не найден.")
            return
        await users.add_balance(user.id, amount, LedgerEntryType.ADMIN_CREDIT, "Начисление админом")
        await GameService(session, message.bot).log_admin_action(message.from_user.id, "credit", f"{telegram_id}:{amount}")
        await session.commit()
    await message.answer(f"Начислено {amount} ⭐ пользователю {telegram_id}.")


@router.message(Command("debit"))
async def admin_debit(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("Формат: /debit <telegram_id> <amount>")
        return
    telegram_id = int(parts[1])
    amount = int(parts[2])
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_by_telegram_id(telegram_id)
        if not user:
            await message.answer("Пользователь не найден.")
            return
        try:
            await users.remove_balance(user.id, amount, LedgerEntryType.ADMIN_DEBIT, "Списание админом")
        except ValueError as exc:
            await message.answer(str(exc))
            await session.rollback()
            return
        await GameService(session, message.bot).log_admin_action(message.from_user.id, "debit", f"{telegram_id}:{amount}")
        await session.commit()
    await message.answer(f"Списано {amount} ⭐ у пользователя {telegram_id}.")


@router.message(Command("reply_ticket"))
async def admin_reply_ticket(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer("Формат: /reply_ticket <ticket_id> <текст>")
        return
    ticket_id = int(parts[1])
    text = parts[2]
    async with SessionLocal() as session:
        ticket_service = TicketService(session)
        ticket = await ticket_service.get_by_id(ticket_id)
        if not ticket:
            await message.answer("Тикет не найден.")
            return
        await ticket_service.append_admin_message(ticket_id, message.from_user.id, text)
        user = await session.scalar(select(User).where(User.id == ticket.user_id))
        await GameService(session, message.bot).log_admin_action(message.from_user.id, "reply_ticket", str(ticket_id))
        await session.commit()
    if user:
        await message.bot.send_message(
            user.telegram_id,
            f"📩 Новый ответ в тикете #{ticket_id}\n\n{text}\n\nОткройте раздел помощи, чтобы посмотреть диалог.",
        )
    await message.answer("Ответ отправлен.")


@router.callback_query(F.data.startswith("admin:accept:"))
async def admin_accept(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    game_id = callback.data.split(":")[2]
    async with game_action_locks.get(f"game:{game_id}"):
        await callback.message.edit_reply_markup(reply_markup=processing_keyboard("⏳ Принятие игры..."))
        async with SessionLocal() as session:
            service = GameService(session, callback.bot)
            game = await session.scalar(select(GameSession).where(GameSession.id == game_id))
            if not game:
                await callback.answer("Игра не найдена", show_alert=True)
                return
            try:
                await service.accept_game(game, callback.from_user.id)
                await service.log_admin_action(callback.from_user.id, "accept_game", game.id)
                await service.render_game_views(game)
            except ValueError as exc:
                await callback.answer(str(exc), show_alert=True)
                await session.rollback()
                return
            await session.commit()
    await callback.answer("Игра принята")


@router.callback_query(F.data.startswith("admincard:"))
async def admin_card(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, game_id, value = callback.data.split(":")
    async with game_action_locks.get(f"game:{game_id}"):
        await callback.message.edit_reply_markup(reply_markup=admin_game_keyboard(game_id, locked=True))
        async with SessionLocal() as session:
            service = GameService(session, callback.bot)
            game = await session.scalar(select(GameSession).where(GameSession.id == game_id))
            if not game:
                await callback.answer("Игра не найдена", show_alert=True)
                return
            try:
                await service.add_admin_card(game, callback.from_user.id, value)
                await service.log_admin_action(callback.from_user.id, "add_card", f"{game.id}:{value}")
                await service.render_game_views(game)
            except ValueError as exc:
                await callback.message.edit_reply_markup(reply_markup=admin_game_keyboard(game_id))
                await callback.answer(str(exc), show_alert=True)
                await session.rollback()
                return
            await session.commit()
    await callback.answer()


@router.callback_query(F.data.startswith("adminstop:"))
async def admin_stop(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    game_id = callback.data.split(":")[1]
    async with game_action_locks.get(f"game:{game_id}"):
        await callback.message.edit_reply_markup(reply_markup=admin_game_keyboard(game_id, locked=True))
        async with SessionLocal() as session:
            service = GameService(session, callback.bot)
            game = await session.scalar(select(GameSession).where(GameSession.id == game_id))
            if not game:
                await callback.answer("Игра не найдена", show_alert=True)
                return
            try:
                await service.admin_stop(game, callback.from_user.id)
                await service.log_admin_action(callback.from_user.id, "stop_game", game.id)
                await service.render_game_views(game)
            except ValueError as exc:
                await callback.answer(str(exc), show_alert=True)
                await session.rollback()
                return
            await session.commit()
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with SessionLocal() as session:
        users_total = await session.scalar(select(func.count()).select_from(User))
        active_games = await session.scalar(
            select(func.count()).select_from(GameSession).where(
                GameSession.status.in_([GameStatus.SEARCHING, GameStatus.WAITING_OPPONENT_SETUP, GameStatus.ACTIVE])
            )
        )
        withdrawals = await session.scalar(select(func.count()).select_from(WithdrawalRequest))
        tickets = await session.scalar(select(func.count()).select_from(Ticket))
        turnover = await session.scalar(
            select(func.coalesce(func.sum(func.abs(LedgerEntry.amount)), 0)).where(
                LedgerEntry.entry_type == LedgerEntryType.BET_HOLD
            )
        )
        payouts = await session.scalar(
            select(func.coalesce(func.sum(WithdrawalRequest.amount), 0)).where(
                WithdrawalRequest.status == WithdrawalStatus.COMPLETED
            )
        )
        await session.commit()
    revenue = (turnover or 0) - (payouts or 0)
    await callback.message.answer(
        "📊 Статистика\n\n"
        f"Игроков: {users_total}\n"
        f"Активных игр: {active_games}\n"
        f"Выводов: {withdrawals}\n"
        f"Тикетов: {tickets}\n"
        f"Оборот: {turnover or 0} ⭐\n"
        f"Выплаты: {payouts or 0} ⭐\n"
        f"Доход проекта: {revenue} ⭐"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:games")
async def admin_games(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with SessionLocal() as session:
        result = await session.scalars(
            select(GameSession).where(GameSession.status.in_([GameStatus.SEARCHING, GameStatus.WAITING_OPPONENT_SETUP, GameStatus.ACTIVE]))
        )
        games = list(result)
        await session.commit()
    if not games:
        await callback.message.answer("Активных игр нет.")
    else:
        rows = [f"{game.id} | {game.status.value} | {game.stake} ⭐" for game in games[:20]]
        await callback.message.answer("🎮 Активные игры\n\n" + "\n".join(rows))
    await callback.answer()


@router.callback_query(F.data == "admin:tickets")
async def admin_tickets(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    async with SessionLocal() as session:
        result = await session.scalars(select(Ticket).order_by(Ticket.id.desc()).limit(20))
        tickets = list(result)
        await session.commit()
    if not tickets:
        await callback.message.answer("Тикетов нет.")
    else:
        rows = [f"#{ticket.id} | {ticket.status.value}" for ticket in tickets]
        await callback.message.answer("🎫 Тикеты\n\n" + "\n".join(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("withdraw:done:"))
async def withdraw_done(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    withdrawal_id = int(callback.data.split(":")[2])
    async with SessionLocal() as session:
        service = WithdrawalService(session)
        item = await service.mark_done(withdrawal_id)
        if item:
            await GameService(session, callback.bot).log_admin_action(callback.from_user.id, "withdraw_done", str(withdrawal_id))
        await session.commit()
    if not item:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    await callback.message.edit_text("✅ Вывод завершен", reply_markup=None)
    await callback.answer()
