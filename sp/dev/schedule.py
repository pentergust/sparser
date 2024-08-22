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

from typing import Iterable, Iterator, NamedTuple

# Базовые хранилища данных
# ========================

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

    Расписанеи уроков привязывается к конкретному клссу и дню недели.
    Представляет осбой список уроков, хранящийся в формате LessonsMin.
    При получении урока автоматически будет дополнять его до Lesson.

    Реализованы методы для добавления добалвения уроков, итерации
    и получение/установка уроков по индексу.

    :param cl: Для какого класса представлено расписание.
    :type cl: str
    :param weekday: Для какого дня неедли предсталвено расписание (0-5).
    :type weekday: int
    :param lessons: Представленный список уроков.
    :type lessons: list[LessonMini] | None
    """

    def __init__(
        self,
        cl: str,
        weekday: int,
        lessons: list[LessonMini] | None = None
    ):
        self._lessons: list[LessonMini | None] = lessons or []
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

        Вернёт информацю об уроке в любом случае.
        К примеру если урока по данному индексу нет, то вернут экземпляр
        Lesson с описание класс, дня недели и заданного индекса.

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
        Все не входящие в LessonMini ключи при этом будут отброшены.

        :param lesson: Урок, которые необходимо добавить в конец.
        :type lesson: Lesson | LessonMini
        """
        self._lessons.append(self._get_mini_lesson(lesson))

    def insert(self, lessons: Iterable[Lesson | LessonMini]) -> None:
        """Добавляет сразу несколько уроков в расписание.

        По очереди будет добавлять все уроки в конец списка.
        Все уроки автоматически будут ужаты до LessonsMini при помощи
        метода ``add()``.

        :param lessons: Итератор уроков для добавления в список.
        :type lessons: Iterable[Lesson | LessonMini]
        """
        for lesson in lessons:
            self.add(lesson)

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

    def __repr__(self) -> str:
        """Что из себя представляет класс."""
        return f"{self.__class__.__name__}({self._lessons.__repr__()})"

    def __len__(self) -> int:
        """Возаращет количество урокрв на сегодня."""
        return len(self._lessons)

    def __iter__(self) -> Iterator[Lesson]:
        """Поочерёдно получает каждый элемент расписания.

        :returns: Полная информаци об уроке.
        :rtype: Lesson
        """
        for i, mini_lesson in enumerate(self._lessons):
            yield self._get_lesson(i, mini_lesson)

    def __contains__(self, lesson: Lesson | LessonMini) -> bool:
        """Проверяет что некоторый урок есть в расписании на сегодня.

        Обратите внимаени что проверка происходит только по тем ключам,
        которые находятся в класс LessonMini.

        :returns: Находится ли переданный урок в расписании.
        :rtype: bool
        """
        return self._get_mini_lesson(lesson) in self._lessons


    # Магическая индексация
    # =====================

    def __getitem__(self, index: int) -> Lesson:
        """Получает элемент по индексу.

        Синтаксический сахар для метода ``get()``.

        :param index: Порядковый номер урока для получения.
        :type index: int
        :returns: Полная информация об уроке.
        :rtype: Lesson
        """
        return self.get(index)

    def __setitem__(self, index: int, lesson: Lesson | LessonMini) -> None:
        """Устанавливает урок по индексу в расписании.

        Также автоматически добавить все недостающие уроки до.
        Обратите внимаени, все ключи не входящие в LessonMini будут
        отброшены.

        :param index: Порядковый номер урока для добавления.
        :type index: int
        :param lesson: Информация об уроке для добавления в расписание.
        :type lesson: Lesson | LessonMini
        """
        if not isinstance(lesson, (Lesson, LessonMini)):
            raise ValueError("Can only add Lesson or LessonMini instance")
        self.set(index, lesson)


# Расипсние уроков на неделю
# ==========================

class WeekLessons:
    """Расписанеи уроков на неделю для конкретного класса.

    Позвоялет просматривать и управлять расписаним уроков на неделю
    для укзаанного класса.
    Данные будет сохраняться в сжатом формате и когда нужно будут
    разжиматься до полноценного расписания уроков на день.

    :param cl: Для какого класса составлено расписание на неделю.
    :type cl: str
    :param days: Напрямую заданное расписание уроков.
    :type days: list[DayLessons] | None
    """

    def __init__(self, cl: str, days: list[DayLessons] | None = None):
        self.cl = cl
        self._days = self._to_days(days)


    def _to_days(
        self,
        days: list[DayLessons] | None
    ) -> list[list[LessonMini] | None]:
        if days is None:
            return [None, None, None, None, None, None]
        day_lessons = []
        for day in days:
            if day is None:
                day_lessons.append(None)
            else:
                day_lessons.append(day._lessons)
        # Это константы дней недели, они никогда не будут меняться
        if len(day_lessons) < 6: # noqa: PLR2004
            for _ in range(6-len(day_lessons)):
                day_lessons.append(None)
        return day_lessons


    # Упрвление уроками на день
    # =========================

    def get(self, day: int) -> DayLessons:
        """Получает расписание уроков в определённыый день недели.

        :param day: Для какого дня получить расписания (0-5).
        :type day: int
        :raises IndexError: Если укажете индекс вне дня недели.
        :return: Расписание уроков на день.
        :rtype: DayLessons
        """
        # Это константы дней недели, они никогда не будут меняться
        if day > 5 or day < 0: # noqa: PLR2004
            raise IndexError("Day must be in range from 0 to 5")
        return DayLessons(cl=self.cl, weekday=day, lessons=self._days[day])

    def set(self, day: int, lessons: DayLessons) -> None:
        """Устанавливает уроки на день для конкреьного дня.

        :param day: Для какого дня установить расписания (0-5).
        :type day: int
        :param lessons: Расписание уроков на день.
        :type lessons: DayLessons
        """
        self._days[day] = lessons._lessons


    # Магические методы
    # =================

     # Магические методы
    # =================

    def __repr__(self) -> str:
        """Что из себя представляет класс."""
        return f"{self.__class__.__name__}({self._days.__repr__()})"

    def __len__(self) -> int:
        """Возвращет количество дней недели."""
        return len(self._days)

    def __iter__(self) -> Iterator[DayLessons]:
        """Поочерёдно возвращет расписание уроков для каждого дня.

        :yield: Расписание уроков на определённый день.
        :rtype: Iterator[DayLessons]
        """
        for i, day_lessons in enumerate(self._days):
            yield DayLessons(cl=self.cl, weekday=i, lessons=day_lessons)


    # Магическая индексация
    # =====================

    def __getitem__(self, index: int) -> DayLessons:
        """Получает расписание уроков на день.

        :param index: Для какого дня недели (0-5).
        :type index: int
        :return: Расписание уроков на день.
        :rtype: DayLessons
        """
        return self.get(index)

    def __setitem__(self, index: int, lessons: DayLessons) -> None:
        """Устанавливает расипсание в определённый день.

        Обратите внимаение, что класс в DayLessons будет проигнорирован.

        :param index: В какой день недели установить расписание. (0-5)
        :type index: int
        :param lessons: Расписание уроков на день.
        :type lessons: DayLessons
        :raises ValueError: Если вместо расписания передали нечто иное.
        """
        if not isinstance(lessons, DayLessons):
            raise ValueError("Can only set DayLessons")
        self.set(index, lessons)
