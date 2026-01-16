"""Индексы уроков/кабинетов."""

from abc import ABC, abstractmethod
from collections.abc import Iterable, KeysView, Mapping

from sp.lesson import DayLesson, DayLessons, Lesson, WeekLessons

# TODO: Объединить с lesson
_IndexWeek = list[list[DayLesson | None]]
_Index = Mapping[str, _IndexWeek]


class ScheduleIndex(ABC):
    """Индекс расписания.

    Позволяет хранить представление расписания в упрощённом формате.
    """

    def __init__(self, lessons: Iterable[Lesson | None]) -> None:
        self._index = self._build(lessons)

    @abstractmethod
    def _build(self, lessons: Iterable[Lesson | None]) -> _Index: ...

    # TODO: Фильтрацию при помощи намерений

    def keys(self) -> KeysView[str]:
        """Возвращает все значения индекса."""
        return self._index.keys()

    def get(self, key: str) -> _IndexWeek | None:
        """Возвращает сырое значение индекса по ключу."""
        return self._index.get(key)

    def week(self, key: str) -> WeekLessons:
        """Возвращает расписание на неделю по ключу."""
        return WeekLessons(self._index[key])

    def day(self, key: str, day: int) -> DayLessons:
        """Возвращает расписание на день по ключу."""
        return DayLessons(self._index[key][day], day)


class LessonIndex(ScheduleIndex):
    """Индекс предметов."""

    def _build(self, lessons: Iterable[Lesson | None]) -> _Index:
        res: _Index = {}
        for lesson in lessons:
            if lesson is None:
                continue

            key = str(lesson.name)

            if key not in res:
                res[key] = [[None for _ in range(8)] for _ in range(6)]

            res[key][lesson.day][lesson.order] = DayLesson(
                cl=lesson.cl, name=lesson.name, cabinets=lesson.cabinets
            )

        return res


class CabinetIndex(ScheduleIndex):
    """Индекс кабинетов."""

    def _build(self, lessons: Iterable[Lesson | None]) -> _Index:
        res: _Index = {}
        for lesson in lessons:
            if lesson is None:
                continue

            for key in map(str, lesson.cabinets):
                if key not in res:
                    res[key] = [[None for _ in range(8)] for _ in range(6)]

                res[key][lesson.day][lesson.order] = DayLesson(
                    cl=lesson.cl, name=lesson.name, cabinets=lesson.cabinets
                )

        return res
