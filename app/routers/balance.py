from __future__ import annotations

from uuid import uuid4

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy import select

from app.common.enums import LedgerEntryType, WithdrawalMethod
from app.common.text import balance_text, deposit_receipt_text
from app.config import get_settings
from app.db.models import Deposit, User
from app.db.session import SessionLocal
from app.keyboards.inline import (
    admin_withdrawal_keyboard,
    balance_keyboard,
    topup_keyboard,
    withdraw_all_keyboard,
    withdrawal_methods_keyboard,
)
from app.services.users import UserService
from app.services.withdrawals import WithdrawalService
from app.states.common import WithdrawalStates

router = Router()


async def _balance_message(message: Message) -> None:
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        wallet = await users.get_wallet(user.id)
        await session.commit()
    await message.answer(balance_text(wallet.balance_stars), reply_markup=balance_keyboard())


@router.message(F.text == "💰 Баланс")
async def balance_menu(message: Message) -> None:
    await _balance_message(message)


@router.callback_query(F.data == "balance:open")
async def balance_open(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        wallet = await users.get_wallet(user.id)
        await session.commit()
    await callback.message.answer(balance_text(wallet.balance_stars), reply_markup=balance_keyboard())
    await callback.answer()


@router.callback_query(F.data == "balance:topup")
async def balance_topup(callback: CallbackQuery) -> None:
    await callback.message.edit_text("<b>Пополнение</b>\n\nВыберите сумму:", reply_markup=topup_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("topup:"))
async def create_invoice(callback: CallbackQuery) -> None:
    amount = int(callback.data.split(":")[1])
    payload = f"topup:{callback.from_user.id}:{uuid4()}"
    settings = get_settings()
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        session.add(Deposit(user_id=user.id, amount=amount, invoice_payload=payload))
        await session.commit()
    await callback.message.answer_invoice(
        title=f"Пополнение BJOKER на {amount} ⭐",
        description="Пополнение игрового баланса",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Пополнение", amount=amount)],
        photo_url=settings.topup_photo_url or None,
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    payment = message.successful_payment
    payload = payment.invoice_payload
    async with SessionLocal() as session:
        deposit = await session.scalar(select(Deposit).where(Deposit.invoice_payload == payload))
        if not deposit:
            await session.rollback()
            return
        users = UserService(session)
        user = await session.scalar(select(User).where(User.id == deposit.user_id))
        if deposit.telegram_charge_id:
            return
        deposit.telegram_charge_id = payment.telegram_payment_charge_id
        await users.add_balance(user.id, deposit.amount, LedgerEntryType.TOPUP, "Пополнение через Telegram Stars")
        await session.commit()
        settings = get_settings()
        await message.answer(deposit_receipt_text(deposit.amount))
        await message.bot.send_message(
            settings.admin_chat_id,
            f"💰 Пополнение\n\n👤 Пользователь: @{user.username if user.username else user.telegram_id}\n⭐ Сумма: {deposit.amount}",
        )


@router.callback_query(F.data == "balance:withdraw")
async def withdraw_open(callback: CallbackQuery, state: FSMContext) -> None:
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        wallet = await users.get_wallet(user.id)
        await session.commit()
    if wallet.balance_stars < 1:
        await callback.answer("❌ Вам нечего выводить", show_alert=True)
        return
    if wallet.balance_stars < 250:
        await callback.answer("❌ Вывод доступен от 250 ⭐", show_alert=True)
        return
    await callback.message.edit_text("Куда хотите вывести?", reply_markup=withdrawal_methods_keyboard())
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("withdraw:method:"))
async def withdraw_method(callback: CallbackQuery, state: FSMContext) -> None:
    method = callback.data.rsplit(":", 1)[-1]
    await state.update_data(method=method)
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        wallet = await users.get_wallet(user.id)
        await session.commit()
    await callback.message.edit_text(
        "Укажите сумму вывода.\n\nАктуальный баланс: "
        f"<b>{wallet.balance_stars} ⭐</b>",
        reply_markup=withdraw_all_keyboard(),
    )
    await state.set_state(WithdrawalStates.waiting_for_amount)
    await callback.answer()


@router.callback_query(F.data == "withdraw:all")
async def withdraw_all(callback: CallbackQuery, state: FSMContext) -> None:
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
        wallet = await users.get_wallet(user.id)
        await session.commit()
    await state.update_data(amount=wallet.balance_stars)
    await state.set_state(WithdrawalStates.waiting_for_requisites)
    await callback.message.answer("Укажите реквизиты для вывода.")
    await callback.answer()


@router.message(WithdrawalStates.waiting_for_amount)
async def withdraw_amount(message: Message, state: FSMContext) -> None:
    if not (message.text or "").isdigit():
        await message.answer("Введите сумму числом.")
        return
    amount = int(message.text)
    await state.update_data(amount=amount)
    await state.set_state(WithdrawalStates.waiting_for_requisites)
    await message.answer("Укажите реквизиты для вывода.")


@router.message(WithdrawalStates.waiting_for_requisites)
async def withdraw_requisites(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    amount = data["amount"]
    method = WithdrawalMethod(data["method"])
    async with SessionLocal() as session:
        users = UserService(session)
        user = await users.get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        service = WithdrawalService(session)
        try:
            request = await service.create(user.id, amount, method, message.text or "")
        except ValueError as exc:
            await message.answer(str(exc))
            await session.rollback()
            return
        await session.commit()
        settings = get_settings()
        await message.answer("Заявка на вывод создана.")
        await message.bot.send_message(
            settings.admin_chat_id,
            (
                "💸 Новая заявка на вывод\n\n"
                f"👤 Пользователь: @{message.from_user.username or message.from_user.id}\n"
                f"⭐ Сумма: {request.amount}\n"
                f"💳 Способ: {request.method.value.upper()}\n"
                f"📄 Реквизиты: {request.requisites}"
            ),
            reply_markup=admin_withdrawal_keyboard(request.id),
        )
    await state.clear()