from aiogram import F, Router
from aiogram.types import Message

from app.common.text import build_help_menu
from app.config import get_settings
from app.keyboards.inline import help_keyboard

router = Router()


@router.message(F.text == "📖 Помощь")
async def help_menu(message: Message) -> None:
    await message.answer(build_help_menu(get_settings()), reply_markup=help_keyboard())

