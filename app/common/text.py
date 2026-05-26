from __future__ import annotations

from app.config import Settings


MAIN_MENU_TEXT = (
    "<b>Добро пожаловать в BJOKER</b>\n\n"
    "Премиальный стол, быстрые действия, динамичные экраны и игра в стиле dark casino."
)


HELP_TEXT = (
    "<b>BLACK JACK ONLINE</b>\n\n"
    "Вам необходимо набрать <b>21 очко</b> или максимально приблизиться к этому значению.\n"
    "Если сумма ваших карт превышает <b>21 очко</b>, это считается <b>перебором</b>.\n\n"
    "<b>Подсчёт очков:</b>\n"
    "2-10 — по номиналу\n"
    "Валет — 2\n"
    "Дама — 3\n"
    "Король — 4\n"
    "Туз — 11\n\n"
    "<b>Особое правило:</b>\n"
    "Два туза = 21 очко.\n\n"
    "Если по итогам раунда результат одинаковый, запускается следующий раунд с той же ставкой."
)


def premium(value: str, emoji_id: str | None = None, fallback: str = "⭐") -> str:
    if not emoji_id:
        return f"{fallback} {value}".strip()
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>{value}'


def profile_text(username: str, telegram_id: int, balance: int, stats: dict[str, int]) -> str:
    name = f"@{username}" if username else "без username"
    return (
        "<b>Профиль игрока</b>\n\n"
        f"Пользователь: {name}\n"
        f"ID: <code>{telegram_id}</code>\n"
        f"Баланс: <b>{balance} ⭐</b>\n\n"
        "<b>Статистика игр</b>\n"
        f"Всего игр: {stats['games_total']}\n"
        f"Общий выигрыш: {stats['gross_wins']} ⭐\n"
        f"Максимальный выигрыш: {stats['max_win']} ⭐\n"
        f"Максимальная ставка: {stats['max_bet']} ⭐"
    )


def balance_text(balance: int) -> str:
    return (
        "<b>Баланс</b>\n\n"
        f"Текущий баланс: <b>{balance} ⭐</b>\n"
        "Выберите действие ниже."
    )


def games_menu_text(balance: int, stake: int | None = None) -> str:
    stake_block = (
        f"\nТекущая ставка: <b>{stake} ⭐</b>"
        if stake
        else "\nТекущая ставка: <b>не выбрана</b>"
    )
    return (
        "<b>Игровое меню</b>\n\n"
        f"Баланс: <b>{balance} ⭐</b>"
        f"{stake_block}\n\n"
        "Выберите игру."
    )


def game_search_text(stake: int) -> str:
    return (
        "<b>BLACK JACK ONLINE</b>\n\n"
        f"Ставка: <b>{stake} ⭐</b>\n"
        "Поиск игры запущен.\n\n"
        "⏳ Поиск..."
    )


def game_result_text(
    title: str,
    player_points: int,
    opponent_points: int,
    player_cards: str,
    opponent_cards: str,
) -> str:
    return (
        f"<b>{title}</b>\n\n"
        f"Ваш счёт: <b>{player_points}</b>\n"
        f"Счёт соперника: <b>{opponent_points}</b>\n"
        f"Ваши карты: {player_cards}\n"
        f"Карты соперника: {opponent_cards}"
    )


def deposit_receipt_text(amount: int) -> str:
    return (
        "<b>Пополнение зачислено</b>\n\n"
        f"Сумма: <b>{amount} ⭐</b>\n"
        "Средства уже доступны в вашем балансе."
    )


def admin_payment_log(username: str | None, telegram_id: int, amount: int) -> str:
    name = f"@{username}" if username else str(telegram_id)
    return f"💰 Пополнение\n\n👤 Пользователь: {name}\n⭐ Сумма: {amount}"


def build_help_menu(settings: Settings) -> str:
    return (
        f"<b>{settings.bot_name} — помощь</b>\n\n"
        f"{HELP_TEXT}\n\n"
        "Если возникла проблема, создайте обращение в поддержку."
    )
