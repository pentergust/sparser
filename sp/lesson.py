"""Представление Урока."""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class Lesson:
    """Исчерпывающая информация об уроке."""

    cl: str
    """Для какого класса проводится."""

    name: str | None
    """Название урока.

    Может быть пустым, тогда засчитывается как отсутствие урока.
    """

    cabinets: Sequence[str]
    """В каких кабинетах проводится.

    Будет указано несколько, если класс разделяется на группы.
    """

    day: int
    """В какой день недели проводится. От 0 до 5."""

    order: int
    """Порядковые номер урока в дне."""


@dataclass(slots=True, frozen=True)
class DayLesson:
    """Урок на день.

    Содержит не полную информацию об уроке, без указания дня.
    """

    cl: str
    """Для какого класса проводится."""

    name: str | None
    """Название урока.

    Может быть пустым, тогда засчитывается как отсутствие урока.
    """

    cabinets: Sequence[str]
    """В каких кабинетах проводится.

    Будет указано несколько, если класс разделяется на группы.
    """

    def to_lesson(self, day: int, order: int) -> Lesson:
        """Дополняет информацию до полноценного урока."""
        return Lesson(self.cl, self.name, self.cabinets, day, order)


@dataclass(slots=True, frozen=True)
class PartialLesson:
    """Частичная информация об уроке.

    Содержит не только необходимую информацию об уроке.
    """

    name: str | None
    """Название урока.

    Может быть пустым, тогда засчитывается как отсутствие урока.
    """

    cabinets: Sequence[str]
    """В каких кабинетах проводится.

    Будет указано несколько, если класс разделяется на группы.
    """

    def to_lesson(self, cl: str, day: int, order: int) -> Lesson:
        """Дополняет информацию до полноценного урока."""
        return Lesson(cl, self.name, self.cabinets, day, order)


# Lessons -> DayLessons -> PartialLessons
AnyLesson = Lesson | DayLesson | PartialLesson
PartialWeekLessons = list[list[PartialLesson | None]]
ScheduleMap = Mapping[str, PartialWeekLessons]


# Контейнеры для уроков
# =====================


class LessonIterator(Protocol):
    def iter_lessons(self) -> Iterator[Lesson | None]: ...


class PartialSchedule:
    """Представляет сжатое расписание."""

    def __init__(self, day: int | None = None, cl: str | None = None) -> None:
        self._day = day
        self._cl = cl

    def pack(self, lesson: AnyLesson) -> DayLesson | PartialLesson:
        """Запаковывает урок для расписания.

        - Partial -> Partial.
        - Day -> Partial. Если совпадает класс.
        - Lesson -> Day / Partial.
        """
        if isinstance(lesson, PartialLesson):
            return lesson

        if self._cl is not None and lesson.cl == self._cl:
            return PartialLesson(lesson.name, lesson.cabinets)
        return DayLesson(lesson.cl, lesson.name, lesson.cabinets)

    def unpack(
        self,
        lesson: PartialLesson | DayLesson,
        order: int,
        day: int | None = None,
    ) -> Lesson:
        """Дополняет информацию до полноценного урока."""
        day = day or self._day
        if day is None:
            raise ValueError("You need to specify day to unpack lesson")

        if isinstance(lesson, PartialLesson):
            if self._cl is None:
                raise ValueError("Class is bot specified")
            return lesson.to_lesson(self._cl, day, order)
        return lesson.to_lesson(day, order)


class DayLessons(PartialSchedule):
    """Уроки на день.

    Хранит данные в сжатом виде.
    Автоматически подставляет день недели и порядок урока.
    Если указать класс, будет подставлять и его.
    """

    def __init__(
        self,
        lessons: Sequence[DayLesson | PartialLesson | None],
        day: int,
        cl: str | None = None,
    ) -> None:
        super().__init__(day, cl)
        self.lessons = lessons or []

    def lesson(self, order: int) -> Lesson | None:
        """Возвращает полный урок по индексу."""
        if order > len(self.lessons):
            return None
        dl = self.lessons[order]
        if dl is None:
            return None

        return self.unpack(dl, order)

    def iter_lessons(self) -> Iterator[Lesson | None]:
        """Проходится по каждому уроку."""
        for i, lesson in enumerate(self.lessons):
            if lesson is None:
                yield None
                continue
            yield self.unpack(lesson, i)


class WeekLessons(PartialSchedule):
    """Уроки на неделю.

    Хранит данные в упрощённом виде.
    Автоматически подставляет день недели и порядок урока.
    Если указать класс, будет подставлять и его.
    """

    def __init__(
        self,
        lessons: Sequence[Sequence[DayLesson | PartialLesson | None]],
        cl: str | None = None,
    ) -> None:
        super().__init__(cl=cl)
        self.lessons = lessons

    def lesson(self, day: int, order: int) -> Lesson | None:
        """Возвращает полный урок по индексу."""
        dl = self.lessons[day][order]
        if dl is None:
            return None

        return self.unpack(dl, order, day)

    def day(self, day: int) -> DayLessons:
        """Возвращает уроки на день."""
        return DayLessons(self.lessons[day], day, self._cl)

    def iter_lessons(self) -> Iterator[Lesson | None]:
        """Проходится по каждому уроку."""
        for day, day_lessons in enumerate(self.lessons):
            for order, lesson in enumerate(day_lessons):
                if lesson is None:
                    yield None
                    continue
                yield self.unpack(lesson, order, day)

    def iter_days(self) -> Iterator[DayLessons]:
        """Возвращает все дни в расписании."""
        for day, lessons in enumerate(self.lessons):
            yield DayLessons(lessons, day, self._cl)
