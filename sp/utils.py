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
    """
    logger.info("Write file {} ...", path)
    if not path.exists():
        path.parents[0].mkdir(parents=True, exist_ok=True)
        logger.info("Created not exists dirs")

    with open(path, "w") as f:
        f.write(ujson.dumps(data, indent=4, ensure_ascii=False))
    return data


def load_file(path: Path, data: _T | None = None) -> _T:
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
            return data
    except Exception as e:
        logger.exception(e)
        return data


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
    """
    return v[2 if (4 < n % 100 < 20) else (2, 0, 1, 1, 1, 2)[min(n % 10, 5)]]  # noqa


def get_str_timedelta(s: int, hours: bool | None = True) -> str:
    """Возвращает строковый обратный отсчёт из количества секунд.

    Если hours = False -> ММ:SS.
    Если hours = True -> HH:MM:SS.
    """
    if hours:
        h, r = divmod(s, 3600)
        m, s = divmod(r, 60)
        return f"{h:02}:{m:02}:{s:02}"
    else:
        m, s = divmod(s, 60)
        return f"{m:02}:{s:02}"
