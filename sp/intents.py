"""Вспомогательный класс намерений.

Часто при работе над расписанием, поиском, счётчиками или списком
изменений, нам бы хотелось более точно укзаать результаты работы.
Например если мы хотим получить резльтат только для определённого
класса или дня недели.

С этой целью был создан класс намерений, который используется как
фильтр, чтобы более точно описать что вы хотиет полчить от расписания.
"""

from datetime import datetime
from typing import Iterable, NamedTuple, TypeVar, Union

# Дни нелдели, используются для парсинга намерений
# TODO: Подключить из sp.emums
_days_names = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]
_short_days_names = ["пн", "вт", "ср", "чт", "пт", "сб"]


# Вспомогательный функции
# =======================

_T = TypeVar("_T")
def _ensure_list(a: _T) -> Union[_T, tuple[Union[str, int]]]:
    if a is not None:
        return (a,) if isinstance(a, (str, int)) else a


# Класс намерений
# ===============

class Intent(NamedTuple):
    """Вспомогательный класс, хранящий в себе намерение.

    Позволяет вам более точно укзаать результаты работы методов
    расписания.
    К примеру если вы производите подсчёт элементовр расписания, то
    можете укзаать что хотите считать для определённых дней недели
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

    #: Классы намерения (алиас на индекс 0)
    cl: set[str] = set()

    #: Дни недели намерения 0-5 (понедельник-суббота) (алиас на индекс 1)
    days: set[int] = set()

    #: Уроки намерения, например матем (алиас на индекс 2)
    lessons: set[str] = set()

    #: Кабенты расписания, например 328 (алиас на индекс 3)
    cabinets: set[str] = set()


    def to_str(self) -> str:
        """Запаковывает намерение в строку.

        Используется, для сохранения содержимого намерения в строке.
        Например при сохранении в базу данных или другое хранилище.
        После данное намерение легко можно будет распокавать из строки.

        Примеры запакованных намерений:

        - ``:::`` - Пустое намерение.
        - ``9в::матем:`` - Намерение с классом "9в" и "уроком математика".
        - ``:1,2::`` - Намерение с несколькими значениями (тут днями).

        :return: Запакованное намерение.
        :rtype: str
        """
        return ":".join(
            [",".join(map(str, x)) for x in self]
        )


    # Создание нового экземлпряа намерений
    # ====================================

    @classmethod
    def from_str(cls, s: str) -> "Intent":
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
            Мы предпогаем что вы никак не изменяли запакованную строку.

        Формат строки:

            ``cl,...:day,...:lessons,...:cabinets,cabinets2,cabinetsN``

        - "9в:1,2::" -> `Intent(cl=["9в"], days=[1, 2])`

        :param s: Строка с упакованным намерение.
        :type s: str

        :return: Новое распакованное намерение.
        :rtype: Intent
        """
        res: list[set[str | int]] = []
        for i, part in enumerate(s.split(":")):
            # Если это пустая строка, добавляем пустое множество
            if part == "":
                res.append(set())
            # Если это список дней, переводим в числа
            elif i == 1:
                res.append({int(x) for x in part.split(",")})
            else:
                res.append({x for x in part.split(",")})

        return Intent(*res)


    @classmethod
    def construct( # noqa
        cls, sc, cl: Union[Iterable[str], str]=(),
        days: Union[Iterable[int], int]=(),
        lessons: Union[Iterable[str], str]=(),
        cabinets: Union[Iterable[str], str]=()
    ):
        """Собирает новый экземпляр намерений.

        Занимается сборкой и валидацией нового экземпляра намерений.
        Вы можете передавать для сборки итерируемые контейнеры.

        .. code-block:: python

            i = Intent.construct(sc, cl="8а")
            # Intent({"8а"}, set(), set(), set())

            i = Intent.construct(sc, days=[2, 3], lessons="матем")

        Экзмеляр Schedule используется для валидации параметров
        относительно текущего расписания.

        :param sc: Экземпляр расписания уроков для валидации аргументов.
        :type sc: Schedule
        :param cl: Какие классы расписания добавить в намерение
        :type cl: Union[Iterable[str], str]
        :param days: Какие дни добавить в намерение (0-5)
        :type days: Union[Iterable[int], int]
        :param lessons: Какие уроки добавить в намерение (из l_index).
        :type lessons: Union[Iterable[str], str]
        :param cabinets: Какие кабинеты добавить в намерение (c_index).
        :type cabinets: Union[Iterable[str], str]
        :return: Проверенное намерение из переданных аргументов
        :rtype: Intent
        """
        return Intent(
            {x for x in _ensure_list(cl) if x in sc.lessons},
            {x for x in _ensure_list(days) if x < 6}, # noqa: PLR2004
            {x for x in _ensure_list(lessons) if x in sc.l_index},
            {x for x in _ensure_list(cabinets) if x in sc.c_index},
        )

    @classmethod
    def parse(cls, sc, args: Iterable[str]):
        """Извлекает намерения из списка строковых аргументов.

        .. code-block::

                Урок          Кабинет
                /             /
            > Химия вторнки 204 8а
                    /           /
                День       класс

        Также занимается валидацией параметров, использую класс
        Schedule относительно текущего расписнаия.

        :param sc: Экземпляр расписания уроков для валидации аргументов.
        :type sc: Schedule
        :param args: Арнументы парсинга намерений.
        :type args: Iterable[str]
        :return: Готовое намерение из строковых аргументов.
        :rtype: Intent
        """
        weekday = datetime.today().weekday()
        cl: list[str] = []
        days: list[int] = []
        lessons: list[str] = []
        cabinets: list[str] = []

        # Парсим аргументы
        for arg in args:
            # Пропускаем пустые аргументы
            if not arg:
                continue

            # Подставляем класс пользователя
            if arg == "?" and sc.cl is not None:
                cl.append(sc.cl)

            # Дни недели
            elif arg == "сегодня":
                days.append(weekday)

            elif arg == "завтра":
                today = weekday+1
                if today > 5: # noqa: PLR2004
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
                    i for i, k in enumerate(_days_names) if arg.startswith(k)
                ]
                days += [
                    i for i, k in enumerate(_short_days_names)
                    if arg.startswith(k)
                ]

        return Intent(set(cl), set(days), set(lessons), set(cabinets))


    # Создание экземпляра со значения по умолчанию
    # TODO: Прощайте методы реконструкции!
    # ============================================

    def reconstruct( # noqa
        self, sc, cl: Union[Iterable[str], str]=(),
        days: Union[Iterable[int], int]=(),
        lessons: Union[Iterable[str], str]=(),
        cabinets: Union[Iterable[str], str]=()
    ):
        """Пересобирает новый экземпляр намерений.

        Занимается сборкой и валидацией нового экземпляра намерений
        на основе текущего экземпляра.
        Вы можете передавать для сборки итерируемые контейнеры.
        Если вы не укзаали какой-то параметр, который уже был в
        экзмемпляре, он будет взят из текущего экземлпяра.

        .. code-block:: python

            # Intent({"8а"}, set(), set(), set())
            i = Intent.construct(sc, cl="8а")

            # Intent({"8а"}, set(), {"матем"}, set())
            new_i = i.reconstruct(sc, lessons="матем")

        Экзмеляр Schedule используется для валидации параметров
        относительно текущего расписания.

        :param sc: Экземпляр расписания уроков для валидации аргументов.
        :type sc: Schedule
        :param cl: Какие классы расписания добавить в намерение
        :type cl: Union[Iterable[str], str]
        :param days: Какие дни добавить в намерение (0-5)
        :type days: Union[Iterable[int], int]
        :param lessons: Какие уроки добавить в намерение (из l_index).
        :type lessons: Union[Iterable[str], str]
        :param cabinets: Какие кабинеты добавить в намерение (c_index).
        :type cabinets: Union[Iterable[str], str]
        :return: Пересобранное намерение из переданных аргументов
        :rtype: Intent
        """
        return Intent(
            {sc.get_class(x) for x in _ensure_list(cl)} or self.cl,
            {x for x in _ensure_list(days) if x < 6} or self.days, # noqa: PLR2004
            (
                {x for x in _ensure_list(lessons) if x in sc.l_index}
                or self.lessons
            ),
            (
                {x for x in _ensure_list(cabinets) if x in sc.c_index}
                or self.cabinets
            )
        )

    def reparse(self, sc, args: Iterable[str]):
        """Извлекает намерения из списка строковых аргументов.

        Собрает новый экземпляр намерений из строковых аргументов и
        параметров экземпляра.
        Если вы не указали какой-то параметр в строковых аргументах
        он будет подставлен из текущего экземлпяра.

        .. code-block::

                Урок          Кабинет
                /             /
            > Химия вторнки 204 8а
                    /           /
                День       класс

        Также занимается валидацией параметров, использую класс
        Schedule относительно текущего расписнаия.

        :param sc: Экземпляр расписания уроков для валидации аргументов.
        :type sc: Schedule
        :param args: Арнументы парсинга намерений.
        :type args: Iterable[str]
        :return: Готовое намерение из строковых аргументов.
        :rtype: Intent
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
                if today > 5: # noqa: PLR2004
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
                days += [
                    i for i, k in enumerate(_days_names) if arg.startswith(k)
                ]
                days += [
                    i for i, k in enumerate(_short_days_names)
                    if arg.startswith(k)
                ]

        return Intent(
            set(cl) or self.cl,
            set(days) or self.days,
            set(lessons) or self.lessons,
            set(cabinets) or self.cabinets
        )
