"""Вспомогательные функции для работы проекта.

Используется как набор общих вспомогательных функций,
которые работают внутри проекта, но редко выходят за его пределы.

.. note:: Непостоянство

    Обратите внимание что перечень функций не постоянный.
    Они могут быть со временем перемещены или удалены вовсе.
    Не стоит слишком сильно полагаться на них вне проекта sp.

Содержит:

- Функции для работы с json файлами.
- Склонение слов относительно числа.
- Получение строкового таймера обратного отсчёта.
- Упаковка нескольких записей об обновлениях в одну.
"""

from pathlib import Path
from typing import TypeVar

# В теории более быстрый, чем стандартный json
import ujson
from loguru import logger

from sp.parser import UpdateData

# Работа с json файлами
# =====================

LoadData = dict | list
_T = TypeVar("_T", bound=LoadData)

def save_file(path: Path, data: _T) -> _T:
    """Записывает данные в json файл.

    Используется как обёртка для более удобной упаковки данных
    в json файлы.
    Автоматически создаёт файл, если он не найден.

    .. deprecated:: 6.1
        В скором времени проект откажется от использования json.
        Данные методы будут перемещены.

    :param path: Путь к файлу для записи данных.
    :type path: Path
    :param data: Данные для записи в файл.
    :type data: Union[dict, list]
    :return: Ваши данные для записи.
    :rtype: dict
    """
    logger.info("Write file {} ...", path)
    if not path.exists():
        path.parents[0].mkdir(parents=True, exist_ok=True)
        logger.info("Created not exists dirs")

    with open(path, 'w') as f:
        f.write(ujson.dumps(data, indent=4, ensure_ascii=False))
    return data

def load_file(path: Path, data: _T | None=None) -> _T:
    """Читает данные из json файла.

    Используется как обёртка для более удобного чтения данных из
    json файла.
    Если переданы данные и файла не существует -> создаёт новый файл
    и записывает переданные данные.
    Если файла не существует и данные переданы или возникло исключение
    при чтении файла -> возвращаем пустой словарь.

    .. deprecated:: 6.1
        В скором времени проект откажется от использования json.
        Данные методы будут перемещены.

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
            return []
    except Exception as e:
        logger.exception(e)
        return []


# Прочие утилиты
# ==============

def plural_form(n: int, v: tuple[str, str, str]) -> str:
    """Возвращает склонённое значение в зависимости от числа.

    Возвращает склонённое слово: "для одного", "для двух",
    "для пяти" значений.

    .. code-block:: python

        plural_form(days, ("день", "дня", "дней"))
        # days = 1 -> день
        # days = 32 -> дня
        # days = 65 -> дней

    :param n: Некоторое число, используемое в склонении.
    :type n: int
    :param v: Варианты слова (для 1, для 2, для 5).
    :type v: tuple[str]
    :return: Склонённое слово в зависимости от числа.
    :rtype: str
    """
    return v[2 if (4 < n % 100 < 20) else (2, 0, 1, 1, 1, 2)[min(n % 10, 5)]] #noqa

def get_str_timedelta(s: int, hours: bool | None=True) -> str:
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


# TODO: В надеждах когда-нибудь переписать эту страшную функцию
# А пока работает и не трогаем, хе-хе ...
def compact_updates(updates: list[UpdateData]) -> UpdateData:  # noqa: PLR0912
    """Упаковывает несколько записей об обновлениях в одну.

    Используется чтобы совместить несколько записей об изменениях.
    Например чтобы показать все изменения в расписании за неделю.
    Или использовать при получении обновлений расписания для
    пользователя.

    **Правила совмещения**:

    - Если урока ранее не было -> добавляем урок.
    - Если Урок A, сменился на B, а после снова на A -> удаляем урок.
    - Если A -> B, B -> C, то A => C.
    - Иначе добавить запись.

    :param updates: Список записей об обновлениях расписания.
    :type updates: list[dict[str, Union[int, list[dict]]]]
    :return: Новая упакованная запись об обновлённом расписании.
    :rtype: dict[str, Union[int, list[dict]]]
    """
    res: list[dict[str, list[dict]]] = updates[0]["updates"].copy()

    # Просматриваем все последующии записи об обновлениях
    for update_data in updates[1:]:
        for day, day_update in enumerate(update_data["updates"]):
            for cl, cl_updates in day_update.items():
                if cl not in res[day]:
                    res[day][cl] = cl_updates
                    continue

                old_lessons = res[day][cl]
                new_lessons: list[tuple | None] = []

                for i, lesson in enumerate(cl_updates):
                    old_lesson = old_lessons[i]

                    # Если нет старого и нового урока.
                    if old_lesson is None and lesson is None:
                        new_lessons.append(None)

                    # Если появился новый урок
                    elif old_lesson is None and lesson is not None:
                        new_lessons.append(lesson)

                    # Совмещение записей об изменении уроков
                    elif lesson is None and old_lesson is not None:
                        new_lessons.append(old_lesson)

                    # B -> A, C -> A = None
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
