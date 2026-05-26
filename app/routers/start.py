from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.common.text import MAIN_MENU_TEXT
from app.db.session import SessionLocal
from app.keyboards.reply import main_menu_keyboard
from app.services.users import UserService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with SessionLocal() as session:
        users = UserService(session)
        await users.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        await session.commit()
    await message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())

