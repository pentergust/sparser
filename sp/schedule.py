"""расписание уроков."""

from collections.abc import Mapping

from sp.lesson import PartialLesson

PartialWeekLessons = list[list[PartialLesson | None]]
ScheduleMap = Mapping[str, PartialWeekLessons]

class Schedule:
    """Главный класс расписания."""

    def __init__(self, schedule: ScheduleMap) -> None:
        self._schedule = schedule

    # TODO: Новые индексы

    @property
    def schedule(self) -> ScheduleMap:
        """Возвращает сжатое расписание."""
        return self._schedule

    def lessons(self, cl: str) -> PartialWeekLessons | None:
        """Возвращает сжатые уроки для класса."""
        return self._schedule.get(cl)
