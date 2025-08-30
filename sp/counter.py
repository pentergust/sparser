"""Счётчики элементов расписания.

Предоставляет счётчик для анализа количества элементов в расписании.
Все методы используют намерения, для уточнения результатов подсчёта.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from sp.intents import Intent
from sp.schedule import Schedule


@dataclass(slots=True)
class CounterGroup:
    """Группа результатов работы счётчика.

    в зависимости от типа счётчика некоторые поля могут быть пусты.
    К примеру у счётчика по классам классы будут пустыми.
    """

    total: int
    cl: Counter[str]
    days: Counter[int]
    lessons: Counter[str]
    cabinets: Counter[str]


class CounterTarget(Enum):
    """Описывает все доступные подгруппы счётчиков.

    Пример использования с ``CurrentCounter``:

    ```py
        counter = CurrentCounter(sc, Intent())
        message = view.counter(
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


_K = TypeVar("_K", int, str)
CounterRes = dict[_K, CounterGroup]


def _group_counter_res(
    counter_res: CounterRes[_K],
) -> dict[int, CounterRes[_K]]:
    """Группирует результат работы счётчиков по total ключу."""
    groups: defaultdict[int, CounterRes[Any]] = defaultdict(dict)
    for k, v in counter_res.items():
        if not v.total:
            continue

        groups[v.total][k] = v

    return groups


def reverse_counter(cnt: Counter[str]) -> dict[int, list[str]]:
    """Меняет ключ и значение ``collections.Counter`` местами.

    Переворачивает счётчик из name:count -> count:[name, name, name].
    Используется в группировке результатов работы счётчиков по
    количеству.
    Также будет пропускать пустые значения при подсчёте.
    """
    res: defaultdict[int, list[str]] = defaultdict(list)
    for k, v in cnt.items():
        if not v:
            continue

        res[v].append(k)
    return res


class CurrentCounter:
    """Счётчик элементов текущего расписания.

    Предоставляет методы для подсчёта элементов расписания.
    Вы можете отобразить результат через класс представления.
    """

    def __init__(self, sc: Schedule, intent: Intent) -> None:
        self.sc = sc
        self.intent = intent

    def cl(self, intent: Intent | None = None) -> dict[int, CounterRes[str]]:
        """Счётчик по классам с использованием sp.lessons.

        Считает элементы расписания, пробегаясь по sp.lessons.
        Использует намерение для уточнения результатов поиска.
        """
        res: dict[str, CounterGroup] = {}
        intent = intent or self.intent
        for cl, days in self.sc.schedule["lessons"].items():
            if intent.cl and cl not in intent.cl:
                continue

            day_counter: Counter[int] = Counter()
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

                day_counter[day] = len(lessons)

            res[cl] = CounterGroup(
                total=sum(day_counter.values()),
                cl=Counter(),
                days=day_counter,
                lessons=lessons_counter,
                cabinets=cabinets_counter,
            )
        return _group_counter_res(res)

    def days(self, intent: Intent | None = None) -> dict[int, CounterRes[int]]:
        """Счётчик по дням с использованием sc.lessons.

        Производит подсчёт элементов относительно дней недели.
        Использует намерение для уточнения результатов работы счётчиков.
        """
        res = {
            x: CounterGroup(0, Counter(), Counter(), Counter(), Counter())
            for x in range(6)
        }
        intent = intent or self.intent

        for cl, days in self.sc.schedule["lessons"].items():
            if intent.cl and cl not in intent.cl:
                continue

            for day, lessons in enumerate(days):
                if intent.days and day not in intent.days:
                    continue

                for lesson in lessons:
                    lesson_cabinet: list[str] = lesson.split(":")
                    res[day].cl[cl] += 1
                    res[day].lessons[lesson_cabinet[0]] += 1
                    res[day].total += 1
                    for x in lesson_cabinet[1].split("/"):
                        res[day].cabinets[x] += 1

        return _group_counter_res(res)

    def lessons(
        self, intent: Intent | None = None
    ) -> dict[int, CounterRes[str]]:
        """Счётчик уроков с использованием индексов.

        Производит подсчёт элементов расписания в счётчиках.
        В зависимости от режима считает уроки или кабинеты.
        Использует намерение, для уточнения результатов счётчика.
        """
        res: dict[str, CounterGroup] = defaultdict(
            lambda: CounterGroup(0, Counter(), Counter(), Counter(), Counter())
        )
        intent = intent or self.intent
        for k, v in self.sc.l_index.items():
            if intent.lessons and k not in intent.lessons:
                continue

            for day, cabinets in enumerate(v):
                if intent.days and day not in intent.days:
                    continue

                for cabinet, cl_s in cabinets.items():
                    if intent.cabinets and cabinet not in intent.cabinets:
                        continue

                    for cl, i in cl_s.items():
                        if intent.cl and cl not in intent.cl:
                            continue

                        res[k].total += len(i)
                        res[k].cl[cl] += len(i)
                        res[k].days[day] += len(i)
                        res[k].lessons[cabinet] += len(i)

        return _group_counter_res(res)

    def cabinets(
        self, intent: Intent | None = None
    ) -> dict[int, CounterRes[str]]:
        """Счётчик уроков с использованием индексов.

        Производит подсчёт элементов расписания в счётчиках.
        В зависимости от режима считает уроки или кабинеты.
        Использует намерение, для уточнения результатов счётчика.
        """
        res: dict[str, CounterGroup] = defaultdict(
            lambda: CounterGroup(0, Counter(), Counter(), Counter(), Counter())
        )
        intent = intent or self.intent
        for k, v in self.sc.c_index.items():
            if intent.cabinets and k not in intent.cabinets:
                continue

            for day, lessons in enumerate(v):
                if intent.days and day not in intent.days:
                    continue

                for lesson, cl_s in lessons.items():
                    if intent.lessons and lesson not in intent.lessons:
                        continue

                    for cl, i in cl_s.items():
                        if intent.cl and cl not in intent.cl:
                            continue

                        res[k].total += len(i)
                        res[k].cl[cl] += len(i)
                        res[k].days[day] += len(i)
                        res[k].cabinets[lesson] += len(i)

        return _group_counter_res(res)
