from aiogram.fsm.state import StatesGroup, State


class BroadcastStates(StatesGroup):
    waiting_for_message = State()       # ждём текст/пост
    waiting_for_file = State()          # ждём файл со списком ID
    waiting_for_token = State()         # ждём токен бота, от имени которого идёт рассылка
    waiting_for_confirmation = State()  # финальное подтверждение
