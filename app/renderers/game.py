from __future__ import annotations

from datetime import datetime, timezone

from app.domain.blackjack import calculate_points, card_admin_label, format_cards, hidden_cards


def _seconds_left(deadline: datetime | None) -> int:
    if not deadline:
        return 0
    delta = int((deadline - datetime.now(timezone.utc)).total_seconds())
    return max(delta, 0)


def _clock(deadline: datetime | None) -> str:
    seconds = _seconds_left(deadline)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def render_player_game(game) -> str:
    return (
        "<b>BLACK JACK ONLINE</b>\n\n"
        f"У соперника: {hidden_cards(len(game.opponent_cards) or 2)}\n"
        f"Время: <b>{_clock(game.player_deadline_at)}</b>\n"
        f"Счёт: <b>{calculate_points(game.player_cards)}</b>\n"
    )


def render_player_cards(game) -> str:
    return format_cards(game.player_cards)


def render_admin_game(game, username: str | None) -> str:
    preview = " ".join(card_admin_label(card) for card in game.pending_player_cards[:5]) if game.pending_player_cards else "—"
    player_name = f"@{username}" if username else "без username"
    own_cards = " ".join(card_admin_label(card) for card in game.opponent_cards) if game.opponent_cards else "—"
    return (
        "<b>Управление игрой</b>\n\n"
        f"Игрок: {player_name}"
        f"\nРаунд: {game.round_number}"
        f"\nСтавка: {game.stake} ⭐"
        f"\nВремя игрока: {_clock(game.player_deadline_at)}"
        f"\nВремя стола: {_clock(game.admin_deadline_at)}"
        f"\nКарты игрока: {format_cards(game.player_cards)}"
        f"\nОчки игрока: {calculate_points(game.player_cards)}"
        f"\nСледующие карты игрока: {preview}"
        f"\nВаши карты: {own_cards}"
        f"\nВаши очки: {calculate_points(game.opponent_cards)}"
        f"\nСтоп игрока: {'да' if game.player_stopped else 'нет'}"
        f"\nСтоп стола: {'да' if game.opponent_stopped else 'нет'}"
    )
