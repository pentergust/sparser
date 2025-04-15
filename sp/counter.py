"""Счётчики элементов расписания.

Предоставляет вспомогательный класс для подсчёта количества
элементов в расписании.
Используется для последующего анализа расписания.
Все функции используют намерения, для уточнения результатов подсчёта.

Обратите внимание, что счётчики возвращают "сырой" результат.
Который вы может в последствии самостоятельно обработать
в необходимый вам формат.
"""

from collections import Counter, defaultdict
from enum import Enum
from typing import TypeAlias, TypedDict, TypeVar

from .intents import Intent
from .parser import Schedule

# Вспомогательные типы данных
# ===========================


class ClCounterData(TypedDict):
    """Результаты подсчётов счётчика классов."""

    total: int
    days: Counter
    lessons: Counter
    cabinets: Counter


class DayCounterData(TypedDict):
    """Результат подсчёта счётчика дней."""

    total: int
    cl: Counter
    lessons: Counter
    cabinets: Counter


class IndexCounterData(TypedDict):
    """Результаты подсчёта счётчика индексов."""

    total: int
    cl: Counter
    days: Counter
    main: Counter


class CounterTarget(Enum):
    """Описывает все доступные подгруппы счётчиков.

    Пример использования с CurrentCounter:

    ```py
        counter = CurrentCounter(sc, Intent())
        message = platform.counter(
            counter.cl()
            target=CounterTarget.CL
        )
    ```

    - `NONE`: То же самое что и None, без цели отображения.
    - `CL`: По классам в расписании.
    - `DAYS`: По дням недели.
    - `LESSONS`: По урокам (l_index).
    - `CABINETS`: По кабинетам (c_index).
    - `MAIN`: Противоположный выбранному счётчику индекса.
        Если это счётчик уроков - то по кабинетам.
        И напротив, если это счётчик кабинетов, то по урокам.
    """

    NONE = "none"
    CL = "cl"
    DAYS = "days"
    LESSONS = "lessons"
    CABINETS = "cabinets"
    MAIN = "main"


# Вспомогательные функции
# =======================

_R = TypeVar("_R", ClCounterData, DayCounterData, IndexCounterData)
CounterRes: TypeAlias = dict[str, _R]


def _group_counter_res(counter_res: CounterRes) -> dict[int, CounterRes]:
    """Группирует результат работы счётчиков по total ключу.

    Формат вывода:

    ```py
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
    ```
    """
    groups: defaultdict[int, CounterRes] = defaultdict(dict)
    for k, v in counter_res.items():
        key = v["total"]
        if not key:
            continue

        groups[key][k] = v

    return groups


def reverse_counter(cnt: Counter) -> dict[int, list[str]]:
    """Меняет ключ и значение ``collections.Counter`` местами.

    Переворачивает счётчик из name:count -> count:[name, name, name].
    Используется в группировке результатов работы счётчиков по
    количеству.
    Также будет пропускать пустые значения при подсчёте.
    """
    res = defaultdict(list)
    for k, v in cnt.items():
        if not v:
            continue

        res[v].append(k)
    return res


# Класс счётчика
# ==============


