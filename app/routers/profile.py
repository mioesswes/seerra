from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.common.text import profile_text
from app.config import get_settings
from app.db.session import SessionLocal
from app.keyboards.inline import profile_keyboard
from app.services.users import UserService

router = Router()


async def _send_profile(from_user_id: int, from_user_username: str | None, from_user_first_name: str | None, target: Message) -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(from_user_id, from_user_username, from_user_first_name)
        wallet = await users.get_wallet(user.id)
        stats = await users.stats(user.id)
        await session.commit()

    text = profile_text(from_user_username or "", from_user_id, wallet.balance_stars, stats)

    if Path(settings.profile_image_path).exists():
        await target.answer_photo(
            FSInputFile(settings.profile_image_path),
            caption=text,
            reply_markup=profile_keyboard(),
        )
    else:
        await target.answer(text, reply_markup=profile_keyboard())


@router.message(F.text == "👤 Профиль")
async def profile_menu(message: Message) -> None:
    await _send_profile(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message,
    )


@router.callback_query(F.data == "profile:open")
async def profile_callback(callback: CallbackQuery) -> None:
    await _send_profile(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
        callback.message,
    )
    await callback.answer()