from __future__ import annotations

from aiogram import Bot
from aiogram.types import InputMediaPhoto, InputMediaVideo

from app.config import get_settings


async def send_admin_log(bot: Bot, text: str) -> None:
    await bot.send_message(get_settings().admin_chat_id, text[:4096])


async def send_admin_error(bot: Bot, text: str) -> None:
    await bot.send_message(get_settings().admin_chat_id, f"⚠️ Ошибка\n\n{text[:4000]}")


async def send_ticket_payload_to_admin(
    bot: Bot,
    header: str,
    text: str | None,
    media: list[dict],
) -> None:
    chat_id = get_settings().admin_chat_id
    caption_parts = [header]
    if text:
        caption_parts.append(text)
    caption = "\n\n".join(caption_parts)

    if media:
        media_types = {item["type"] for item in media}
        prepared = []
        for item in media[:10]:
            if item["type"] == "photo":
                prepared.append(InputMediaPhoto(media=item["file_id"]))
            elif item["type"] == "video":
                prepared.append(InputMediaVideo(media=item["file_id"]))
        if len(prepared) >= 2 and media_types.issubset({"photo", "video"}):
            prepared[0].caption = caption[:1024]
            await bot.send_media_group(chat_id, prepared)
            return
        if len(prepared) == 1 and media_types.issubset({"photo", "video"}):
            single = prepared[0]
            single.caption = caption[:1024]
            if isinstance(single, InputMediaPhoto):
                await bot.send_photo(chat_id, photo=single.media, caption=single.caption)
                return
            if isinstance(single, InputMediaVideo):
                await bot.send_video(chat_id, video=single.media, caption=single.caption)
                return
        for index, item in enumerate(media[:10]):
            current_caption = caption[:1024] if index == 0 else None
            if item["type"] == "photo":
                await bot.send_photo(chat_id, photo=item["file_id"], caption=current_caption)
            elif item["type"] == "video":
                await bot.send_video(chat_id, video=item["file_id"], caption=current_caption)
            elif item["type"] == "document":
                await bot.send_document(chat_id, document=item["file_id"], caption=current_caption)
        return

    await bot.send_message(chat_id, caption[:4096])
