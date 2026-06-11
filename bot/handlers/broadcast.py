import json
import os
import uuid

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, FSInputFile
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types.input_file import BufferedInputFile

from bot.config import settings
from bot.states import BroadcastStates
from bot.services.file_parser import parse_user_ids, FileParseError
from bot.services.broadcaster import run_broadcast

router = Router(name="broadcast")


# ---------- ШАГ 1: приём сообщения для рассылки ----------

@router.message(StateFilter(BroadcastStates.waiting_for_message))
async def receive_message(message: Message, state: FSMContext, bot: Bot):
    """Сохраняем метаданные полученного поста и переходим к файлу."""
    message_data = await _extract_message_data(message, bot)
    await state.update_data(message_data=message_data)

    # Сохраняем сообщение "для истории" — пересылаем обратно, чтобы показать, что принято
    await message.answer("✅ Пост принят. Теперь отправь файл с ID пользователей.")
    await message.copy(chat_id=message.chat.id, from_chat_id=message.chat.id, message_id=message.id)  # для наглядности (опционально)

    await state.set_state(BroadcastStates.waiting_for_file)


# ---------- ШАГ 2: приём файла с ID ----------

@router.message(StateFilter(BroadcastStates.waiting_for_file), F.document)
async def receive_file(message: Message, state: FSMContext, bot: Bot):
    document = message.document
    ext = os.path.splitext(document.file_name)[1].lower()
    if ext not in (".json", ".csv", ".xlsx", ".xls", ".txt"):
        await message.answer("⚠️ Не поддерживаемый формат. Пришли JSON/CSV/XLSX/TXT.")
        return

    os.makedirs(settings.temp_dir, exist_ok=True)
    temp_path = os.path.join(settings.temp_dir, f"{uuid.uuid4()}{ext}")

    # Правильный способ скачивания в aiogram 3.x
    await bot.download(document, destination=temp_path)

    try:
        ids, errors = await parse_user_ids(temp_path)
    except FileParseError as e:
        await message.answer(f"❌ Ошибка парсинга файла:\n<code>{e}</code>")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return

    if not ids:
        await message.answer("❌ В файле не найдено ни одного валидного ID.")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return

    await state.update_data(file_path=temp_path, user_ids=ids)

    msg = f"✅ Файл обработан.\n👥 Уникальных ID: <b>{len(ids)}</b>"
    if errors:
        msg += f"\n⚠️ Некорректных строк: {len(errors)}"
    msg += "\n\nТеперь пришли <b>token</b> бота, от имени которого будет рассылка."

    await state.set_state(BroadcastStates.waiting_for_token)
    await message.answer(msg)


# ---------- ШАГ 3: приём токена ----------

@router.message(StateFilter(BroadcastStates.waiting_for_token))
async def receive_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if not token or ":" not in token or len(token) < 20:
        await message.answer("⚠️ Это не похоже на токен бота. Формат: <code>123456:ABC-DEF...</code>")
        return

    await state.update_data(broadcast_token=token)
    data = await state.get_data()
    message_data = data["message_data"]
    user_ids = data["user_ids"]

    # Показываем сводку и кнопку подтверждения
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_broadcast"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast"),
    )

    await state.set_state(BroadcastStates.waiting_for_confirmation)
    await message.answer(
        f"📋 <b>Проверь перед запуском:</b>\n\n"
        f"📤 Сообщение: <i>{message_data['type']}</i>\n"
        f"👥 Получателей: <b>{len(user_ids)}</b>\n"
        f"🤖 Бот: <code>{token[:10]}...</code>\n\n"
        f"Запустить рассылку?",
        reply_markup=kb.as_markup(),
    )


# ---------- ШАГ 4: подтверждение и рассылка ----------

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена.")
    await callback.answer()


@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer("🚀 Запуск рассылки...")
    await callback.message.edit_text("🚀 Рассылка запущена. Я буду информировать о прогрессе.")

    data = await state.get_data()
    token = data["broadcast_token"]
    user_ids = data["user_ids"]
    message_data = data["message_data"]

    # Функция отправки прогресса
    progress_status = await bot.send_message(
        callback.from_user.id, "⏳ Начало..."
    )

    async def progress_cb(text: str):
        try:
            await bot.edit_message_text(text, chat_id=progress_status.chat.id, message_id=progress_status.message_id)
        except Exception:
            pass  # если edit упал — не критично

    # Запускаем рассылку
    stats = await run_broadcast(token, user_ids, message_data, progress_cb)

    # Сохраняем статистику
    os.makedirs(settings.temp_dir, exist_ok=True)
    report_path = os.path.join(settings.temp_dir, f"report_{uuid.uuid4().hex[:8]}.json")
    stats.save(report_path)

    # Финальное сообщение
    duration = stats.finished_at - stats.started_at
    duration_min = int(duration // 60)
    duration_sec = int(duration % 60)

    final_msg = (
        f"🏁 <b>Рассылка завершена!</b>\n\n"
        f"👥 Всего: {stats.total}\n"
        f"✅ Доставлено: {len(stats.success)}\n"
        f"❌ Ошибок: {len(stats.failed)}\n"
        f"⏱ Время: {duration_min}м {duration_sec}с\n\n"
        f"Детальный отчёт — в файле ниже."
    )

    await bot.send_message(callback.from_user.id, final_msg)

    # Отправляем JSON с результатом
    with open(report_path, "rb") as f:
        report_bytes = f.read()
    await bot.send_document(
        callback.from_user.id,
        BufferedInputFile(report_bytes, filename="broadcast_report.json"),
        caption="Полный отчёт: success_ids + failed (с причинами)",
    )

    # Чистим временные файлы
    try:
        os.remove(data["file_path"])
        os.remove(report_path)
    except Exception:
        pass

    await state.clear()


# ---------- Вспомогательные функции ----------

async def _extract_message_data(message: Message, bot: Bot) -> dict:
    """
    Возвращает данные ТОЛЬКО для copy_message.
    Это самый надёжный способ: сохраняет всё форматирование, медиагруппы, кнопки.
    """
    # Если сообщение переслано из канала/чата — копируем оттуда (бот должен быть там участником)
    if message.forward_from_chat and message.forward_from_message_id:
        return {
            "type": "copy",
            "from_chat_id": message.forward_from_chat.id,
            "message_id": message.forward_from_message_id,
        }

    # Если переслано из личного чата с другим пользователем
    if message.forward_from and message.forward_from_message_id:
        return {
            "type": "copy",
            "from_chat_id": message.forward_from.id,
            "message_id": message.forward_from_message_id,
        }

    # Обычное сообщение — берём из текущего чата с ботом.
    # copy_message умеет копировать из чата A в чат B, даже если это приватный чат.
    return {
        "type": "copy",
        "from_chat_id": message.chat.id,
        "message_id": message.message_id,
    }
