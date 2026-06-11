import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Callable, Awaitable
from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest

from bot.config import settings


@dataclass
class BroadcastStats:
    total: int = 0
    success: List[int] = field(default_factory=list)
    failed: List[dict] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0

    def save(self, path: str):
        data = {
            "total": self.total,
            "success_count": len(self.success),
            "failed_count": len(self.failed),
            "duration_seconds": round(self.finished_at - self.started_at, 2),
            "success_ids": self.success,
            "failed": self.failed,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


async def run_broadcast(
    token: str,
    user_ids: List[int],
    message_data: dict,
    progress_callback: Callable[[str], Awaitable[None]],
) -> BroadcastStats:
    """
    Выполняет рассылку через бота с указанным токеном.
    progress_callback - функция, вызываемая периодически для отчёта.
    """
    stats = BroadcastStats(total=len(user_ids), started_at=time.time())
    sleep_time = 1.0 / settings.messages_per_second

    # Подключаемся через socks-прокси, если задан
    bot = Bot(token=token, session=_make_session())

    try:
        for i, user_id in enumerate(user_ids, 1):
            try:
                await _send_to_user(bot, user_id, message_data)
                stats.success.append(user_id)
            except TelegramRetryAfter as e:
                # Flood limit - ждём и повторяем
                await asyncio.sleep(e.retry_after + 1)
                try:
                    await _send_to_user(bot, user_id, message_data)
                    stats.success.append(user_id)
                except Exception as ex:
                    stats.failed.append({"id": user_id, "error": str(ex)})
            except TelegramForbiddenError:
                stats.failed.append({"id": user_id, "error": "Bot blocked / user deactivated"})
            except TelegramBadRequest as e:
                stats.failed.append({"id": user_id, "error": f"BadRequest: {e.message}"})
            except Exception as e:
                stats.failed.append({"id": user_id, "error": str(e)})

            # Отправка прогресса раз в N сообщений или каждые 2 секунды
            if i % 50 == 0 or i == len(user_ids):
                pct = round(i / len(user_ids) * 100, 1)
                elapsed = time.time() - stats.started_at
                await progress_callback(
                    f"📊 Прогресс: {i}/{stats.total} ({pct}%)\n"
                    f"✅ Успешно: {len(stats.success)}\n"
                    f"❌ Ошибок: {len(stats.failed)}\n"
                    f"⏱ Прошло: {elapsed:.0f} сек"
                )

            await asyncio.sleep(sleep_time)

    finally:
        await bot.session.close()

    stats.finished_at = time.time()
    return stats


async def _send_to_user(bot: Bot, user_id: int, message_data: dict):
    """
    Отправляет сообщение пользователю через copy_message.
    copy_message работает для любого типа: текст, фото, видео, стикер, кружочек, медиагруппа.
    """
    msg_type = message_data.get("type")
    if msg_type != "copy":
        raise ValueError(f"Поддерживается только copy_message, получен тип: {msg_type}")

    await bot.copy_message(
        chat_id=user_id,
        from_chat_id=message_data["from_chat_id"],
        message_id=message_data["message_id"],
    )
