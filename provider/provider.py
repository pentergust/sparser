"""Поставщик расписания."""

from provider.types import Schedule, ScheduleFilter, Status, TimeTable


class Provider:
    """Поставщик расписания."""

    async def timetable(self) -> TimeTable:
        """Возвращает расписание звонков."""

    async def status(self) -> Status:
        """Возвращает статус поставщика."""

    async def schedule(self, filters: ScheduleFilter) -> Schedule:
        """Возвращает расписание уроков."""
