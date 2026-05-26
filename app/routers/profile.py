from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from app.common.text import profile_text
from app.config import get_settings
from app.db.session import SessionLocal
from app.keyboards.inline import profile_cover_keyboard, profile_keyboard
from app.services.users import UserService

router = Router()


async def _send_profile(message: Message) -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        wallet = await users.get_wallet(user.id)
        stats = await users.stats(user.id)
        await session.commit()

    if Path(settings.profile_image_path).exists():
        await message.answer_photo(FSInputFile(settings.profile_image_path), reply_markup=profile_cover_keyboard())
    await message.answer(
        profile_text(message.from_user.username or "", message.from_user.id, wallet.balance_stars, stats),
        reply_markup=profile_keyboard(),
    )


@router.message(F.text == "👤 Профиль")
async def profile_menu(message: Message) -> None:
    await _send_profile(message)


@router.callback_query(F.data == "profile:open")
async def profile_callback(callback: CallbackQuery) -> None:
    await _send_profile(callback.message)
    await callback.answer()


@router.callback_query(F.data == "profile:refresh_media")
async def profile_refresh_media(callback: CallbackQuery) -> None:
    settings = get_settings()
    if not callback.message:
        await callback.answer()
        return
    if not Path(settings.profile_image_path).exists():
        await callback.answer("Файл profile.jpg не найден", show_alert=True)
        return
    await callback.message.edit_media(
        media=InputMediaPhoto(media=FSInputFile(settings.profile_image_path)),
        reply_markup=profile_cover_keyboard(),
    )
    await callback.answer("Обложка обновлена")
