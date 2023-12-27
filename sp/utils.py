"""
Вспомогательные функции для работы парсера.

Author: Muilinuri Nirvalen
"""

from pathlib import Path
from typing import Optional
# from typing import Iterable
from typing import Union
from typing import Any
from types import NoneType

import ujson
from loguru import logger


# Работа с json файлами
# =====================

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
        f.write(ujson.dumps(data, indent=4, ensure_ascii=False))
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
            return ujson.loads(f.read())

    elif data is not None:
        return save_file(path, data)

    else:
        return {}


def check_keys(data: dict, model: dict) -> dict:
    """Проверяет ключи словоря с шаблоном.
    Дополняет отцуцтвуюшие ключи.

    Args:
        data (dict): Исходный словарь
        model (dict): Шаблон для проверки

    Returns:
        dict: Проверенный словарь
    """
    res = data.copy()

    for k, v in model.items():
        if k not in res or res[k] is None:
            res[k] = v

    return res

def ensure_list(a):
    return (a,) if isinstance(a, (str, int, NoneType)) else a


def plural_form(n: int, v: list[str]) -> str:
    """Возвращает просклонённое слово в зависимости от числа.

    plural_form(difference.days, ("день", "дня", "дней"))

    Args:
        n (int): Число
        v (list[str]): Варианты слова (для 1, для 2, для 5)

    Returns:
        str: ПРосклонённое слово в зависимости от числа
    """
    return v[2 if (4 < n % 100 < 20) else (2, 0, 1, 1, 1, 2)[min(n % 10, 5)]]


def get_str_timedelta(s: int | float, hours: Optional[bool]=True) -> str:
    """Возаращает строковый обратный отсчёт из количества секунд.

    Если hours = False -> ММ:SS.
    Если hours = True -> HH:MM:SS.

    Args:
        s (int | float): Количество секунд прошедшего времени.
        hours (bool, optional): Учитывать ли часы.

    Returns:
        str: Строковый обраный отсчёт.
    """
    if hours:
        hours, remainder = divmod(int(s), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    else:
        minutes, seconds = divmod(int(s), 60)
        return f"{minutes:02}:{seconds:02}"


def compact_updates(updates: list[dict]) -> dict:
    """Собиарет несколько записей об обновлениях в одну.

    Используется чтобы совместить несколько записей об изменениях.
    Например чтобы покзаать все имзеенния в расписании за неделю.
    Или использваоть при получении обнолвений.

    Правила совмещения:

    1. Если урока ранее не было -> добавляем урок.
    2. Если Урок A, сменился на B, а после снова на A -> удаляем урок.
    3. Если A -> B, B -> C, то A => C.
    4. Иначе добавить запись.

    Args:
        updates (list[Dict]): Спиоск записей обновлений расписания.

    Returns:
        dict: Новая совмешённая запись об обновлении расписания.
    """
    res = updates[0]["updates"].copy()

    # Просматриваем все последующии записи об обновленях
    for update_data in updates[1:]:
        for day, day_update in enumerate(update_data["updates"]):
            for cl, cl_updates in day_update.items():
                if cl not in res[day]:
                    res[day][cl] = cl_updates
                    continue

                new_lessons = []
                old_lessons = res[day][cl]

                for i, lesson in enumerate(cl_updates):
                    old_lesson = old_lessons[i]

                    # Если нет старого и нового урока.
                    if old_lesson is None and lesson is None:
                        new_lessons.append(None)

                    # Если появился новый урок
                    elif old_lesson is None and lesson is not None:
                        new_lessons.append(lesson)

                    # Совмещенеи записей об изменении уроков
                    elif lesson is None and old_lesson is not None:
                        new_lessons.append(old_lesson)

                    # B -> A, C -> a = None
                    elif old_lesson[1] == lesson[1]:
                        new_lessons.append(None)

                    # A -> B -> A = None
                    elif old_lesson[0] == lesson[1]:
                        new_lessons.append(None)

                    # A -> B; B -> C = A -> C
                    elif old_lesson[1] == lesson[0]:
                        new_lessons.append((old_lesson[0], lesson[1]))

                    else:
                        new_lessons.append(lesson)

                if new_lessons == [None] * 8:
                    del res[day][cl]
                else:
                    res[day][cl] = new_lessons

    return {
        "start_time": updates[0]["start_time"],
        "end_time": updates[-1]["end_time"],
        "updates": res
    }
