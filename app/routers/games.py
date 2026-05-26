from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.common.locks import game_action_locks
from app.common.text import game_search_text, games_menu_text

from app.db.models import GameSession
from app.db.session import SessionLocal
from app.keyboards.inline import games_menu_keyboard, player_game_keyboard, processing_keyboard, searching_keyboard, stake_keyboard
from app.services.games import GameService
from app.services.users import UserService

router = Router()


GAMES_STICKER_ID = "CAACAgIAAxkBAAFKqQVqFRGr-jMQOxnwcBGHerX4fCu7RgACD5UAAm8HqUjdhbdcgRfCsTsE"


async def _games_menu(message: Message, stake: int | None = None) -> None:
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        wallet = await users.get_wallet(user.id)
        await session.commit()
    await message.answer_sticker(GAMES_STICKER_ID)
    await message.answer(games_menu_text(wallet.balance_stars, stake), reply_markup=games_menu_keyboard())


@router.message(F.text == "🎲 Игры")
async def games_menu(message: Message) -> None:
    await _games_menu(message)


@router.callback_query(F.data == "games:blackjack")
async def blackjack_open(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "<b>BLACK JACK ONLINE</b>\n\nВыберите размер ставки.",
        reply_markup=stake_keyboard(None),
    )
    await callback.answer()


@router.callback_query(F.data == "games:soon")
async def games_soon(callback: CallbackQuery) -> None:
    await callback.answer("🚧 Игра находится в разработке", show_alert=True)


@router.callback_query(F.data.startswith("stake:"))
async def choose_stake(callback: CallbackQuery) -> None:
    amount = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        f"<b>BLACK JACK ONLINE</b>\n\nСтавка выбрана: <b>{amount} ⭐</b>\nНажмите ниже для запуска поиска.",
        reply_markup=stake_keyboard(amount),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("game:start:"))
async def start_search(callback: CallbackQuery) -> None:
    amount = int(callback.data.split(":")[2])
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        service = GameService(session, callback.bot)
        try:
            game = await service.create_search(user.id, amount)
        except ValueError as exc:
            await callback.answer(str(exc), show_alert=True)
            await session.rollback()
            return
        sent = await callback.message.answer(game_search_text(amount), reply_markup=searching_keyboard(game.id))
        await service.push_search_messages(game, user, sent.message_id)
        await session.commit()
    await callback.answer()


@router.callback_query(F.data.startswith("game:cancel:"))
async def cancel_search(callback: CallbackQuery) -> None:
    game_id = callback.data.split(":")[2]
    await callback.message.edit_reply_markup(reply_markup=processing_keyboard("⏳ Отмена поиска..."))
    async with SessionLocal() as session:
        service = GameService(session, callback.bot)
        game = await session.scalar(select(GameSession).where(GameSession.id == game_id))
        if not game:
            await callback.answer("Игра не найдена", show_alert=True)
            return
        try:
            await service.cancel_search(game)
        except ValueError as exc:
            await callback.answer(str(exc), show_alert=True)
            await session.rollback()
            return
        await session.commit()
    await callback.message.edit_text("<b>Поиск отменен</b>\n\nСтавка возвращена на баланс.")
    await callback.answer()


@router.callback_query(F.data.startswith("play:hit:"))
async def player_hit(callback: CallbackQuery) -> None:
    game_id = callback.data.split(":")[2]
    async with game_action_locks.get(f"game:{game_id}"):
        async with SessionLocal() as session:
            service = GameService(session, callback.bot)
            game = await session.scalar(select(GameSession).where(GameSession.id == game_id))
            if not game:
                await callback.answer("Игра не найдена", show_alert=True)
                return
            try:
                await service.player_hit(game)
                await service.render_game_views(game)
            except ValueError as exc:
                await callback.answer(str(exc), show_alert=True)
                await session.rollback()
                return
            await session.commit()
    await callback.answer()


@router.callback_query(F.data.startswith("play:stop:"))
async def player_stop(callback: CallbackQuery) -> None:
    game_id = callback.data.split(":")[2]
    async with game_action_locks.get(f"game:{game_id}"):
        async with SessionLocal() as session:
            service = GameService(session, callback.bot)
            game = await session.scalar(select(GameSession).where(GameSession.id == game_id))
            if not game:
                await callback.answer("Игра не найдена", show_alert=True)
                return
            try:
                await service.player_stop(game)
                await service.render_game_views(game)
            except ValueError as exc:
                await callback.answer(str(exc), show_alert=True)
                await session.rollback()
                return
            await session.commit()
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery) -> None:
    await callback.answer("Сообщение обновляется")