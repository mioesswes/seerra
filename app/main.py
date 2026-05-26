from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from sqlalchemy import select

from app.common.admin_notifier import send_admin_error
from app.common.enums import GameStatus
from app.config import get_settings
from app.db.models import GameSession
from app.db.session import SessionLocal, init_db
from app.routers import admin, balance, games, help as help_router, profile, start, tickets
from app.services.games import GameService


async def background_game_worker(bot: Bot) -> None:
    while True:
        async with SessionLocal() as session:
            service = GameService(session, bot)
            try:
                await service.process_timeouts()
                result = await session.scalars(
                    select(GameSession).where(
                        GameSession.status == GameStatus.ACTIVE
                    )
                )
                for game in list(result):
                    await service.render_game_views(game)
                await session.commit()
            except Exception:
                await session.rollback()
                logging.exception("Background worker error")
                await send_admin_error(bot, "Сбой фонового игрового воркера. Проверьте приложение и логи.")
        await asyncio.sleep(10)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    await init_db()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(balance.router)
    dp.include_router(help_router.router)
    dp.include_router(games.router)
    dp.include_router(tickets.router)
    dp.include_router(admin.router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запуск"),
            BotCommand(command="admin", description="Админ-панель"),
            BotCommand(command="credit", description="Начислить баланс"),
            BotCommand(command="debit", description="Списать баланс"),
            BotCommand(command="reply_ticket", description="Ответить на тикет"),
        ]
    )

    worker = asyncio.create_task(background_game_worker(bot))
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
