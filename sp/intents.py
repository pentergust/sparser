"""Вспомогательный класс намерений для уточнения работы
и фильтрации результатов методов Schedule.

При получении например списка изменений может потребоваться уточнить
результат относительно дня, кабинета, класса и т.д.
Этот класс объединяет множество аргементов: cl, days.
lesons. cabinets, а также их валидацию и сборку.

Author: Milinuri Nirvalen
"""

from datetime import datetime
from typing import Iterable, NamedTuple, TypeVar, Union

_days_names = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]
_short_days_names = ["пн", "вт", "ср", "чт", "пт", "сб"]

_T = TypeVar("T")
def _ensure_list(a: _T) -> tuple[_T]:
    if a is not None:
        return (a,) if isinstance(a, (str, int)) else a


class Intent(NamedTuple):
    cl: set[str] = set()
    days: set[int] = set()
    lessons: set[str] = set()
    cabinets: set[str] = set()


    def to_str(self) -> str:
        """Запаковывает намерение в строку."""
        return ":".join([",".join(map(str, x)) for x in self])


    # Создание нового экземлпряа намерений
    # ====================================

    @classmethod
    def from_str(cls, s: str):
        """Получает намерение упакованной из строки.

        Формат:
            cl:day:lessons:cabinets,cabinets2,cabinetsN

        "9в:1,2::" -> Intent(cl=["9в"], days=[1, 2])

        Args:
            s (str): Строка с упаковынным намерением.

        Returns:
            Intent: Распакованный экземпляр намерений
        """
        res = []
        for i, part in enumerate(s.split(":")):
            if part == "":
                res.append(set())
            elif i == 1:
                res.append({int(x) for x in part.split(",")})
            else:
                res.append({x for x in part.split(",")})

        return Intent(*res)


    @classmethod
    def construct(cls, sc, cl: Iterable[str]=(),
            days: Iterable[int]=(), lessons: Iterable[str]=(),
            cabinets: Iterable[str]=()):
        """Собирает новый экземпляр намерений.

        Занимается сборкой и валидацией нового экземпляра намерений.
        Вы можете передавать для сборки итерируемые контейнеры.

        i = Intent.construct(sc, cl="8а")
        i // Intent({"8а"}, set(), set(), set())

        Экзмеляр Schedule используется для валидации параметров
        относительно текущего расписания.

        Args:
            sc (Schedule): Экземлпяр расписание уроков
            cl (Iterable[str], optional): Для каких классов
            days (Iterable[int], optional): Для каких дней недели
            lessons (Iterable[str], optional): Для каких уроков
            cabinets (Iterable[str], optional): Для каких кабинетов

        Returns:
            Intent: Новый экземпляр намерений
        """
        return Intent(
            {sc.get_class(x) for x in _ensure_list(cl)},
            {x for x in _ensure_list(days) if x < 6},
            {x for x in _ensure_list(lessons) if x in sc.l_index},
            {x for x in _ensure_list(cabinets) if x in sc.c_index},
        )

    @classmethod
    def parse(cls, sc, args: list[str]):
        """Извлекает намерения из списка строковых аргументов.

           Урок          Кабинет
          /             /
        > Химия вторнки 204 8а
                /           /
            День       класс

        Также занимается валидацией параметров, использую класс
        Schedule относительно текущего расписнаия.

        Args:
            sc (Schedule): Расписание уроков
            args (list[str]): Набор аргуметонов для сборки намерений

        Returns:
            Intent: Новый экземпляр намерений
        """
        weekday = datetime.today().weekday()
        cl = []
        days = []
        lessons = []
        cabinets = []

        for arg in args:
            if not arg:
                continue

            if arg == "?" and sc.cl is not None:
                cl.append(sc.cl)

            elif arg == "сегодня":
                days.append(weekday)

            elif arg == "завтра":
                today = weekday+1
                if today > 5:
                    today = 0

                days.append(today)

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
                days += [i for i, k in enumerate(_days_names) if arg.startswith(k)]
                days += [i for i, k in enumerate(_short_days_names) if arg.startswith(k)]

        return Intent(set(cl), set(days), set(lessons), set(cabinets))


    # Создание экземпляра со значения по умолчанию
    # ============================================

    def reconstruct(self, sc, cl: Union[set, tuple]=(),
            days: Union[set, tuple]=(), lessons: Union[set, tuple]=(),
            cabinets: Union[set, tuple]=()):
        """Пересобирает новый экземпляр намерений.

        Занимается сборкой и валидацией нового экземпляра намерений.
        Вы можете передавать для сборки итерируемые контейнеры.
        Если вы не укзаали какой-то параметр, который уже был в
        экзмемпляре, он будет взят из текущего экземлпяра.

        i = Intent.construct(sc, cl="8а")
        i // Intent({"8а"}, set(), set(), set())
        new_i = i.reconstruct(sc, lessons="матем")
        new_i  // Intent({"8а"}, set(), {"матем"}, set())

        Экзмеляр Schedule используется для валидации параметров
        относительно текущего расписания.

        Args:
            sc (Schedule): Экземлпяр расписание уроков
            cl (Iterable[str], optional): Для каких классов
            days (Iterable[int], optional): Для каких дней недели
            lessons (Iterable[str], optional): Для каких уроков
            cabinets (Iterable[str], optional): Для каких кабинетов

        Returns:
            Intent: Новый пересобранный экземпляр намерений
        """
        return Intent(
            {sc.get_class(x) for x in _ensure_list(cl)} or self.cl,
            {x for x in _ensure_list(days) if x < 6} or self.days,
            {x for x in _ensure_list(lessons) if x in sc.l_index}  or self.lessons,
            {x for x in _ensure_list(cabinets) if x in sc.c_index}  or self.cabinets,
        )

    def reparse(self, sc, args: list[str]):
        """Извлекает намерения из списка строковых аргументов.

        Собрает новый экземпляр намерений из строковых аргументов и
        параметров экземпляра.
        Если вы не указали какой-то параметр в строковых аргументах
        он будет подставлен из текущего экземлпяра.

           Урок          Кабинет
          /             /
        > Химия вторнки 204 8а
                /           /
            День       класс

        Также занимается валидацией параметров, использую класс
        Schedule относительно текущего расписнаия.

        Args:
            sc (Schedule): Расписание уроков
            args (list[str]): Набор аргуметонов для сборки намерений

        Returns:
            Intent: Новый экземпляр намерений
        """
        weekday = datetime.today().weekday()
        cl = []
        days = []
        lessons = []
        cabinets = []

        for arg in args:
            if not arg:
                continue

            if arg == "?" and sc.cl is not None:
                cl.append(sc.cl)

            if arg == "сегодня":
                days.append(weekday)

            elif arg == "завтра":
                today = weekday+1
                if today > 5:
                    today = 0

                days.append(today)

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
                days += [i for i, k in enumerate(_days_names) if arg.startswith(k)]
                days += [i for i, k in enumerate(_short_days_names) if arg.startswith(k)]

        return Intent(
            set(cl) or self.cl,
            set(days) or self.days,
            set(lessons) or self.lessons,
            set(cabinets) or self.cabinets
        )
