"""
Набор фильтров для уточнения получения расписания.

Author: Milinuri Nirvalen
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


days_names = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]
short_days_names = ["пн", "вт", "ср", "чт", "пт", "сб"]

@dataclass
class Filters:
    """Набор фильтров для уточнения расписания."""
    cl: set
    days: set
    lessons: set
    cabinets: set


def to_list(arg) -> list:
    return [arg] if isinstance(arg, (str, int)) else arg

def construct_filters(sc,  cl: Optional[set]=None,
                      days: Optional[set]=None, lessons: Optional[set]=None,
                      cabinets: Optional[set]=None) -> Filters:
    """Собирает фильтр из входных аргументов.

    Args:
        sc (Schedule): Расписание уроков
        cl (set, optional): Для каких классов
        days (set, optional): Для каких дней недели
        lessons (set, optional): Для каких уроков
        cabinets (set, optional): Для каких кабинетов

    Returns:
        Filters: Набор фильтров для уточнения расписания
    """
    if cl is not None:
        cl = set(map(lambda x: sc.get_class(x), to_list(cl)))
    else:
        cl = set()

    if days is not None:
        days = set(filter(lambda x: x < 6, to_list(days)))
    else:
        days = set()

    if lessons is not None:
        lessons = set(filter(lambda x: x in sc.l_index, to_list(lessons)))
    else:
        lessons = set()

    if cabinets is not None:
        cabinets = set(filter(lambda x: x in sc.c_index, to_list(cabinets)))
    else:
        cabinets = set()

    return Filters(cl, days, lessons, cabinets)

def parse_filters(sc, args: list[str]) -> Filters:
    """Извлекает фильтры из списка аргументов.

    Args:
        sc (Schedule): Расписание уроков
        args (list[str]): Набор аргуметонов для сборки фильтров

    Returns:
        Filters: Набор фильтров для уточнения расписания
    """
    weekday = datetime.today().weekday()
    cl = []
    days = []
    lessons = []
    cabinets = []

    for arg in args:
        if not arg:
            continue

        if arg == "сегодня":
            days.append(weekday)

        elif arg == "завтра":
            days.append(weekday+1)

        elif arg.startswith("недел"):
            days = [0, 1, 2, 3, 4, 5]

        elif arg in sc.lessons:
            cl.append(arg)

        elif arg in sc.l_index:
            lessons.append(arg)

        elif arg in sc.c_index:
            cabinets.append(arg)

        else:
            # Если начало слова совпадает: пятниц... -а, -у, -ы...
            days += [i for i, k in enumerate(days_names) if arg.startswith(k)]
            days += [i for i, k in enumerate(short_days_names) if arg.startswith(k)]

    return construct_filters(sc, cl, days, lessons, cabinets)
