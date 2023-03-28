"""Набло фильтров для уточнения получения расписания.

Author: Milinuri Nirvalen
"""
from datetime import datetime
from typing import Optional


days_parts = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]

class Filters:
    """Набор фильтров для получени уточнения расписания."""
    def __init__(self, sc, cl: Optional[list]=None,
                 days: Optional[list]=None,
                 lessons: Optional[list]=None,
                 cabinets: Optional[list]=None):
        super(Filters, self).__init__()
        self.sc = sc or []
        self._days = days or []
        self.cl = cl or []
        self.lessons = lessons or []
        self.cabinets = cabinets or []

    @property
    def days(self) -> set:
        return set(filter(lambda x: x < 6, self._days))

    def get_cl(self) -> list:
        return self.cl if self.cl else [self.sc.cl]

    def parse_args(self, args: list) -> None:
        weekday = datetime.today().weekday()

        for arg in args:
            if not arg:
                continue

            if arg == "сегодня":
                self._days.append(weekday)

            elif arg == "завтра":
                self._days.append(weekday+1)

            elif arg.startswith("недел"):
                self._days = [0, 1, 2, 3, 4, 5]

            elif arg in self.sc.lessons:
                self.cl.append(arg)

            elif arg in self.sc.l_index:
                self.lessons.append(arg)

            elif arg in self.sc.c_index:
                self.cabinets.append(arg)

            else:
                # Если начало слова совпадает: пятниц... -а, -у, -ы...
                self._days += [i for i, k in enumerate(days_parts) if arg.startswith(k)]
