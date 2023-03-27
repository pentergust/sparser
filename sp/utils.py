"""
Вспомогательные функции для работы.

Author: Muilinuri Nirvalen
Ver: 5.0
"""
import json

from pathlib import Path
from typing import Optional


def save_file(path: Path, data: dict) -> dict:
    """Записывает данные в файл.

    Args:
        path (Path): Путь к файлу для записи
        data (dict): Данные для записи

    Returns:
        dict: Данные для записи
    """
    if not path.exists():
        path.parents[0].mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))
    return data

def load_file(path: Path, data: Optional[dict]=None):
    """Читает данные из файла.

    Args:
        path (Path): Путь к файлу для чтения
        data (dict, optional): Данные для записи при отцуцтвии файла

    Returns:
        dict: Данные из файла/данные для записи
    """
    if path.is_file():
        with open(path) as f:
            return json.loads(f.read())

    elif data is not None:
        return save_file(path, data)

    else:
        return {}
