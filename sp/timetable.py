"""Расписание уроков.

Предоставляет компоненты для описания времени начала и конца уроков.
"""

from dataclasses import dataclass
from datetime import time


@dataclass(slots=True, frozen=True)
class LessonTime:
    """Время начала и конца урока."""

    start: time
    end: time


@dataclass(slots=True, frozen=True)
class IndexedLessonTime:
    """Время начала и конца урока с указанием номера урока."""

    start: time
    end: time
    index: int


class Timetable:
    """Расписание звонков."""

    def __init__(self, lessons: list[LessonTime]) -> None:
        self.lessons = lessons

    def current(self, now: time) -> IndexedLessonTime:
        """Возвращает текущий урок, основываясь на времени.

        Используется в функции сбора расписания на день.
        Чтобы указать на время текущего урока.
        """
        l_end_time = None
        for i, lesson in enumerate(self.lessons):
            if (
                l_end_time is not None
                and now >= l_end_time
                and now < lesson.start
            ):
                return IndexedLessonTime(l_end_time, lesson.start, i)

            if now >= lesson.start and now < lesson.end:
                return IndexedLessonTime(lesson.start, lesson.end, i)

            l_end_time = lesson.end

        # Лучше возвращать первый урок, чем вообще ничего не возвращать
        return IndexedLessonTime(self.lessons[0].start, self.lessons[0].end, 0)
