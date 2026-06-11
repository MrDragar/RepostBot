from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from bot.config import settings
from bot.states import BroadcastStates

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ Доступ запрещён.")
        return
    await state.clear()
    await message.answer(
        "👋 Привет!\n\n"
        "Я бот для рассылок. Для запуска рассылки отправь /broadcast\n\n"
        "Поддерживаемые форматы файлов с ID:\n"
        "• JSON: [123, 456] или {{\"users\": [123, 456]}}\n"
        "• CSV / Excel с колонкой 'id'\n"
        "• TXT (по ID в строке)"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ Доступ запрещён.")
        return
    
    await state.clear()
    await state.set_state(BroadcastStates.waiting_for_message)
    
    await message.answer(
        "📝 <b>Шаг 1/3: Подготовка поста</b>\n\n"
        "Чтобы бот-рассыльщик мог использовать <code>copy_message</code>, "
        "он должен иметь доступ к оригиналу сообщения.\n\n"
        "<b>Сделай так:</b>\n"
        "1️⃣ Отправь нужный пост <b>напрямую боту-рассыльщику</b> (или в канал/группу, где он состоит).\n"
        "2️⃣ <b>Перешли</b> этот пост мне (этому боту).\n\n"
        "Жду пересланное сообщение!"
    )
