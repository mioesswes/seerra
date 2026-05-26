from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Игры"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📖 Помощь")],
        ],
        resize_keyboard=True,
    )

