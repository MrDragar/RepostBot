import json
import os
import pandas as pd
from typing import List, Tuple


class FileParseError(Exception):
    pass


async def parse_user_ids(file_path: str) -> Tuple[List[int], List[str]]:
    """
    Парсит ID пользователей из JSON / CSV / Excel / TXT.
    Возвращает список уникальных int и список ошибок парсинга.
    """
    ext = os.path.splitext(file_path)[1].lower()
    ids: List[int] = []
    errors: List[str] = []

    try:
        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Поддерживаем: [123, 456], {"users": [...]}, {"ids": [...]}
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = (
                    data.get("users")
                    or data.get("ids")
                    or data.get("data")
                    or data.get("userIds")
                    or []
                )
            else:
                raise FileParseError("Неизвестная структура JSON")

        elif ext == ".csv":
            df = pd.read_csv(file_path)
            items = _find_id_column(df).tolist()

        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
            items = _find_id_column(df).tolist()

        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                items = [line.strip() for line in f if line.strip()]

        else:
            raise FileParseError(f"Неподдерживаемый формат файла: {ext}")

        for item in items:
            try:
                uid = int(str(item).strip())
                if uid > 0:
                    ids.append(uid)
                else:
                    errors.append(f"Отрицательный/нулевой ID: {item}")
            except (ValueError, TypeError):
                errors.append(f"Некорректный ID: {item}")

        # Убираем дубликаты, сохраняя порядок
        seen = set()
        unique_ids = []
        for uid in ids:
            if uid not in seen:
                seen.add(uid)
                unique_ids.append(uid)

        return unique_ids, errors

    except Exception as e:
        raise FileParseError(f"Ошибка парсинга: {e}")


def _find_id_column(df: pd.DataFrame) -> pd.Series:
    """
    Ищет колонку с ID пользователей.
    Поддерживаются варианты (регистр не важен):
    id, userId, user_id, userid, tg_id, telegram_id, chat_id, user, tg, account и др.
    """
    aliases = {
        "id", "user_id", "userid", "user", "users",
        "tg_id", "tgid", "telegram_id", "telegramid", "telegram",
        "chat_id", "chatid", "chat",
        "account", "member", "subscriber", "recipient",
    }
    for col in df.columns:
        if str(col).strip().lower() in aliases:
            return df[col]
    # Если ничего не нашли — берём первую колонку
    return df.iloc[:, 0]
