from __future__ import annotations

import random
from dataclasses import dataclass


Card = dict[str, str | int]

RANK_ORDER = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]
FULL_INPUT_ORDER = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]
RANK_TO_POINTS = {
    "A": 11,
    "K": 4,
    "Q": 3,
    "J": 2,
    "10": 10,
    "9": 9,
    "8": 8,
    "7": 7,
    "6": 6,
    "5": 5,
    "4": 4,
    "3": 3,
    "2": 2,
}
SUIT_FALLBACK = {
    "hearts": "♥️",
    "spades": "♠️",
    "diamonds": "♦️",
    "clubs": "♣️",
}
RANK_TO_ADMIN_LABEL = {
    "A": "Т(11)",
    "K": "К(4)",
    "Q": "Д(3)",
    "J": "В(2)",
    "10": "10",
    "9": "9",
    "8": "8",
    "7": "7",
    "6": "6",
    "5": "5",
    "4": "4",
    "3": "3",
    "2": "2",
}

SUIT_INPUTS = {
    "hearts": [
        "5235764579220361760",
        "5235523322317414425",
        "5235503986374645112",
        "5235768522000342664",
        "5235739775784231500",
        "5235561796634453978",
        "5235843795597170443",
        "5235462711738950893",
        "5235816969231438603",
        "5235942304967073100",
        "5235852647524766259",
        "5235698462493807012",
        "5235709616523874904",
    ],
    "spades": [
        "5235929278331262823",
        "5235450625700961905",
        "5235920675511774157",
        "5235873370741969954",
        "5235599021116006994",
        "5233365358949212356",
        "5235860588919299874",
        "5233203546056336959",
        "5235984915337616665",
        "5235497797326769656",
        "5235724429866081871",
        "5235813400113617605",
        "5235898973042024501",
    ],
    "diamonds": [
        "5235657746203840811",
        "5235542568065868927",
        "5235948159007498516",
        "5235937060812003405",
        "5235573844017715872",
        "5233207669224939838",
        "5235579564914154432",
        "5235864381375421692",
        "5235973765602517909",
        "5235951122534933460",
        "5235887041622874882",
        "5235798762865071838",
        "5235577507624820382",
    ],
    "clubs": [
        "5233613509274673198",
        "5235747609804579684",
        "5233468704452297640",
        "5235749920496984566",
        "5235790722686296424",
        "5235516029462949703",
        "5235478568758187692",
        "5235771910729538813",
        "5235666512232092784",
        "5235478049067144660",
        "5235464180617749717",
        "5235843142762144771",
        "5235715655247892410",
    ],
}


def _build_card_catalog() -> list[Card]:
    cards: list[Card] = []
    for suit, ids in SUIT_INPUTS.items():
        by_rank = dict(zip(FULL_INPUT_ORDER, ids, strict=True))
        for rank in RANK_ORDER:
            cards.append(
                {
                    "rank": rank,
                    "suit": suit,
                    "emoji_id": by_rank[rank],
                    "value": RANK_TO_POINTS[rank],
                }
            )
    return cards


CARD_CATALOG = _build_card_catalog()


def build_deck() -> list[Card]:
    deck = [dict(card) for card in CARD_CATALOG]
    random.shuffle(deck)
    return deck


def deal_from_deck(deck: list[Card], count: int = 1) -> tuple[list[Card], list[Card]]:
    cards = deck[:count]
    rest = deck[count:]
    return cards, rest


def card_points(card: Card) -> int:
    return int(card["value"])


def card_rank(card: Card) -> str:
    return str(card["rank"])


def card_admin_label(card: Card) -> str:
    return RANK_TO_ADMIN_LABEL[card_rank(card)]


def calculate_points(cards: list[Card]) -> int:
    if len(cards) == 2 and sum(1 for card in cards if card_rank(card) == "A") == 2:
        return 21
    return sum(card_points(card) for card in cards)


def is_bust(cards: list[Card]) -> bool:
    return calculate_points(cards) > 21


def format_card(card: Card) -> str:
    fallback = SUIT_FALLBACK[str(card["suit"])]
    return f'<tg-emoji emoji-id="{card["emoji_id"]}">{fallback}</tg-emoji>'


def format_cards(cards: list[Card]) -> str:
    return " ".join(format_card(card) for card in cards) if cards else "🃏"


def hidden_cards(count: int) -> str:
    return " ".join(["🃏"] * count) if count else "—"


@dataclass(slots=True)
class RoundResult:
    winner: str | None
    player_points: int
    opponent_points: int
    requires_reround: bool


def resolve_round(player_cards: list[Card], opponent_cards: list[Card]) -> RoundResult:
    player_points = calculate_points(player_cards)
    opponent_points = calculate_points(opponent_cards)
    player_bust = player_points > 21
    opponent_bust = opponent_points > 21

    if len(player_cards) == 2 and sum(1 for card in player_cards if card_rank(card) == "A") == 2:
        return RoundResult("player", player_points, opponent_points, False)
    if len(opponent_cards) == 2 and sum(1 for card in opponent_cards if card_rank(card) == "A") == 2:
        return RoundResult("opponent", player_points, opponent_points, False)

    if player_bust and opponent_bust:
        if player_points == opponent_points:
            return RoundResult(None, player_points, opponent_points, True)
        if player_points < opponent_points:
            return RoundResult("player", player_points, opponent_points, False)
        return RoundResult("opponent", player_points, opponent_points, False)

    if player_bust:
        return RoundResult("opponent", player_points, opponent_points, False)
    if opponent_bust:
        return RoundResult("player", player_points, opponent_points, False)

    if player_points == opponent_points:
        return RoundResult(None, player_points, opponent_points, True)
    if player_points > opponent_points:
        return RoundResult("player", player_points, opponent_points, False)
    return RoundResult("opponent", player_points, opponent_points, False)
