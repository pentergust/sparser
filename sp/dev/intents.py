"""Намерения расписание.

**Намерение** описывает желание получить какую-то информацию из
расписания.
Относитель к намерениям как к очень умным фильтрам.
Намерение состоит из ключа, по котрому производится сравнение, а также
значение, которое сравнивается с уроком.

Помимо одиночных намерений, также присутсовует цепочка намерений,
которая объединяет в себе сразу несколько намерений.
"""

from enum import IntEnum
from typing import NamedTuple, Self

# вспомогательный класс
# =====================

class Lesson(NamedTuple):
    """Описывает один конкретный урок в расписании.

    Урок - наименьшая еденица расписания, имеющая ценность.
    Данный кортеж наиболее полно представляет каждый урок.
    Поскольку урок явялется универсаьн для нескольких расписаний,
    некоторые его поля могут быть не заполнены.

    :param name: Название урока.
    :type name: str | None
    :param cl: Для какого класа проводится урок.
    :type cl: str | None
    :param location: В каком кабинете проводится урок.
    :type location: str | None
    :param teacher: Какое преподаватель проводит урок.
    :type teacher: str | None
    :param weekday: В какой день недели проводится урок.
    :type weekday: int | None
    :param metadata: Дополнительная информация об уроке.
    :type metadata: str | None
    :param index: Положение урока относительно дня.
    :type index: int | None
    """

    name: str | None = None
    cl: str | None = None
    location: str | None = None
    teacher: str | None = None
    weekday: int | None = None
    metadata: str | None = None
    index: int | None = None


# Вспомогатльные классы для описания намерения
# ============================================

class ScheduleObject(IntEnum):
    """Описывает все доступные элементы расписания.

    - ``LESSON``: Название урока в расписании.
    - ``CLASS``: Для какого класса проводится урок.
    - ``LOCATION``: В каком кабинете проводится урок.
    - ``TEACHER``: Какое преподаватель проводит урок.
    - ``WEEKDAY``: В какой день недели проводится урок.
    - ``METADATA``: Дополнительная информация о занятии.
    - ``INDEX``: Положение урока относительно дня.

    Значение перечисления расставлены в соостветсвии с индексами
    урока.
    При упаковке намерения вторая цифра означает ключ.
    """

    LESSON = 0   # name
    CLASS = 1    # cl
    LOCATION = 2 # location
    TEACHER = 3  # teacher
    WEEKDAY = 4  # weekday
    METADATA = 5 # metadata
    INDEX = 6 # index


class IntentType(IntEnum):
    """Описывает типы намерений.

    Тип намерения определяет как намерение будет взаимодействовать
    с уроком и другими намерениями.

    - ``AND`` (по умолчанию): Не пропускает. если хотя бы одно умловие
        в цепочке не соответствует.
    - ``NOT``: Обратное действие. Пропускает все условия значения,
        которые отличаются от данного.

    При упаковке тип намерения указывается первым числом.
    """

    AND = 0 # ""
    OR = 1
    NOT = 2 # !

# Исключениея
# ===========

class ParseIntentError(Exception):
    """Если не удалось распаковать намерение из строки.

    Возникает когад допущена ошибка в формате строки, при использовании
    метода ``Intent.unpack()``.
    """

    pass


# Класс намерения
# ===============

