import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties 
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers import common, broadcast


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("aiogram").setLevel(logging.DEBUG)

    # Сессия с SOCKS прокси
    session = AiohttpSession()
    if settings.proxy_url:
        session=AiohttpSession(proxy=settings.proxy_url)

    bot = Bot(token=settings.bot_token, session=session, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(broadcast.router)

    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

