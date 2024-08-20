from enum import IntEnum, StrEnum

from typing import NamedTuple, Self


# вспомогательный класс
# =====================

class Lesson(NamedTuple):
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
    LESSON = 0   # name
    CLASS = 1    # cl
    LOCATION = 2 # location
    TEACHER = 3  # teacher
    WEEKDAY = 4  # weekday
    METADATA = 5 # metadata
    INDEX = 6 # index


class IntentType(IntEnum):
    AND = 0
    OR = 1
    NOT = 2


# Исключениея
# ===========

class ParseIntentError(Exception):
    pass


# Класс намерения
# ===============

class Intent(NamedTuple):
    type: IntentType
    key: ScheduleObject
    value: str | int

    # Сериализация и десериализация намерений
    # =======================================

    @classmethod
    def unpack(cls, intent_str) -> Self:
        try:
            intent_type = int(intent_str[0])
            intent_key = int(intent_str[1])
            value = intent_str[2:]
            return Intent(
                IntentType(intent_type),
                ScheduleObject(intent_key),
                value
            )
        except ValueError as e:
            raise ParseIntentError(f"Unable to parse intent from {intent_str}")

    def pack(self) -> str:
        return f"{self.type.value}{self.key.value}{self.value}"


    # Фильтрация намерений
    # ====================

    def filter(self, lesson: Lesson) -> bool:
        lesson_value = lesson[self.key.value]
        if lesson_value is None:
            return False
        if lesson_value == self.value:
            return True if self.type != IntentType.NOT else False
        return False if self.type != IntentType.NOT else True


# Класс цепочки намерений
# =======================

class IntentChain:
    def __init__(self, chain: list[Intent] = None):
        self._intents: list[Intent] = chain or []

    @property
    def intents(self) -> list[Intent]:
        return self._intents

    # Сериализация и десериализация
    # =============================

    @classmethod
    def unpack(cls, chain_str: str) -> Self:
        return IntentChain(
            chain=[Intent.unpack(i_str) for i_str in chain_str.split(":")]
        )

    def pack(self) -> str:
        return ":".join(i.pack() for i in self._intents)


    # Упрвление цепочкой намерений
    # ============================

    def add(self,
        key: ScheduleObject,
        value: str | int,
        chain_type: IntentType = IntentType.OR
    ) -> Self:
        self._intents.append(
            Intent(type=chain_type, key=key, value=value)
        )
        return self


    # Фильтрация намерений
    # ====================

    def filter(self, lesson: Lesson) -> bool:
        for chain in self._intents:
            res = chain.filter(lesson)
            if res:
                return True
            elif chain.type == IntentType.AND:
                return False
        return False