class Intent(NamedTuple):
    """Намерение что-либо получить из расписания.

    Данный класс используется как одиночный фильтр для урока.
    Используется для фильтрации уроков по конкретному критерию.
    Поддерживается AND и NOT режимы работы.
    Во втором режеми он будет пропусть все значения, кроме заданного.

    :param type: Тип намерения, AND или NOT.
    :type type: IntentType
    :param key: Ключ для сравнения с уроком.
    :type key: ScheduleObject
    :param value: Значение для сравнения с уроком.
    :type value: str | int
    """

    type: IntentType
    key: ScheduleObject
    value: str | int

    # Сериализация и десериализация намерений
    # =======================================

    @classmethod
    def unpack(cls, intent_str) -> Self:
        """Распаковывает намерение из строки.

        Обратный метод для запаковки в строку..
        Полезное если вы решили сохранить намерение в базе данных и
        теперь желает восстановить его из строки.

        :param intent_str: Запакованное в строку намерение
        :type intent_str: str
        :raises ParseIntentError: При неправильном формате намерения.
        :return: Экземпляр намерения из строки.
        :rtype: Intent
        """
        try:
            intent_type = int(intent_str[0])
            intent_key = int(intent_str[1])
            value = intent_str[2:]
            return Intent(
                IntentType(intent_type),
                ScheduleObject(intent_key),
                value
            )
        except ValueError:
            raise ParseIntentError(f"Unable to parse intent from {intent_str}")

    def pack(self) -> str:
        """Запаковывает намерение в строку.

        Формат строки следующий: ``00матем``.

        - Первыя цифра указывает нам на тип намерения (IntentType).
        - Вторая цифра указывается на ключ (ScheduleObject).
        - Все последующие символы являются значениями ключа.

        :returns: Запакованное в строку намерение.
        :rtype: str
        """
        return f"{self.type.value}{self.key.value}{self.value}"


    # Фильтрация намерений
    # ====================

    def filter(self, lesson: Lesson) -> bool:
        """Проверяет урок на соответсвие намерения.

        Сравнивать значение урока по определённому ключу.

        :param lesson: Урок, который необхоидмо провреить.
        :type lesson: Lesson
        :returb: Соответствует ли урок намерению.
        :rtype: bool
        """
        lesson_value = lesson[self.key.value]
        if lesson_value is None:
            return False
        if lesson_value == self.value:
            return True if self.type != IntentType.NOT else False
        return False if self.type != IntentType.NOT else True


# Класс цепочки намерений
# =======================

