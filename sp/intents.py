"""Вспомогательный класс намерений.

Часто при работе над расписанием, поиском, счётчиками или списком
изменений, нам бы хотелось более точно указать результаты работы.
Например если мы хотим получить результат только для определённого
класса или дня недели.

С этой целью был создан класс намерений, который используется как
фильтр, чтобы более точно описать что вы хотите получить от расписания.
"""

from collections.abc import Iterable
from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple, Self, TypeVar

from sp.enums import DAY_NAMES, SHORT_DAY_NAMES

if TYPE_CHECKING:
    from sp.parser import Schedule

# Вспомогательный функции
# =======================

_T = TypeVar("_T")


def _ensure_list(a: _T) -> _T | tuple[str | int]:
    return (a,) if isinstance(a, str | int) else a


# Класс намерений
# ===============


class Intent(NamedTuple):
    """Вспомогательный класс, хранящий в себе намерение.

    Позволяет вам более точно указать результаты работы методов
    расписания.
    К примеру если вы производите подсчёт элементов расписания, то
    можете указать что хотите считать для определённых дней недели
    или классов.

    Так вы можете уточнять результаты работы со всеми методами, что
    поддерживают намерения.

    .. warning:: Пожалуйста не вводите данные вручную.

        Если вы хотите собрать новое намерение, то используйте
        метод класса ``construct``:

        .. code-block:: python

            sc = Schedule()
            i = Intent.construct(sc, cl="8в")

        Или воспользуйтесь методом `parse`:

        .. code-block:: python

            sc = Schedule()
            prompt = "9в матем 204"
            i = Intent.parse(sc, prompt.split())

        Ручная сборка намерения используется **только** в тех случаях,
        когда вы уверены в том что переданные данные присутствуют в
        расписании.
    """

    #: Классы намерения (ссылка на индекс 0)
    cl: set[str] = set()

    #: Дни недели намерения 0-5 (понедельник-суббота) (ссылка на индекс 1)
    days: set[int] = set()

    #: Уроки намерения, например матем (ссылка на индекс 2)
    lessons: set[str] = set()

    #: Кабинеты расписания, например 328 (ссылка на индекс 3)
    cabinets: set[str] = set()

    def to_str(self) -> str:
        """Запаковывает намерение в строку.

        Используется, для сохранения содержимого намерения в строке.
        Например при сохранении в базу данных или другое хранилище.
        После данное намерение легко можно будет распаковать из строки.

        Примеры запакованных намерений:

        - ``:::`` - Пустое намерение.
        - ``9в::матем:`` - Намерение с классом "9в" и "уроком математика".
        - ``:1,2::`` - Намерение с несколькими значениями (тут днями).
        """
        return ":".join([",".join(map(str, x)) for x in self])

    # Создание нового экземпляра намерений
    # ====================================

    @classmethod
    def from_str(cls, s: str) -> Self:
        """Распаковывает намерение из строки.

        Получает экземпляр намерение, которое ранее было упаковано
        в строку через метод ``to_str()``.

        .. code-block:: python

            # Запаковываем намерение
            sc = Schedule()
            i = Intent.construct(sc, cl="8в")
            i_str = i.to_str()

            # Тут будет ваш код...
            # ... Что-то делаем...
            # ... И спустя долгое время...

            # а теперь вы захотели загрузить намерение из строки
            i = Intent.from_str(i_str)

        .. note::

            Обратите внимание, что метод from_str не производит
            валидацию передаваемых значений относительно расписания.
            Мы предполагаем что вы никак не изменяли запакованную строку.

        Формат строки:

            ``cl,...:day,...:lessons,...:cabinets,cabinets2,cabinetsN``

        - "9в:1,2::" -> `Intent(cl=["9в"], days=[1, 2])`
        """
        res: list[set[str]] = []
        days: set[int] = set()
        for i, part in enumerate(s.split(":")):
            # Если это пустая строка, добавляем пустое множество
            if part == "":
                res.append(set())
            # Если это список дней, переводим в числа
            elif i == 1:
                days = {int(x) for x in part.split(",")}
            else:
                res.append({x for x in part.split(",")})

        return cls(res[0], days, res[1], res[2])

    @classmethod
    def construct(  # noqa
        cls,
        sc: "Schedule",
        cl: Iterable[str] | str = (),
        days: Iterable[int] | int = (),
        lessons: Iterable[str] | str = (),
        cabinets: Iterable[str] | str = (),
    ) -> Self:
        """Собирает новый экземпляр намерений.

        Занимается сборкой и валидацией нового экземпляра намерений.
        Вы можете передавать для сборки итерируемые контейнеры.

        .. code-block:: python

            i = Intent.construct(sc, cl="8а")
            # Intent({"8а"}, set(), set(), set())

            i = Intent.construct(sc, days=[2, 3], lessons="матем")

        Экземпляр Schedule используется для валидации параметров
        относительно текущего расписания.
        """
        return cls(
            {str(x) for x in _ensure_list(cl) if x in sc.lessons},
            {int(x) for x in _ensure_list(days) if int(x) < 6},  # noqa: PLR2004
            {str(x) for x in _ensure_list(lessons) if x in sc.l_index},
            {str(x) for x in _ensure_list(cabinets) if x in sc.c_index},
        )

    @classmethod
    def parse(cls, sc: "Schedule", args: Iterable[str]) -> Self:
        """Извлекает намерения из списка строковых аргументов.

        .. code-block:: text

                Урок          Кабинет
                /             /
            > Химия вторник 204 8а
                    /           /
                День       класс

        Также занимается валидацией параметров, использую класс
        Schedule относительно текущего расписания.
        """
        weekday = datetime.today().weekday()
        cl: list[str] = []
        days: list[int] = []
        lessons: list[str] = []
        cabinets: list[str] = []

        # Получение аргументы
        for arg in args:
            # Пропускаем пустые аргументы
            if not arg:
                continue

            # Дни недели
            elif arg == "сегодня":
                days.append(weekday)

            elif arg == "завтра":
                today = weekday + 1
                if today > 5:  # noqa: PLR2004
                    today = 0

                days.append(today)

            elif arg.startswith("недел"):
                days = [0, 1, 2, 3, 4, 5]

            # Подставляем классы
            elif arg in sc.lessons:
                cl.append(arg)

            # Ищем по названию урока
            elif arg in sc.l_index:
                lessons.append(arg)

            # Ищем по кабинету
            elif arg in sc.c_index:
                cabinets.append(arg)

            else:
                # Если начало слова совпадает: пятниц... -а, -у, -ы...
                days += [
                    i for i, k in enumerate(DAY_NAMES) if arg.startswith(k)
                ]
                days += [
                    i
                    for i, k in enumerate(SHORT_DAY_NAMES)
                    if arg.startswith(k)
                ]

        return cls(set(cl), set(days), set(lessons), set(cabinets))

    # Создание экземпляра со значения по умолчанию
    # TODO: Прощайте методы реконструкции!
    # ============================================

    def reconstruct(  # noqa
        self,
        sc: "Schedule",
        cl: Iterable[str] | str = (),
        days: Iterable[int] | int = (),
        lessons: Iterable[str] | str = (),
        cabinets: Iterable[str] | str = (),
    ) -> "Intent":
        """Собирает новый экземпляр намерений.

        Занимается сборкой и валидацией нового экземпляра намерений
        на основе текущего экземпляра.
        Вы можете передавать для сборки итерируемые контейнеры.
        Если вы не указали какой-то параметр, который уже был в
        экземпляре, он будет взят из текущего экземпляра.

        .. code-block:: python

            # Intent({"8а"}, set(), set(), set())
            i = Intent.construct(sc, cl="8а")

            # Intent({"8а"}, set(), {"матем"}, set())
            new_i = i.reconstruct(sc, lessons="матем")

        Экземпляр Schedule используется для валидации параметров
        относительно текущего расписания.
        """
        return Intent(
            {str(x) for x in _ensure_list(cl) if x is sc.lessons} or self.cl,
            {int(x) for x in _ensure_list(days) if int(x) < 6} or self.days,  # noqa: PLR2004
            (
                {str(x) for x in _ensure_list(lessons) if x in sc.l_index}
                or self.lessons
            ),
            (
                {str(x) for x in _ensure_list(cabinets) if x in sc.c_index}
                or self.cabinets
            ),
        )
