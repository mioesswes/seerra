from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def games_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎰 BLACK JACK", callback_data="games:blackjack")],
            [
                InlineKeyboardButton(text="🛠 Дартс", callback_data="games:soon"),
                InlineKeyboardButton(text="🛠 Баскет", callback_data="games:soon"),
                InlineKeyboardButton(text="🛠 Футбол", callback_data="games:soon"),
            ],
            [
                InlineKeyboardButton(text="🛠 Боулинг", callback_data="games:soon"),
                InlineKeyboardButton(text="🛠 Пирамида", callback_data="games:soon"),
            ],
            [
                InlineKeyboardButton(text="🛠 Мины", callback_data="games:soon"),
                InlineKeyboardButton(text="🛠 Слоты", callback_data="games:soon"),
            ],
        ]
    )


def stake_keyboard(selected_amount: int | None = None) -> InlineKeyboardMarkup:
    amounts = [100, 250, 500, 1000, 5000, 10000]
    rows: list[list[InlineKeyboardButton]] = []
    for idx in range(0, len(amounts), 2):
        chunk = amounts[idx : idx + 2]
        rows.append(
            [InlineKeyboardButton(text=f"{amount} ⭐", callback_data=f"stake:{amount}") for amount in chunk]
        )
    if selected_amount is not None:
        rows.append([InlineKeyboardButton(text="▶️ Начать поиск", callback_data=f"game:start:{selected_amount}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def searching_keyboard(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить поиск", callback_data=f"game:cancel:{game_id}")]]
    )


def admin_search_keyboard(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Принять", callback_data=f"admin:accept:{game_id}")]]
    )


def processing_keyboard(text: str = "⏳ Обновление...") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data="noop")]]
    )


def player_game_keyboard(game_id: str, locked: bool = False) -> InlineKeyboardMarkup:
    if locked:
        return processing_keyboard()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅➕", callback_data=f"play:hit:{game_id}"),
                InlineKeyboardButton(text="➖❌", callback_data=f"play:stop:{game_id}"),
            ]
        ]
    )


def admin_game_keyboard(game_id: str, locked: bool = False) -> InlineKeyboardMarkup:
    if locked:
        return processing_keyboard("⏳ Ход обрабатывается...")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="К", callback_data=f"admincard:{game_id}:K"),
                InlineKeyboardButton(text="В", callback_data=f"admincard:{game_id}:J"),
                InlineKeyboardButton(text="Д", callback_data=f"admincard:{game_id}:Q"),
                InlineKeyboardButton(text="Т", callback_data=f"admincard:{game_id}:A"),
                InlineKeyboardButton(text="🛑", callback_data=f"adminstop:{game_id}"),
            ],
            [
                InlineKeyboardButton(text="10", callback_data=f"admincard:{game_id}:10"),
                InlineKeyboardButton(text="9", callback_data=f"admincard:{game_id}:9"),
                InlineKeyboardButton(text="8", callback_data=f"admincard:{game_id}:8"),
                InlineKeyboardButton(text="7", callback_data=f"admincard:{game_id}:7"),
                InlineKeyboardButton(text="6", callback_data=f"admincard:{game_id}:6"),
            ],
            [
                InlineKeyboardButton(text="5", callback_data=f"admincard:{game_id}:5"),
                InlineKeyboardButton(text="4", callback_data=f"admincard:{game_id}:4"),
                InlineKeyboardButton(text="3", callback_data=f"admincard:{game_id}:3"),
                InlineKeyboardButton(text="2", callback_data=f"admincard:{game_id}:2"),
            ],
        ]
    )


def balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Пополнить", callback_data="balance:topup")],
            [InlineKeyboardButton(text="💸 Вывод", callback_data="balance:withdraw")],
        ]
    )


def topup_keyboard() -> InlineKeyboardMarkup:
    amounts = [100, 250, 500, 1000, 5000, 10000]
    rows: list[list[InlineKeyboardButton]] = []
    for idx in range(0, len(amounts), 2):
        chunk = amounts[idx : idx + 2]
        rows.append(
            [InlineKeyboardButton(text=f"{amount} ⭐", callback_data=f"topup:{amount}") for amount in chunk]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def withdrawal_methods_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ STARS", callback_data="withdraw:method:stars")],
            [InlineKeyboardButton(text="💎 USDT", callback_data="withdraw:method:usdt")],
            [InlineKeyboardButton(text="💠 TON", callback_data="withdraw:method:ton")],
            [InlineKeyboardButton(text="🏦 СБП", callback_data="withdraw:method:sbp")],
        ]
    )


def withdraw_all_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💸 Вывести всё", callback_data="withdraw:all")]]
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="balance:open")]]
    )


def profile_cover_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔄 Обновить", callback_data="profile:refresh_media")]]
    )


def help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📂 Список обращений", callback_data="ticket:list")],
            [InlineKeyboardButton(text="➕ Создать обращение", callback_data="ticket:create")],
        ]
    )


def ticket_open_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"🎫 #{ticket_id}", callback_data=f"ticket:open:{ticket_id}")]]
    )


def admin_withdrawal_keyboard(withdrawal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Завершен", callback_data=f"withdraw:done:{withdrawal_id}")]]
    )


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="🎮 Активные игры", callback_data="admin:games")],
            [InlineKeyboardButton(text="🎫 Тикеты", callback_data="admin:tickets")],
        ]
    )