class IntentChain:
    """Цепочка намерений.

    Цепочка намерений исползуется дл объединения нескольких намерений.
    для создания более точный намерений.
    К примеру это можно использовать чтобы более точно укзааться
    результаты поиска.
    Имеет те же методы, что и обычные намерения.
    """

    def __init__(self, chain: list[Intent] = None):
        self._intents: list[Intent] = chain or []

    @property
    def intents(self) -> list[Intent]:
        """Возвращает полный список всех намерений цепочки."""
        return self._intents

    # Сериализация и десериализация
    # =============================

    @classmethod
    def unpack(cls, chain_str: str) -> Self:
        """Распаковывает цепочку намерений из строки.

        Обратный метод для запаковки.
        К примеру если вы собираетесь достать намерения из базы данных
        или прочего хранилища, где они ранее были запакованы.

        :param chain_str: Строка с запакованной цепочко.
        :type chain_str: str
        :returns: Востановленная цепочка намерений.
        :rtype: IntentChain
        """
        return IntentChain(
            chain=[Intent.unpack(i_str) for i_str in chain_str.split(":")]
        )

    def pack(self) -> str:
        """Запаковывает цепочка намерений в строку.

        **Пример строки**: ``00матем:019в``

        Где ``:`` для разделения звеньев цепи.
        Внутри же каждого звена нахоидся запакованное намерение.
        Более подробно о том как запаковываются намерения можно узнать
        в методе :py:class:

        после вы можете использовать запакованную цепочку намерений
        к примеру для хранения в базе данных или других хранилищах.
        В запакованной строке находится достаточно информации, чтобы
        после обратно восстановить её в полноценную цепочку намерений.

        :returns: Запакованная в строку цепочка намерений.
        :rtype: str
        """
        return ":".join(i.pack() for i in self._intents)


    # Упрвление цепочкой намерений
    # ============================

    def add(self,
        key: ScheduleObject,
        value: str | int,
        chain_type: IntentType = IntentType.AND
    ) -> Self:
        """Добавляет намерение в цепочку.

        .. note:: Не производится проверки на повтори.
            В отличие от метода ``include()``, метод ``add()`` не
            производит проеерки на дубликаты.
            Так что будьте аккуратнее, когда добавляете новые намерения.

        Сначала преобразует входящие аргументы в экземпляр намерения.
        А после уже добавляет его в цепочку.

        :param key: По какому ключу будет справниваться намерение.
        :type key: ScheduleObject
        :param value: По какому значению ключабу будет сравниваться.
        :type value: str | int
        :param chain_type: Тип цепочки, И или НЕ.
        :type chain_type: IntentType
        :returns: Обновлённая цепочка намерений.
        :rtype: IntentChain
        """
        self._intents.append(
            Intent(type=chain_type, key=key, value=value)
        )
        return self

    def include(self, intent: Intent) -> Self:
        """Включает намерение в цеопчку.

        также предварительно проверяет, что данного намерения ещё
        нету в изначальной цепочке.

        .. code-block python

            ic = IntentChain()
            ic.include(
                Intent(IntentType.AND, ScheduleObject.LESSON, "Матем")
            ).include(
                Intent(IntentType.AND, ScheduleObject.CLASS, "9в")
            )

        Если вам нужно создать и сразу же включить намерение, то
        воспользуйтесь методом ``add()``.

        :param intent: Намерение для включения.
        :type intent: Intent
        :returns: Обновлённая цепочка намерений.
        """
        if intent in self._intents:
            return ValueError("Intent is alredy in chain")
        self._intents.append(intent)
        return self

    def extend(self, chain: Self) -> Self:
        """Расширяет цепочки намерений засчёт другой цеопчки.

        Будет поочерёдно добавлять намерения в цепочки.
        Гарантирует что все намерения в цепочке уникальный.

        :param chain: Цепочка намерений для включения.
        :type chain: IntentChain
        :returns: Обновлённая цепочка намерений.
        :rtype: IntentChai
        """
        for intent in chain.intents:
            self.include(intent)
        return self


    # Фильтрация намерений
    # ====================

    def filter(self, lesson: Lesson) -> bool:
        """Производит фильтрацию урока по цепочке намерений.

        Производит фильтрацию по каждому звену цепи, пока одно из нех
        не вернёт истину.
        Если в процесе столкнётся со звеном AND, то вернёт его результат.

        :param lesson: Урок, который нужно проверить на цепочку фильтров.
        :type lessons: Lesson
        :returns: Соответствует ли урок цепочке фильров.
        """
        if not isinstance(lesson, Lesson):
            return False

        for chain in self._intents:
            res = chain.filter(lesson)
            if res:
                return True
            elif chain.type == IntentType.AND:
                return False
        return False


    # Магические методы представления
    # ===============================

    def __repr__(self) -> str:
        """Немного информации о цепочке намерений."""
        return f"{self.__class__.__name__}({self._intents.__repr__()})"

    def __str__(self) -> str:
        """Запаковывает намерение в строку.

        Используется для как синтаксический сахар для более удобной
        запаковки цепочки намерений.

        .. code-block:: python
            str(chain)

            # аналогично
            chain.pack()

        :return: Запакованное в строку намерение.
        :rtype: str
        """
        return self.pack()

    # Магические методы сравнения
    # ===========================

    def __eq__(self, another: Self) -> bool:
        """Проверяет что две цепочки намерений совпадают."""
        return self._intents == another.intents

    def __ne__(self, another: Self) -> bool:
        """Проверяет что две цепочки намерений не совпадают."""
        return self._intents != another.intents


    # прочие магические методы
    # ========================

    def __contains__(self, lesson: Lesson) -> bool:
        """Проверяет наличие урока в цепочке намерений.

        Используется как синтаксический сахар для метода ``filter()``.

        ..code-block:: python
            lesson in chain

            # аналогично
            chain.filter(lesson)

        :param lesson: Урок, который необходимо проекрить.
        :type lesson: Lesson
        :returns: Находится ли урок в области действия намерений.
        :rtype: bool
        """
        return self.filter(lesson)

    def __len__(self) -> int:
        """Возвращает длину цепочки намерений."""
        return len(self._intents)


    # Магическое сложение цепочек
    # ===========================

    def __add__(self, other: Intent | Self) -> Self:
        """Сложение намерений.

        Позволяет добавлять намерения в цепочку.
        Работает как с экземплярами намерений, так и с целыми цепочками
        намерений.
        В случае с цепочкой намерений, каждое намерение будет включено
        отдельно.

        :param other: Намерение или цепочка намерений для добавления.
        :type other: Intent | IntentChain
        :return: Обновленная цепочка намерений.
        :rtype: IntentChain
        """
        if isinstance(other, Intent):
            return self.include(other)
        elif isinstance(other, IntentChain):
            return self.extend(other)
        else:
            raise TypeError(f"Cannot add {type(other)} tp IntentChain")