class CurrentCounter:
    """Счётчик элементов текущего расписания.

    Предоставляет методы для подсчёта элементов текущего расписания.
    Возвращает сырые результаты, которое после можно обработать через
    класс представления.
    """

    def __init__(self, sc: Schedule, intent: Intent) -> None:
        self.sc = sc
        self.intent = intent

    def cl(
        self, intent: Intent | None = None
    ) -> dict[int, dict[str, ClCounterData]]:
        """Счётчик по классам с использованием sp.lessons.

        Считает элементы расписания, пробегаясь по sp.lessons.
        Использует намерение для уточнения результатов поиска.

        Пример результатов работы счетчика:

        ```py
        {
            "7а": { # Классы
                "total": 12, # Общее количество элементов.
                "days": Counter(), # Количество элементов по дням.
                "lessons": Counter(), # Количество элементов по урокам.
                "cabinets": Counter(), # Элементы по кабинетам.
            }
        }
        ```
        """
        res: dict[str, ClCounterData] = {}
        intent = intent or self.intent

        # Пробегаемся по урокам и дням в расписании
        for cl, days in self.sc.lessons.items():
            if intent.cl and cl not in intent.cl:
                continue

            day_counter: Counter[str] = Counter()
            lessons_counter: Counter[str] = Counter()
            cabinets_counter: Counter[str] = Counter()

            for day, lessons in enumerate(days):
                if intent.days and day not in intent.days:
                    continue

                for lesson in lessons:
                    lesson_cabinet = lesson.split(":")

                    lessons_counter[lesson_cabinet[0]] += 1
                    for cabinet in lesson_cabinet[1].split("/"):
                        cabinets_counter[cabinet] += 1

                day_counter[str(day)] = len(lessons)

            res[cl] = {
                "total": sum(day_counter.values()),
                "days": day_counter,
                "lessons": lessons_counter,
                "cabinets": cabinets_counter,
            }
        return _group_counter_res(res)

    def days(
        self, intent: Intent | None = None
    ) -> dict[int, dict[str, DayCounterData]]:
        """Счётчик по дням с использованием sc.lessons.

        Производит подсчёт элементов относительно дней недели.
        Использует намерение для уточнения результатов работы счётчиков.

        Пример результатов работы счётчика:


        ```py
        {
            "1": { # День недели (0 - понедельник, 5 - суббота).
                "total": 12 # Общее количество элементов расписания.
                "cl": Counter() # Количество элементов по классам.
                "lessons": Counter() # Элементов по урокам.
                "cabinets": Counter() # Элементов по кабинетам.
            }
        }
        ```
        """
        res: dict[str, DayCounterData] = {
            str(x): {
                "cl": Counter(),
                "total": 0,
                "lessons": Counter(),
                "cabinets": Counter(),
            }
            for x in range(6)
        }
        intent = intent or self.intent

        for cl, days in self.sc.lessons.items():
            if intent.cl and cl not in intent.cl:
                continue

            for day, lessons in enumerate(days):
                if intent.days and day not in intent.days:
                    continue

                for lesson in lessons:
                    lesson_cabinet: list[str] = lesson.split(":")  # noqa
                    res[str(day)]["cl"][cl] += 1
                    res[str(day)]["lessons"][lesson_cabinet[0]] += 1
                    res[str(day)]["total"] += 1

                    for x in lesson_cabinet[1].split("/"):
                        res[str(day)]["cabinets"][x] += 1

        return _group_counter_res(res)

    def index(
        self, intent: Intent | None = None, cabinets_mode: bool = False
    ) -> dict[int, dict[str, IndexCounterData]]:
        """Счётчик уроков/кабинетов с использованием индексов.

        Производит подсчёт элементов расписания в счётчиках.
        В зависимости от режима считает уроки или кабинеты.
        Использует намерение, для уточнения результатов счётчика.

        .. caution:: Этот счётчик сильно отличается

            Обратите внимание, что поскольку этот счётчик использует
            в подсчёте индексы, то и шаблон результатов работы этого
            счётчика отличается.

        .. table::

                +----------+---------+---------+
                | cabinets | obj     | another |
                +==========+=========+=========+
                | false    | lesson  | cabinet |
                +----------+---------+---------+
                | true     | cabinet | lesson  |
                +----------+---------+---------+

        ```py
        {
            "obj": { # урок или кабинет в зависимости от режима.
                "total": 12 # Общее количество элементов расписания.
                "cl": Counter() # Количество элементов по классам.
                "days": Counter() # Элементов по дням.
                "main": Counter() # Элементов по `another`.
            }
        }
        ```
        """
        res: dict[str, IndexCounterData] = defaultdict(
            lambda: {
                "total": 0,
                "days": Counter(),
                "cl": Counter(),
                "main": Counter(),
            }
        )
        if intent is None:
            intent = self.intent

        if cabinets_mode:
            index = self.sc.c_index
            obj_filter = intent.cabinets
            another_filter = intent.lessons
        else:
            index = self.sc.l_index
            obj_filter = intent.lessons
            another_filter = intent.cabinets

        for k, v in index.items():
            if obj_filter and k not in obj_filter:
                continue

            for day, another_v in enumerate(v):
                if intent.days and day not in intent.days:
                    continue

                for another, cl_s in another_v.items():
                    if another_filter and another not in another_filter:
                        continue

                    for cl, i in cl_s.items():
                        if intent.cl and cl not in intent.cl:
                            continue

                        res[k]["total"] += i
                        res[k]["cl"][cl] += i
                        res[k]["days"][str(day)] += i
                        res[k]["main"][another] += i
        return _group_counter_res(res)
