"""Используемые типы в поставщике."""

from collections.abc import Mapping, MutableSequence, Sequence
from datetime import datetime, time

from pydantic import BaseModel


class ProviderStatus(BaseModel):
    """Информация о поставщике."""

    name: str
    version: str
    url: str

class ScheduleStatus(BaseModel):
    """Информация о расписании."""

    source: str
    url: str
    hash: str
    check_at: datetime
    update_at: datetime
    next_check: datetime


class ScheduleMeta(BaseModel):
    """Необходимые метаданные для расписания."""

    source: str
    url: str
    hash: str | None = None
    check_at: datetime | None = None
    update_at: datetime | None = None
    next_check: datetime | None = None


class Status(BaseModel):
    """Информация о расписании и поставщике."""

    provider: ProviderStatus
    schedule: ScheduleStatus

class LessonTime(BaseModel):
    """Время для уроков."""

    start: time
    end: time

TimeTable = Sequence[LessonTime]

class Lesson(BaseModel):
    """Информация об уроке."""

    name: str | None
    cabinets: list[str]

DayLessons = MutableSequence[Lesson | None]
ClassLessons = Sequence[DayLessons]
ScheduleT = Mapping[str, ClassLessons]

class Schedule(BaseModel):
    """Расписание уроков."""

    schedule: ScheduleT

class ScheduleFilter(BaseModel):
    """Фильтры для получения расписания."""

    days: Sequence[int] | None = None
    cl: Sequence[str] | None = None
