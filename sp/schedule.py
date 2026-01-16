"""расписание уроков."""

from collections.abc import Iterator

from sp import lesson


class Schedule:
    """Главный класс расписания."""

    def __init__(self, schedule: lesson.ScheduleMap) -> None:
        self._schedule = schedule

    # TODO: Новые индексы
    # TODO: Фильтрация через намерения

    @property
    def schedule(self) -> lesson.ScheduleMap:
        """Возвращает сжатое расписание."""
        return self._schedule

    def week(self, cl: str) -> lesson.WeekLessons:
        """Возвращает расписание уроков на неделю для класса."""
        return lesson.WeekLessons(self._schedule[cl], cl)

    def day(self, cl: str, day: int) -> lesson.DayLessons:
        """Возвращает расписание уроков на день для класса."""
        return lesson.DayLessons(self._schedule[cl][day], day, cl)

    def iter_lessons(self) -> Iterator[lesson.Lesson | None]:
        """Возвращает каждый урок в расписании."""
        for cl, week in self._schedule.items():
            for day, day_lessons in enumerate(week):
                for order, partial_lesson in enumerate(day_lessons):
                    if partial_lesson is None:
                        yield None
                    else:
                        yield partial_lesson.to_lesson(cl, day, order)
