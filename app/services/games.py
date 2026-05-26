from __future__ import annotations

from datetime import timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.admin_notifier import send_admin_log
from app.common.enums import GameStatus, LedgerEntryType
from app.common.text import game_result_text, games_menu_text
from app.config import get_settings
from app.db.models import AdminLog, GameSession, User, utcnow
from app.domain.blackjack import CARD_CATALOG, build_deck, calculate_points, card_rank, deal_from_deck, format_cards, resolve_round
from app.keyboards.inline import admin_game_keyboard, admin_search_keyboard, games_menu_keyboard, player_game_keyboard
from app.renderers.game import render_admin_game, render_player_cards, render_player_game
from app.services.users import UserService


class GameService:
    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self.users = UserService(session)
        self.settings = get_settings()

    async def get_active_game(self, user_id: int) -> GameSession | None:
        return await self.session.scalar(
            select(GameSession).where(
                GameSession.user_id == user_id,
                GameSession.status.in_([GameStatus.SEARCHING, GameStatus.WAITING_OPPONENT_SETUP, GameStatus.ACTIVE]),
            )
        )

    async def create_search(self, user_id: int, stake: int) -> GameSession:
        active = await self.get_active_game(user_id)
        if active:
            raise ValueError("У вас уже есть активная игра")
        await self.users.remove_balance(user_id, stake, LedgerEntryType.BET_HOLD, "Ставка на игру")
        game = GameSession(user_id=user_id, stake=stake, deck=build_deck())
        self.session.add(game)
        await self.session.flush()
        return game

    async def cancel_search(self, game: GameSession) -> None:
        if game.status != GameStatus.SEARCHING:
            raise ValueError("Поиск уже завершен")
        game.status = GameStatus.CANCELED
        await self.users.add_balance(game.user_id, game.stake, LedgerEntryType.BET_REFUND, "Возврат ставки после отмены поиска")
        await self.session.flush()

    async def accept_game(self, game: GameSession, admin_id: int) -> GameSession:
        if game.status != GameStatus.SEARCHING:
            raise ValueError("Игра уже недоступна")
        now = utcnow()
        game.accepted_by_admin_id = admin_id
        game.status = GameStatus.WAITING_OPPONENT_SETUP
        game.admin_deadline_at = now + timedelta(minutes=1)
        game.player_deadline_at = None
        player_cards, deck = deal_from_deck(game.deck, 2)
        preview_cards, deck = deal_from_deck(deck, min(5, len(deck)))
        game.deck = deck
        game.player_cards = player_cards
        game.pending_player_cards = preview_cards
        await self.session.flush()
        await self._resolve_player_natural_after_deal(game)
        return game

    async def _resolve_player_natural_after_deal(self, game: GameSession) -> None:
        if len(game.player_cards) == 2 and sum(1 for card in game.player_cards if card_rank(card) == "A") == 2:
            game.status = GameStatus.PLAYER_WON
            await self.users.add_balance(game.user_id, game.stake * 2, LedgerEntryType.WIN, "Победа в BLACK JACK")
            await self.session.flush()
            await self.finish_notifications(game, "Победа")
            game.status = GameStatus.FINISHED
            await self.session.flush()
            await self.send_games_return_message(game.user_id)

    def _take_card_by_rank(self, deck: list[dict], rank: str, game: "GameSession | None" = None) -> tuple[dict, list[dict]]:
        updated = list(deck)
        for index, card in enumerate(updated):
            if card_rank(card) == rank:
                return updated.pop(index), updated
        # Нужного ранга нет в колоде — ищем карту того же ранга из каталога,
        # исключая все карты которые уже задействованы в игре
        used: set[tuple[str, str]] = set()
        if game is not None:
            for c in (*game.player_cards, *game.pending_player_cards, *game.opponent_cards, *updated):
                used.add((str(c["rank"]), str(c["suit"])))
        for catalog_card in CARD_CATALOG:
            key = (str(catalog_card["rank"]), str(catalog_card["suit"]))
            if card_rank(catalog_card) == rank and key not in used:
                return dict(catalog_card), updated
        raise ValueError(f"Карта ранга {rank} недоступна — все масти уже в игре")

    async def add_admin_card(self, game: GameSession, admin_id: int, rank: str) -> GameSession:
        if game.accepted_by_admin_id != admin_id:
            raise ValueError("Эта игра уже занята другим администратором")
        if game.status not in [GameStatus.WAITING_OPPONENT_SETUP, GameStatus.ACTIVE]:
            raise ValueError("Игра неактивна")
        selected_card, updated_deck = self._take_card_by_rank(game.deck, rank, game)
        game.deck = updated_deck
        game.opponent_cards = [*game.opponent_cards, selected_card]
        if calculate_points(game.opponent_cards) > 21:
            game.opponent_stopped = True
        if game.status == GameStatus.WAITING_OPPONENT_SETUP and len(game.opponent_cards) >= 2:
            now = utcnow()
            game.status = GameStatus.ACTIVE
            game.player_deadline_at = now + timedelta(minutes=1)
            game.admin_deadline_at = now + timedelta(minutes=1)
        await self.session.flush()
        await self.check_game_resolution(game)
        return game

    async def player_hit(self, game: GameSession) -> GameSession:
        if game.status != GameStatus.ACTIVE:
            raise ValueError("Игра недоступна")
        if game.player_stopped:
            raise ValueError("Ход уже завершен")
        if game.pending_player_cards:
            next_card = game.pending_player_cards.pop(0)
        else:
            cards, deck = deal_from_deck(game.deck, 1)
            if not cards:
                raise ValueError("Колода пуста")
            next_card = cards[0]
            game.deck = deck
        game.player_cards = [*game.player_cards, next_card]
        preview_fill = 5 - len(game.pending_player_cards)
        if preview_fill > 0 and game.deck:
            cards, deck = deal_from_deck(game.deck, preview_fill)
            game.pending_player_cards = [*game.pending_player_cards, *cards]
            game.deck = deck
        game.player_deadline_at = utcnow() + timedelta(minutes=1)
        if calculate_points(game.player_cards) > 21:
            game.player_stopped = True
        await self.session.flush()
        await self.check_game_resolution(game)
        return game

    async def player_stop(self, game: GameSession) -> GameSession:
        if game.status != GameStatus.ACTIVE:
            raise ValueError("Игра недоступна")
        game.player_stopped = True
        game.player_deadline_at = utcnow() + timedelta(minutes=1)
        await self.session.flush()
        await self.check_game_resolution(game)
        return game

    async def admin_stop(self, game: GameSession, admin_id: int) -> GameSession:
        if game.accepted_by_admin_id != admin_id:
            raise ValueError("Игра уже закреплена за другим администратором")
        game.opponent_stopped = True
        game.admin_deadline_at = utcnow() + timedelta(minutes=1)
        await self.session.flush()
        await self.check_game_resolution(game)
        return game

    async def check_game_resolution(self, game: GameSession) -> None:
        if game.status != GameStatus.ACTIVE:
            return
        force_finish = (
            (game.player_stopped and game.opponent_stopped)
            or (len(game.player_cards) == 2 and sum(1 for card in game.player_cards if card_rank(card) == "A") == 2)
            or (len(game.opponent_cards) == 2 and sum(1 for card in game.opponent_cards if card_rank(card) == "A") == 2)
        )
        if not force_finish:
            return

        result = resolve_round(game.player_cards, game.opponent_cards)
        if result.requires_reround:
            now = utcnow()
            game.round_number += 1
            game.deck = build_deck()
            player_cards, deck = deal_from_deck(game.deck, 2)
            preview_cards, deck = deal_from_deck(deck, min(5, len(deck)))
            game.deck = deck
            game.player_cards = player_cards
            game.opponent_cards = []
            game.pending_player_cards = preview_cards
            game.player_stopped = False
            game.opponent_stopped = False
            game.status = GameStatus.WAITING_OPPONENT_SETUP
            game.admin_deadline_at = now + timedelta(minutes=1)
            game.player_deadline_at = None
            await self.session.flush()
            await self._resolve_player_natural_after_deal(game)
            return

        if result.winner == "player":
            game.status = GameStatus.PLAYER_WON
            await self.users.add_balance(game.user_id, game.stake * 2, LedgerEntryType.WIN, "Победа в BLACK JACK")
            title = "Победа"
        else:
            game.status = GameStatus.PLAYER_LOST
            title = "Поражение"
        await self.session.flush()
        await self.finish_notifications(game, title)
        game.status = GameStatus.FINISHED
        await self.session.flush()
        await self.send_games_return_message(game.user_id)

    async def finish_notifications(self, game: GameSession, title: str) -> None:
        player_points = calculate_points(game.player_cards)
        opponent_points = calculate_points(game.opponent_cards)
        player_cards = format_cards(game.player_cards)
        opponent_cards = format_cards(game.opponent_cards)
        await self.safe_send_or_edit_player_main(
            game,
            game_result_text(title, player_points, opponent_points, player_cards, opponent_cards),
            None,
        )
        if game.user_cards_message_id:
            user = await self.session.scalar(select(User).where(User.id == game.user_id))
            if user:
                await self.safe_edit_message(
                    user.telegram_id,
                    game.user_cards_message_id,
                    f"Ваши карты: {player_cards}\nКарты соперника: {opponent_cards}",
                    None,
                )
        await send_admin_log(
            self.bot,
            f"🎯 Результат игры\n\nID: {game.id}\nСтавка: {game.stake} ⭐\nИтог: {title}\nСчет игрока: {player_points}\nСчет стола: {opponent_points}",
        )

    async def push_search_messages(self, game: GameSession, user: User, user_message_id: int) -> None:
        game.user_main_message_id = user_message_id
        player_name = f"@{user.username}" if user.username else str(user.telegram_id)
        admin_message = await self.bot.send_message(
            self.settings.admin_chat_id,
            f"🎮 Новая игра BLACK JACK\n\n👤 Игрок: {player_name}\n⭐ Ставка: {game.stake}",
            reply_markup=admin_search_keyboard(game.id),
        )
        game.admin_chat_message_id = admin_message.message_id
        await self.session.flush()

    async def render_game_views(self, game: GameSession) -> None:
        user = await self.session.scalar(select(User).where(User.id == game.user_id))
        if game.status == GameStatus.WAITING_OPPONENT_SETUP:
            await self.safe_send_or_edit_player_main(
                game,
                "<b>BLACK JACK ONLINE</b>\n\nИгра найдена. Подготовка игрового стола...",
                None,
            )
        elif game.status == GameStatus.ACTIVE:
            await self.safe_send_or_edit_player_main(game, render_player_game(game), player_game_keyboard(game.id))
            await self.safe_send_or_edit_player_cards(game, render_player_cards(game))

        if game.admin_chat_message_id:
            await self.safe_edit_message(
                self.settings.admin_chat_id,
                game.admin_chat_message_id,
                render_admin_game(game, user.username if user else None),
                admin_game_keyboard(game.id) if game.status in [GameStatus.WAITING_OPPONENT_SETUP, GameStatus.ACTIVE] else None,
            )

    async def safe_send_or_edit_player_main(
        self,
        game: GameSession,
        text: str,
        reply_markup: InlineKeyboardMarkup | None,
    ) -> None:
        user = await self.session.scalar(select(User).where(User.id == game.user_id))
        if not user:
            return
        if game.user_main_message_id:
            if await self.safe_edit_message(user.telegram_id, game.user_main_message_id, text, reply_markup):
                return
        message = await self.bot.send_message(user.telegram_id, text, reply_markup=reply_markup)
        game.user_main_message_id = message.message_id
        await self.session.flush()

    async def safe_send_or_edit_player_cards(self, game: GameSession, text: str) -> None:
        user = await self.session.scalar(select(User).where(User.id == game.user_id))
        if not user:
            return
        if game.user_cards_message_id:
            if await self.safe_edit_message(user.telegram_id, game.user_cards_message_id, text, None):
                return
        message = await self.bot.send_message(user.telegram_id, text)
        game.user_cards_message_id = message.message_id
        await self.session.flush()

    async def safe_edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None,
    ) -> bool:
        try:
            await self.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
            return True
        except TelegramBadRequest:
            return False

    async def process_timeouts(self) -> None:
        games = await self.session.scalars(
            select(GameSession).where(
                GameSession.status.in_([GameStatus.SEARCHING, GameStatus.WAITING_OPPONENT_SETUP, GameStatus.ACTIVE])
            )
        )
        now = utcnow()
        for game in list(games):
            if game.status == GameStatus.SEARCHING and game.search_expires_at <= now:
                await self.cancel_search(game)
                await self.safe_send_or_edit_player_main(
                    game,
                    "<b>Поиск отменен</b>\n\nСтавка возвращена на баланс.\nВозвращаем вас в меню игр.",
                    None,
                )
                await self.send_games_return_message(game.user_id)
            elif game.status in [GameStatus.WAITING_OPPONENT_SETUP, GameStatus.ACTIVE]:
                if game.player_deadline_at and game.player_deadline_at <= now and not game.player_stopped:
                    game.status = GameStatus.PLAYER_LOST
                    await self.finish_notifications(game, "Поражение")
                    game.status = GameStatus.FINISHED
                    await self.send_games_return_message(game.user_id)
                elif game.admin_deadline_at and game.admin_deadline_at <= now and not game.opponent_stopped:
                    game.status = GameStatus.PLAYER_WON
                    await self.users.add_balance(game.user_id, game.stake * 2, LedgerEntryType.WIN, "Победа по таймеру")
                    await self.finish_notifications(game, "Победа")
                    game.status = GameStatus.FINISHED
                    await self.send_games_return_message(game.user_id)
        await self.session.flush()

    async def send_games_return_message(self, user_id: int) -> None:
        user = await self.session.scalar(select(User).where(User.id == user_id))
        if not user:
            return
        wallet = await self.users.get_wallet(user_id)
        await self.bot.send_message(
            user.telegram_id,
            games_menu_text(wallet.balance_stars, None),
            reply_markup=games_menu_keyboard(),
        )

    async def log_admin_action(self, admin_id: int, action: str, details: str = "") -> None:
        self.session.add(AdminLog(admin_id=admin_id, action=action, details=details))
        await self.session.flush()
        await send_admin_log(self.bot, f"🛡 Действие админа\n\nАдмин: {admin_id}\nДействие: {action}\nДетали: {details or '—'}")
