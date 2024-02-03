"""Вспомогательные функции для подсчёта
количества элементов в расписании.

Author: Milinuri Nirvalen
"""

from collections import Counter, defaultdict
from typing import Optional

from .intents import Intent
from .parser import Schedule

# Вспомогательные функции
# =======================

def group_counter_res(res: dict) -> dict:
    """Группирует результат работы счётчиков по total ключу.

    Args:
        res (dict): Результат работы счётчиков

    Returns:
        dict: Сгруппированыый результат работы счётчиков
    """
    groups = defaultdict(dict)
    for k, v in res.items():
        key = v["total"]
        if not key:
            continue

        groups[key][k] = v

    return groups

def reverse_counter(cnt: Counter) -> dict:
    """Меняет ключ и занчение Counter местами."""
    res = defaultdict(list)
    for k, v in cnt.items():
        if not v:
            continue

        res[v].append(k)
    return res


# Счётчики
# ========

def cl_counter(sc: Schedule, intent: Intent) -> dict:
    """Счётчик по классам с использованием sp.lessons.

    Args:
        sc (Schedule): Расписание уроков
        intent (Intent): Намерения для уточнения подсчётов

    Returns:
        dict: Результат работы счётчика
    """
    res = {}

    for cl, days in sc.lessons.items():
        if intent.cl and cl not in intent.cl:
            continue

        day_counter = Counter()
        lessons_counter = Counter()
        cabinets_counter = Counter()

        for day, lessons in enumerate(days):
            if intent.days and day not in intent.days:
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

def days_counter(sc: Schedule, intent: Intent) -> dict:
    """Счётчик по дням с использованием sc.lessons.

    Args:
        sc (Schedule): Расписание уроков
        intent (Intent): Намерения для уточнения подсчётов

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
        if intent.cl and cl not in intent.cl:
            continue

        for day, lessons in enumerate(days):
            if intent.days and day not in intent.days:
                continue

            for lesson in lessons:
                lesson = lesson.split(":")
                res[str(day)]["cl"][cl] += 1
                res[str(day)]["lessons"][lesson[0]] += 1
                res[str(day)]["total"] += 1

                for x in lesson[1].split("/"):
                    res[str(day)]["cabinets"][x] += 1

    return res

def index_counter(sc: Schedule, intent: Intent,
                  cabinets_mode: Optional[bool]=False) -> dict:
    """Счётчик уроков/кабинетов с использованием индексов.

    Args:
        sc (Schedule): Расписание уроков
        intent (Intent): Намерения для уточнения подсчётов
        cabinets_mode (bool, optional): Считать кабинеты вместо уроков

    Returns:
        dict: Результаты счётчика
    """
    res = {}

    if cabinets_mode:
        index = sc.c_index
        obj_filter = intent.cabinets
        another_filter = intent.lessons
    else:
        index = sc.l_index
        obj_filter = intent.lessons
        another_filter = intent.cabinets

    for k, v in index.items():
        if obj_filter and k not in obj_filter:
            continue

        if k not in res:
            res[k] = {"total": 0, "days": Counter(), "cl": Counter(),
                      "main": Counter()}

        for day, another_v in enumerate(v):
            if intent.days and day not in intent.days:
                continue

            for another, cl_s in another_v.items():
                if another_filter and another not in another_filter:
                    continue

                for cl, i in cl_s.items():
                    if intent.cl and cl not in intent.cl:
                        continue

                    res[k]["total"] += len(i)
                    res[k]["cl"][cl] += len(i)
                    res[k]["days"][str(day)] += len(i)
                    res[k]["main"][another] += len(i)
    return res
