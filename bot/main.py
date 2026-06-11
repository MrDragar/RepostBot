import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.handlers import common, broadcast


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("aiogram").setLevel(logging.WARNING)

    # Сессия с SOCKS прокси
    session = AiohttpSession()
    if settings.proxy_url:
        from aiohttp_socks import ProxyConnector
        session.connector = ProxyConnector.from_url(settings.proxy_url)
        logging.info(f"Используем SOCKS прокси: {settings.proxy_url[:30]}...")

    bot = Bot(token=settings.bot_token, session=session)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(broadcast.router)

    # Очищаем webhook и стартуем polling
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
