"""Урок."""

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

# TODO: Специальные классы для уроков на день и на неделю со своими методами

DayLessons = Sequence[Lesson | None]
WeekLessons = Sequence[DayLessons]

