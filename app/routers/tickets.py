from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.common.admin_notifier import send_ticket_payload_to_admin
from app.db.session import SessionLocal
from app.keyboards.inline import ticket_open_keyboard
from app.services.tickets import TicketService
from app.services.users import UserService
from app.states.common import TicketStates

router = Router()

MENU_TEXTS = {"🎲 Игры", "👤 Профиль", "💰 Баланс", "📖 Помощь"}
MEDIA_GROUP_BUFFER_SECONDS = 1.0
MEDIA_GROUPS: dict[str, dict] = {}


def message_body(message: Message) -> str | None:
    return message.text or message.caption


def extract_media(message: Message) -> list[dict]:
    media: list[dict] = []
    if message.photo:
        media.append({"type": "photo", "file_id": message.photo[-1].file_id, "group_id": message.media_group_id})
    if message.video:
        media.append({"type": "video", "file_id": message.video.file_id, "group_id": message.media_group_id})
    if message.document:
        media.append({"type": "document", "file_id": message.document.file_id, "group_id": message.media_group_id})
    return media


async def flush_media_group(key: str) -> None:
    await asyncio.sleep(MEDIA_GROUP_BUFFER_SECONDS)
    payload = MEDIA_GROUPS.pop(key, None)
    if not payload:
        return

    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(
            payload["telegram_id"],
            payload["username"],
            payload["first_name"],
        )
        service = TicketService(session)
        body = payload["text"]
        media = payload["media"]

        if payload["mode"] == "create":
            try:
                ticket = await service.create_ticket(user.id, body, media)
            except ValueError:
                await session.rollback()
                await payload["bot"].send_message(payload["chat_id"], "У вас уже есть открытый тикет.")
                return
            await session.commit()
            await payload["bot"].send_message(payload["chat_id"], "Обращение создано.", reply_markup=ticket_open_keyboard(ticket.id))
            await send_ticket_payload_to_admin(
                payload["bot"],
                f"📩 Новое обращение\n\n👤 Пользователь: @{payload['username'] or payload['telegram_id']}\n🎫 Тикет #{ticket.id}",
                body,
                media,
            )
            return

        ticket = await service.get_open_ticket(user.id)
        if not ticket:
            await session.commit()
            return
        await service.append_user_message(ticket.id, user.id, body, media)
        await session.commit()
        await send_ticket_payload_to_admin(
            payload["bot"],
            f"📨 Новое сообщение в тикете #{ticket.id}\n\n👤 Пользователь: @{payload['username'] or payload['telegram_id']}",
            body,
            media,
        )
        await payload["bot"].send_message(payload["chat_id"], "Сообщение добавлено в тикет.")


def schedule_media_group(message: Message, mode: str) -> None:
    group_id = message.media_group_id
    if not group_id:
        return
    key = f"{mode}:{message.from_user.id}:{group_id}"
    payload = MEDIA_GROUPS.get(key)
    text = message_body(message)
    media = extract_media(message)
    if payload is None:
        payload = {
            "mode": mode,
            "bot": message.bot,
            "chat_id": message.chat.id,
            "telegram_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "text": text,
            "media": media,
        }
        payload["task"] = asyncio.create_task(flush_media_group(key))
        MEDIA_GROUPS[key] = payload
        return

    if not payload["text"] and text:
        payload["text"] = text
    payload["media"].extend(media)


@router.callback_query(F.data == "ticket:create")
async def ticket_create(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TicketStates.waiting_for_message)
    await callback.message.answer(
        "Опишите проблему максимально подробно.\nМожно приложить фото, видео или текст одним сообщением."
    )
    await callback.answer()


@router.callback_query(F.data == "ticket:list")
async def ticket_list(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        tickets = await TicketService(session).list_user_tickets(user.id)
        await session.commit()
    if not tickets:
        await callback.message.answer("Обращений пока нет.")
    for ticket in tickets[:10]:
        await callback.message.answer(
            f"Тикет #{ticket.id}\nСтатус: {ticket.status.value}",
            reply_markup=ticket_open_keyboard(ticket.id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:open:"))
async def ticket_open(callback: CallbackQuery) -> None:
    ticket_id = int(callback.data.split(":")[2])
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        service = TicketService(session)
        ticket = await service.get_by_id(ticket_id)
        if not ticket or ticket.user_id != user.id:
            await session.commit()
            await callback.answer("Тикет не найден", show_alert=True)
            return
        history = await service.history(ticket_id)
        await session.commit()
    if not history:
        await callback.answer("История пуста", show_alert=True)
        return
    lines = []
    for item in history[-20:]:
        prefix = "Тех поддержка" if item.sender_admin_id else "user"
        time_str = item.created_at.strftime("%H:%M")
        body = item.text or "[медиа]"
        lines.append(f"[{time_str}] {prefix}: {body}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.message(TicketStates.waiting_for_message)
async def ticket_first_message(message: Message, state: FSMContext) -> None:
    if message.media_group_id:
        schedule_media_group(message, "create")
        await state.clear()
        return

    media = extract_media(message)
    body = message_body(message)
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        service = TicketService(session)
        try:
            ticket = await service.create_ticket(user.id, body, media)
        except ValueError as exc:
            await message.answer(str(exc))
            await session.rollback()
            return
        await session.commit()
        await message.answer("Обращение создано.", reply_markup=ticket_open_keyboard(ticket.id))
        await send_ticket_payload_to_admin(
            message.bot,
            f"📩 Новое обращение\n\n👤 Пользователь: @{message.from_user.username or message.from_user.id}\n🎫 Тикет #{ticket.id}",
            body,
            media,
        )
    await state.clear()


@router.message(F.text | F.photo | F.video | F.document)
async def active_ticket_stream(message: Message, state: FSMContext) -> None:
    if (message.text or "") in MENU_TEXTS:
        return
    if (message.text or "").startswith("/"):
        return
    if await state.get_state() == TicketStates.waiting_for_message.state:
        return

    if message.media_group_id:
        schedule_media_group(message, "append")
        return

    media = extract_media(message)
    body = message_body(message)
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        service = TicketService(session)
        ticket = await service.get_open_ticket(user.id)
        if not ticket:
            await session.commit()
            return
        await service.append_user_message(ticket.id, user.id, body, media)
        await session.commit()
        await send_ticket_payload_to_admin(
            message.bot,
            f"📨 Новое сообщение в тикете #{ticket.id}\n\n👤 Пользователь: @{message.from_user.username or message.from_user.id}",
            body,
            media,
        )
        await message.answer("Сообщение добавлено в тикет.")
