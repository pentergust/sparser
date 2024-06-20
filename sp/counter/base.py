"""Простой счётчик расписания.

Проедостовляют вспомогательные функции для подсчёта количества
элементов в текущем расписании.
Приведённый класс может быть использован для статистического анализа
расписнаия.
Для уточнения результатов подсчёта используется намерения.

"""

"""Счётчики элементов расписания.


Обрабите внимение, что счётчики возвращают "сырой" результат.
Который вы можеет в последствии самостоятельно обработать
в необходимый вам формат.

.. tip::

    Если вашей целью является использовать текстовый результат работы счётчиков,
    то обратите внимание на класс :py:class:`sp.text_counter.TextCounter`.

Содержит:

- Вспомогательные функции для результатов счётчиков.
- Счётчики:
    - классы.
    - Дни.
    - Индексы (уроки, кабинеты).
"""

from collections import Counter, defaultdict
from enum import Enum
from typing import Optional, Union

from .intents import Intent
from .parser import Schedule


class CounterTarget(Enum):
    """Описывает все доступные подгруппы счётчиков.

    Пример использования с TextCounter:

    .. code-block:: python

        # coutnter - экземпляр TextCounter с переданным Schedule
        message = counter.cl(
            sc.construct_intent()
            target=CounterTarget.CL
        )

    - `NONE`: То же самое что и None, без цели отображения.
    - `CL`: По классам в расписании.
    - `DAYS`: По дням недели.
    - `LESSONS`: По урокам (l_index).
    - `CABINETS`: По кабинетам (c_index).
    - `MAIN`: Противоположный выбранному счётчику индекса.
        Если это счётчик уроков - то по кабинетам.
        И напротив, если это счётчик кабентов, то по урокам.
    """

    NONE = "none"
    CL = "cl"
    DAYS = "days"
    LESSONS = "lessons"
    CABINETS = "cabinets"
    MAIN = "main"


# Вспомогательные функции
# =======================

def group_counter_res(counter_res: dict[str, dict[str, Union[int, Counter]]]
) -> dict[int, dict[str, dict]]:
    """Группирует результат работы счётчиков по total ключу.

    Формат вывода:

    .. code-block:: python

        {
            2: { # Общее количество ("total" счётчика)
                "8в" { # Некоторые счётчики, не обязательно класс.
                    # ...
                },
                "...", {
                    # ...
                }
            }
        }

    :param counter_res: Результаты работы счётчика расписания.
    :type counter_res: dict[str, dict[str, Union[int, Counter]]]
    :return: Сгруппированные результаты работы счётчика.
    :rtype: dict[int, dict[str, dict]]
    """
    groups = defaultdict(dict)
    for k, v in counter_res.items():
        key = v["total"]
        if not key:
            continue

        groups[key][k] = v

    return groups

def reverse_counter(cnt: Counter) -> dict[int, list[str]]:
    """Меняет ключ и занчение Counter местами.

    :param cnt: Счётчик элементов расписаия.
    :type cnt: Сounter
    :return: Перевернётый счётчик расписнаия.
    :rtype: dict[int, list[str]]
    """
    res = defaultdict(list)
    for k, v in cnt.items():
        if not v:
            continue

        res[v].append(k)
    return res

