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


def premium(emoji_id: str, fallback: str, text: str = "") -> str:
    """Обёртка для premium tg-emoji."""
    tag = f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return f"{tag} {text}".strip() if text else tag


# ── Premium emoji IDs ──────────────────────────────────────────────────────────
_E_PROFILE   = "5417915203100613993"   # 👤
_E_ID        = "5368324170671202286"   # 🪪
_E_BALANCE   = "5447644880824181073"   # ⭐
_E_STATS     = "5440539497383087970"   # 📊
_E_GAMES     = "5441499466327715830"   # 🎮
_E_WIN       = "5445284980978621387"   # 💰
_E_BET       = "5441367794639626656"   # 🎯
_E_STAR      = "5447644880824181073"   # ⭐  (inline)


def profile_text(username: str, telegram_id: int, balance: int, stats: dict[str, int]) -> str:
    name = f"@{username}" if username else "без username"
    return (
        f"{premium(_E_PROFILE, '👤')} <b>Профиль:</b> {name}\n"
        f"{premium(_E_ID, '🪪')} <b>ID:</b> <code>{telegram_id}</code>\n"
        f"{premium(_E_BALANCE, '⭐')} <b>Баланс:</b> <b>{balance}</b> {premium(_E_STAR, '⭐')}\n\n"
        f"{premium(_E_STATS, '📊')} <b>Статистика игр</b>\n"
        f"Всего игр: <b>{stats['games_total']}</b>\n"
        f"Общий выигрыш: <b>{stats['gross_wins']}</b> {premium(_E_WIN, '💰')}\n"
        f"Максимальный выигрыш: <b>{stats['max_win']}</b> {premium(_E_WIN, '💰')}\n"
        f"Максимальная ставка: <b>{stats['max_bet']}</b> {premium(_E_BET, '🎯')}"
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