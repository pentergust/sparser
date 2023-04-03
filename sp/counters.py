"""
Функции счётчиков для расписания.

Author: Milinuri Nirvalen
"""

from .filters import Filters
from .filters import construct_filters
from .parser import Schedule

from collections import Counter
from typing import Optional


# Вспомогательные функции
# =======================

def group_counter_res(res: dict) -> dict:
    """Группирует результат работы счётчиков по total ключу.

    Args:
        res (dict): Результат работы счётчиков

    Returns:
        dict: Сгруппированыый результат работы счётчиков
    """
    groups = {}

    for k, v in res.items():
        key = v["total"]
        if not key:
            continue

        if key not in groups:
            groups[key] = {}

        groups[key][k] = v

    return groups

def reverse_counter(cnt: Counter) -> dict:
    """Меняет ключ и занчение Counter местами."""
    res = {}
    for k, v in cnt.items():
        if not v:
            continue

        if v not in res:
            res[v] = []
        res[v].append(k)
    return res




# Счётчики
# ========

def cl_counter(sc: Schedule, flt: Filters) -> dict:
    """Счётчик по классам с использованием sp.lessons.

    Args:
        sc (Schedule): Расписание уроков
        flt (Filters): Набор фильтров для уточнения подсчётов

    Returns:
        dict: Результат работы счётчика
    """
    res = {}

    for cl, days in sc.lessons.items():
        if flt.cl and cl not in flt.cl:
            continue

        day_counter = Counter()
        lessons_counter = Counter()
        cabinets_counter = Counter()

        for day, lessons in enumerate(days):
            if flt.days and day not in flt.days:
                continue

            for x in lessons:
                x = x.split(":")

                lessons_counter[x[0]] += 1
                for cabinet in x[1].split("/"):
                    cabinets_counter[cabinet] += 1

            day_counter[str(day)] = len(lessons)

        res[cl] = {"total": sum(day_counter.values()),
                   "days": day_counter,
                   "lessons": lessons_counter,
                   "cabinets": cabinets_counter}
    return res

def days_counter(sc: Schedule, flt: Filters) -> dict:
    """Счётчик по дням с использованием sc.lessons.

    Args:
        sc (Schedule): Расписание уроков
        flt (Filters): Набор фильтров для уточнения подсчётов

    Returns:
        dict: Результаты счётчика
    """

    res = {
        str(x): {"cl": Counter(),
                 "total": 0,
                 "lessons": Counter(),
                 "cabinets": Counter()
    } for x in range(6)}

    for cl, days in sc.lessons.items():
        if flt.cl and cl not in flt.cl:
            continue

        for day, lessons in enumerate(days):
            if flt.days and day not in flt.days:
                continue

            for lesson in lessons:
                lesson = lesson.split(":")
                res[str(day)]["cl"][cl] += 1
                res[str(day)]["lessons"][lesson[0]] += 1
                res[str(day)]["total"] += 1

                for x in lesson[1].split("/"):
                    res[str(day)]["cabinets"][x] += 1

    return res

def index_counter(sc: Schedule, flt: Filters,
                  cabinets_mode: Optional[bool]=False) -> dict:
    """Счётчик уроков/кабинетов с использованием индексов.

    Args:
        sc (Schedule): Расписание уроков
        flt (Filters): Набор фильтров для уточнения подсчётов
        cabinets_mode (bool, optional): Считать кабинеты вместо уроков

    Returns:
        dict: Результаты счётчика
    """
    res = {}

    if cabinets_mode:
        index = sc.c_index
        obj_filter = flt.cabinets
        another_filter = flt.lessons
    else:
        index = sc.l_index
        obj_filter = flt.lessons
        another_filter = flt.cabinets

    for k, v in index.items():
        if obj_filter and k not in obj_filter:
            continue

        if k not in res:
            res[k] = {"total": 0, "days": Counter(), "cl": Counter(),
                      "main": Counter()}

        for day, another_v in enumerate(v):
            if flt.days and day not in flt.days:
                continue

            for another, cl_s in another_v.items():
                if another_filter and another not in another_filter:
                    continue

                for cl, i in cl_s.items():
                    if flt.cl and cl not in flt.cl:
                        continue

                    res[k]["total"] += len(i)
                    res[k]["cl"][cl] += len(i)
                    res[k]["days"][str(day)] += len(i)
                    res[k]["main"][another] += len(i)
    return res

