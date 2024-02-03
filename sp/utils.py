"""Вспомогательные функции для работы проекта.

Используется как набор общих вспомогательных функций
которые работают внутри проект, но редко выходят за его пределы.

Содержит:

- Функции для работы с json файлами.
- Проверка ключей словаря по шаблону.
- Склонение слов относительно числа.
- Получение строкового таймера обратного отсчёта.
- Упаковка нескольких записей об обновлениях в одну.

Author: Milinuri Nirvalen
"""

from pathlib import Path
from typing import Any, Optional, Union

# Как более быстрый, чем стандартный json
import ujson
from loguru import logger

# Работа с json файлами
# =====================

def save_file(path: Path, data: Union[dict, list]):
    """Записывает данные в json файл.

    Используется как обёртка для более удобной упаковки данных
    в json файлы.
    Автоматически создаёт файл, есть его не существует.

    :param path: Путь к файлу для записи данных.
    :type path: Path
    :param data: Данные для записи в файл.
    :type data: Union[dict, list]
    :return: Ваши данные для записи.
    :rtype: dict
    """
    if not path.exists():
        path.parents[0].mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        f.write(ujson.dumps(data, indent=4, ensure_ascii=False))
    return data

def load_file(path: Path, data: Optional[dict]=None) -> Union[dict, list]:
    """Читает данные из json файла.

    Используется как обёртка для более удобного чтения данных из
    json файла.
    Если переданы данные и файла не существует -> создаёт новый файл
    и записывает переданные данные.
    Если файла не суещствует и данные переданы или возникло исключение
    при чтении файла -> возвращаем пустой словарь.

    :param path: Путь к файлу для чтения.
    :type path: Path
    :param data: Данные для записи, по умолчанию не указаны.
    :type data: Optional[dict], optional
    :return: Распакованные данные из файла.
    :rtype: Union[dict, list]
    """
    try:
        with open(path) as f:
            return ujson.loads(f.read())
    except FileNotFoundError:
        if data is not None:
            logger.warning("File not found {} -> create", path)
            save_file(path, data)
            return data
        else:
            logger.error("File not found {}", path)
            return {}
    except Exception as e:
        logger.exception(e)
        return {}


# Работа с контейнерами
# =====================

def check_keys(data: dict, model: dict) -> dict:
    """Устарел, будет заменено на UserData..."""
    res = data.copy()

    for k, v in model.items():
        if k not in res or res[k] is None:
            res[k] = v

    return res



# Прочие утилиты
# ==============

def plural_form(n: int, v: tuple[str]) -> str:
    """Возаращает просклонённое значение в зивисимости от числа.

    Возвращает просклонённое слово "для одного", "для двух",
    "для пяти" значений.

    .. code-block:: python

        plural_form(difference.days, ("день", "дня", "дней"))
        # difference.days = 1 -> день
        # difference.days = 32 -> дня
        # difference.days = 65 -> дней

    :param n: Некоторое число, используемое в склонении.
    :type n: int
    :param v: Варианты слова (для 1, для 2, для 5).
    :type v: tuple[str]
    :return: Просклонённое слово в зависимости от числа.
    :rtype: str
    """
    return v[2 if (4 < n % 100 < 20) else (2, 0, 1, 1, 1, 2)[min(n % 10, 5)]] #noqa

def get_str_timedelta(s: int, hours: Optional[bool]=True) -> str:
    """Возвращает строковый обратный отсчёт из количества секунд.

    Если hours = False -> ММ:SS.
    Если hours = True -> HH:MM:SS.

    :param s: Количество секунд для обратного отсчёта.
    :type s: int
    :param hours: Использовать ли часы, по умолчанию да.
    :type hours: Optional[bool], optional
    :return: Строковый обратный отсчёт.
    :rtype: str
    """
    if hours:
        h, r = divmod(s, 3600)
        m, s = divmod(r, 60)
        return f"{h:02}:{m:02}:{s:02}"
    else:
        m, s = divmod(s, 60)
        return f"{m:02}:{s:02}"


def compact_updates(updates: list[dict[str, Any]]) -> dict[str, Any]:
    """Упаковывает несколько записей об обновлениях в одну.

    Используется чтобы совместить несколько записей об изменениях.
    Например чтобы покзаать все изменения в расписании за неделю.
    Или использваоть при получении обнолвений.

    **Правила совмешения**:

    - Если урока ранее не было -> добавляем урок.
    - Если Урок A, сменился на B, а после снова на A -> удаляем урок.
    - Если A -> B, B -> C, то A => C.
    - Иначе добавить запись.

    :param updates: Список записей об обновлениях расписания.
    :type updates: list[dict[str, Any]]
    :return: Новая упакованная запись об обновлённом расписании.
    :rtype: dict[str, Any]
    """
    res = updates[0]["updates"].copy()

    # Просматриваем все последующии записи об обновленях
    for update_data in updates[1:]:
        for day, day_update in enumerate(update_data["updates"]):
            for cl, cl_updates in day_update.items():
                if cl not in res[day]:
                    res[day][cl] = cl_updates
                    continue

                new_lessons: list[Union[tuple, None]] = []
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
