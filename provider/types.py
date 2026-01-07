"""Используемые типы в поставщике."""

from collections.abc import Mapping, Sequence
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

    name: str
    cabinets: list[str]

DayLessons = Sequence[Lesson]
ClassLessons = Sequence[DayLessons]
Schedule = Mapping[str, ClassLessons]

class ScheduleFilter(BaseModel):
    """Фильтры для получения расписания."""

    days: Sequence[int] | None = None
    cl: Sequence[str] | None = None
