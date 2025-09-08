"""Типы расписания."""

from datetime import datetime, time

from pydantic import BaseModel


class Status(BaseModel):
    """Статус расписания."""

    parsed: datetime
    hash: str
    url: str


class Lesson(BaseModel):
    """Урок в расписании."""

    lesson: str
    cabinet: str


class LessonTime(BaseModel):
    """Время урока."""

    start: tuple[int, int]
    end: tuple[int, int]


DayLessons = list[Lesson]
WeekLessons = list[DayLessons]
Schedule = dict[str, WeekLessons]
TimeTable = list[LessonTime]
