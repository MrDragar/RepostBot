import json
import os
import pandas as pd
from typing import List


class FileParseError(Exception):
    pass


async def parse_user_ids(file_path: str) -> List[int]:
    """
    Парсит ID пользователей из JSON / CSV / Excel / TXT.
    Возвращает список int и список ошибок.
    """
    ext = os.path.splitext(file_path)[1].lower()
    ids: List[int] = []
    errors: List[str] = []

    try:
        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Поддерживаем форматы: [123, 456], [{"id": 123}, ...], {"users": [...]}
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("users") or data.get("ids") or data.get("data") or []
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

        # Преобразование и фильтрация
        for item in items:
            try:
                uid = int(str(item).strip())
                if uid > 0:
                    ids.append(uid)
                else:
                    errors.append(f"Отрицательный ID: {item}")
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
    """Ищет колонку с ID пользователей."""
    for col in df.columns:
        if col.lower() in ("id", "user_id", "userid", "tg_id", "telegram_id", "chat_id"):
            return df[col]
    # Берём первую колонку
    return df.iloc[:, 0]
