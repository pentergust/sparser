"""Расписание уроков.

Предосталвяет общий формат расписания для всех поставщиков.
Все поставщики будут приводить свой формат расписания к данному.
Это необходимо для боелее удобной работы с расписанием.

Общий формат расписания включает в себя:
- Урок: Наименьшая еденица расписания.
- День: Несколько уроков в рамках одного дня.
- Недея: Несколько дней в рамках одной учебной недели.
- Расписание: Расписание одной учебной недели для нескольих классов.
"""

from enum import IntEnum
from typing import NamedTuple

# Базовые хранилища данных
# ========================

class ScheduleObject(IntEnum):
    """Описывает все доступные элементы расписания.

    - ``LESSON``: Название урока в расписании.
    - ``CLASS``: Для какого класса проводится урок.
    - ``LOCATION``: В каком кабинете проводится урок.
    - ``TEACHER``: Какое преподаватель проводит урок.
    - ``WEEKDAY``: В какой день недели проводится урок.
    - ``METADATA``: Дополнительная информация о занятии.
    - ``INDEX``: Положение урока относительно дня.

    Значение перечисления расставлены в соостветсвии с индексами
    урока.
    При упаковке намерения вторая цифра означает ключ.
    """

    LESSON = 0   # name
    CLASS = 1    # cl
    LOCATION = 2 # location
    TEACHER = 3  # teacher
    WEEKDAY = 4  # weekday
    METADATA = 5 # metadata
    INDEX = 6 # index

class Lesson(NamedTuple):
    """Описывает один конкретный урок в расписании.

    Урок - наименьшая еденица расписания, имеющая ценность.
    Данный кортеж наиболее полно представляет каждый урок.
    Поскольку урок явялется универсаьн для нескольких расписаний,
    некоторые его поля могут быть не заполнены.

    :param name: Название урока.
    :type name: str | None
    :param cl: Для какого класа проводится урок.
    :type cl: str | None
    :param location: В каком кабинете проводится урок.
    :type location: str | None
    :param teacher: Какое преподаватель проводит урок.
    :type teacher: str | None
    :param weekday: В какой день недели проводится урок.
    :type weekday: int | None
    :param metadata: Дополнительная информация об уроке.
    :type metadata: str | None
    :param index: Положение урока относительно дня.
    :type index: int | None
    """

    name: str | None = None
    cl: str | None = None
    location: str | None = None
    teacher: str | None = None
    weekday: int | None = None
    metadata: str | None = None
    index: int | None = None

class LessonMini(NamedTuple):
    """Формат данных для хранения информации об уроке.

    В то время как класс Lesson предоставляет как можно более полную
    информацию о данном уроке, класс LesonMini используется для хранения
    уникальной информации и опусает повторяющиеся значения.

    При получении данных из хранилища, они автоматически будут
    дополнены до полноо класса Lesson.

    :param name: Имя урока.
    :type name: str | None
    :param location: Где проводится урок.
    :type location: str | None
    :param teacher: Преподаватель, проводящий урок.
    :type teacher: str | None
    :param metadata: Дополнительная информация об уроке.
    :type metadata: str | None
    """

    name: str | None = None
    location: str | None = None
    teacher: str | None = None
    metadata: str | None = None


# Расписание уроков на день
# =========================

class DayLessons:
    """Расписание уроков на день.

    Описывает расписание уроков для конккретного класса на день.
    """

    def __init__(
        self,
        cl: str,
        weekday: int,
        lessons: list[LessonMini] | None = None
    ):
        self._lessons: list[LessonMini] = lessons or []
        self.cl = cl
        self.weekday = weekday


    # Распаковка и запаковка уроков
    # =============================

    def _get_mini_lesson(self, lesson: Lesson | LessonMini) -> LessonMini:
        if isinstance(lesson, LessonMini):
            return lesson
        return LessonMini(
            name=lesson.name,
            location=lesson.location,
            teacher=lesson.teacher,
            metadata=lesson.metadata
        )

    def _get_lesson(
        self,
        index: int,
        lesson: Lesson | LessonMini | None = None
    ) -> Lesson:
        if lesson is None:
            return Lesson(
                cl=self.cl,
                weekday=self.weekday,
                index=index
            )
        return Lesson(
            name=lesson.name,
            cl=self.cl,
            location=lesson.location,
            teacher=lesson.teacher,
            weekday=self.weekday,
            metadata=lesson.metadata,
            index=index
        )


    # Упрвление списком уроков
    # ========================

    def get(self, index: int) -> Lesson:
        """Получает урок по индексу.

        Если урока по данному индексу нет, то вернёт пустую информацию
        об уроке.

        :param index: По какому индексу нужно получить урок.
        :type index: int
        :returns: Полная информация об уроке.
        :rtype: Lesosn
        """
        if index > len(self._lessons):
            return self._get_lesson(index)
        return self._get_lesson(index, self._lessons[index])

    def add(self, lesson: Lesson | LessonMini) -> None:
        """Добавляет урок в конец списка.

        Полная информация будет автоматически сжата до LessonMini.
        Все ненужные ключи при этом будут отброшены.

        :param lesson: Урок, которые необходимо добавить в конец.
        :type lesson: Lesson | LessonMini
        """
        self._lessons.append(self._get_mini_lesson(lesson))

    def set(self, index: int, lesson: Lesson | LessonMini) -> None:
        """Устанавливает необходимый урок по индексу.

        Также автоматически дополняет расписание пустыми урокам.
        Обратите внимаение что при передаче класса Lesosn часть
        параметров, не входящая в LessonMini будет отброшена.

        :param index: В какой позиции необходимо установить урок.
        :type index: int
        """
        if index < len(self._lessons):
            self._lessons[index] = self._get_mini_lesson(lesson)
        else:
            index_dist = index - len(self._lessons)
            if index_dist > 0:
                for i in range(index_dist):
                    self._lessons.append(None)
                self.add(lesson)


    # Магические методы
    # =================

    def __iter__(self) -> Lesson:
        """Поочерёдно получает каждый элемент расписания.

        :returns: Полная информаци об уроке.
        :rtype: Lesson
        """
        for i, mini_lesson in enumerate(self._lessons):
            yield self._get_lesson(i, mini_lesson)
