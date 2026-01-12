"""Представление Урока."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Lesson:
    """Исчерпывающая информация об уроке."""

    cl: str
    """Для какого класса проводится."""

    name: str
    """Название урока."""

    cabinets: Sequence[str]
    """В каких кабинетах проводится.

    Будет указано несколько, если класс разделяется на группы.
    """

    day: int
    """В какой день недели проводится. От 0 до 5."""

    order: int
    """Порядковые номер урока в дне."""


@dataclass(slots=True, frozen=True)
class DayLesson:
    """Урок на день.

    Содержит не полную информацию об уроке, без указания дня.
    """

    cl: str
    """Для какого класса проводится."""

    name: str
    """Название урока."""

    cabinets: Sequence[str]
    """В каких кабинетах проводится.

    Будет указано несколько, если класс разделяется на группы.
    """

    def to_lesson(self, day: int, order: int) -> Lesson:
        """Дополняет информацию до полноценного урока."""
        return Lesson(
            cl=self.cl,
            name=self.name,
            cabinets=self.cabinets,
            day=day,
            order=order,
        )


@dataclass(slots=True, frozen=True)
class PartialLesson:
    """Частичная информация об уроке.

    Содержит не только необходимую информацию об уроке.
    """

    name: str
    """Название урока."""

    cabinets: Sequence[str]
    """В каких кабинетах проводится.

    Будет указано несколько, если класс разделяется на группы.
    """

    def to_lesson(self, cl: str, day: int, order: int) -> Lesson:
        """Дополняет информацию до полноценного урока."""
        return Lesson(
            cl=cl, name=self.name, cabinets=self.cabinets, day=day, order=order
        )

