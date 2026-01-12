"""расписание уроков."""

from collections.abc import Mapping

from sp.lesson import DayLessons, PartialLesson, WeekLessons

PartialWeekLessons = list[list[PartialLesson | None]]
ScheduleMap = Mapping[str, PartialWeekLessons]


class Schedule:
    """Главный класс расписания."""

    def __init__(self, schedule: ScheduleMap) -> None:
        self._schedule = schedule

    # TODO: Новые индексы
    # TODO: Фильтрация через намерения

    @property
    def schedule(self) -> ScheduleMap:
        """Возвращает сжатое расписание."""
        return self._schedule

    def lessons(self, cl: str) -> PartialWeekLessons | None:
        """Возвращает сжатые уроки для класса."""
        return self._schedule.get(cl)

    def week(self, cl: str) -> WeekLessons:
        """Возвращает расписание уроков на неделю для класса."""
        return WeekLessons(self._schedule[cl], cl)

    def day(self, cl: str, day: int) -> DayLessons:
        """Возвращает расписание уроков на день для класса."""
        return DayLessons(self._schedule[cl][day], day, cl)
