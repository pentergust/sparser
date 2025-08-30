"""базовый поставщик расписания."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sp.schedule import Schedule
    from sp.timetable import Timetable


class Provider(ABC):
    """Базовый поставщик расписания.

    Занимается поставкой расписания из некоторого источника.
    Это может быть файл, интернет-ресурс или прочее.
    """

    @abstractmethod
    async def schedule(self) -> Schedule:
        """Возвращает расписание уроков."""

    @abstractmethod
    async def timetable(self) -> Timetable:
        """Возвращает расписание звонков."""
