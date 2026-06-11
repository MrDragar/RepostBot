import json
import os
import pandas as pd
from typing import List, Tuple, Any


class FileParseError(Exception):
    pass


# Ключи, по которым ищем ID в словарях (JSON)
ID_KEYS = {
    "userid", "user_id", "user", "users", "id",
    "tg_id", "tgid", "telegram_id", "telegramid", "telegram",
    "chat_id", "chatid", "chat",
    "account", "member", "subscriber", "recipient",
}


async def parse_user_ids(file_path: str) -> Tuple[List[int], List[str]]:
    ext = os.path.splitext(file_path)[1].lower()
    ids: List[int] = []
    errors: List[str] = []

    try:
        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = _extract_items_from_json(data)

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


def _extract_items_from_json(data: Any) -> List[Any]:
    """
    Извлекает список ID-значений из любого JSON.
    Поддерживает:
      - [1, 2, 3]                               → список чисел
      - [{"userId":1}, {"userId":2}]            → список объектов
      - {"users": [1,2,3]}                      → объект со списком
      - {"data": [{"user_id":1}, ...]}          → объект со списком объектов
    """
    # Случай 1: корень — список
    if isinstance(data, list):
        # Если элементы — словари, достаём ID из них
        if data and isinstance(data[0], dict):
            return [_extract_id_from_dict(obj) for obj in data]
        # Иначе — просто список значений
        return data

    # Случай 2: корень — объект
    if isinstance(data, dict):
        # Ищем известные ключи, в которых лежит список
        for key in ("users", "ids", "data", "userIds", "members", "subscribers", "results", "items"):
            if key in data and isinstance(data[key], list):
                inner = data[key]
                if inner and isinstance(inner[0], dict):
                    return [_extract_id_from_dict(obj) for obj in inner]
                return inner
        # Если ничего не нашли — пробуем достать ID прямо из корневого объекта
        return [_extract_id_from_dict(data)]

    raise FileParseError("Ожидался массив или объект")


def _extract_id_from_dict(obj: dict) -> Any:
    """
    Ищет поле с ID внутри словаря.
    Подходит для: {"userId": 123}, {"user_id": 123}, {"id": 123} и т.п.
    """
    if not isinstance(obj, dict):
        return obj
    # Ищем по нормализованному имени ключа
    for key, value in obj.items():
        if str(key).strip().lower() in ID_KEYS:
            return value
    raise FileParseError(f"В объекте не найдено поле с ID: {list(obj.keys())}")


def _find_id_column(df: pd.DataFrame) -> pd.Series:
    """
    Ищет колонку с ID в DataFrame.
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
    return df.iloc[:, 0]
