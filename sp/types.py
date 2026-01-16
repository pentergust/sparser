"""Используемые типы в поставщике расписания."""

from collections.abc import Mapping, Sequence
from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel


class ProviderStatus(BaseModel):
    """Техническая информация о поставщике.

    Может быть использована чтобы отличать несколько поставщиков.
    """

    name: str
    version: str
    url: str


class ScheduleStatus(BaseModel):
    """Информация о расписании.

    Они же метаданные о расписании.
    Расписывают откуда было загружено расписание.
    Используется для проверки актуальности расписания.
    """

    source: str
    """Имя источника расписания. Гугл таблицы, файл, сайт или прочее."""

    url: str
    """Ссылка на источник, откуда было получено расписание."""

    hash: str
    """Уникальная строка расписания.

    Используется при проверки обновлений.
    """

    check_at: datetime
    """Время последней проверки актуальности расписания."""

    update_at: datetime
    """Время последнего загруженного обновления расписания из источника."""

    next_check: datetime
    """Когда будет следующая проверка актуальности расписания."""


class ScheduleMeta(BaseModel):
    """Необходимые метаданные для расписания.

    Минимальный набор параметров, который загружается при запуске.
    Обязательно стоит указать название и источник расписание.
    Остальные параметры заполняются автоматически поставщиком.
    """

    source: str
    url: str
    hash: str | None = None
    check_at: datetime | None = None
    update_at: datetime | None = None
    next_check: datetime | None = None


class Status(BaseModel):
    """Информация поставщика.

    Предоставляет технические подробности поставщика.
    Может быть использовано при использовании нескольких поставщиков.

    Предоставляет информацию о расписании.
    Используется для автоматической проверки обновлений.
    """

    provider: ProviderStatus
    schedule: ScheduleStatus


class LessonTime(BaseModel):
    """Время урока для расписания звонков."""

    start: time
    end: time


class TimeTable(BaseModel):
    """Общее расписание звонков."""

    default: Sequence[LessonTime]

    def index(self, now: time ) -> int | None:
        """Возвращает индекс текущий урока, основываясь на времени.

        Используется в функции сбора расписания на день.
        Чтобы указать на время текущего урока.
        """
        for i, lesson in enumerate(self.default):
            if now > lesson.start and now < lesson.end:
                return i

            if now < lesson.end:
                return i
        return None


class Lesson(BaseModel):
    """Описание урока."""

    name: str | None
    """Название урока. Может быть пустым если урок помечен как пропуск."""

    cabinets: list[str]
    """В каких кабинетах проводится.

    Может быть несколько, если класс делится на группы."""


# Дополнительные типы для расписания
DayLessons = Sequence[Lesson | None]
ClassLessons = Sequence[DayLessons]
ScheduleT = Mapping[str, ClassLessons]


class Schedule(BaseModel):
    """Полное расписание уроков."""

    schedule: ScheduleT


class ScheduleFilter(BaseModel):
    """Фильтры для получения расписания.

    Передаются при получении расписания.
    Если не передать фильтры, вернёт полное расписание.
    """

    days: Sequence[Literal[0, 1, 2, 3, 4, 5]] | None = None
    """Для каких дней недели.

    Если оставить пустым, вернёт расписание на всю неделю."""

    cl: Sequence[str] | None = None
    """Для каких классов.

    Если оставить пустым, вернёт расписание на для всех классов.
    """
