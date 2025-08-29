"""Базовый класс представления.

Как можно представить расписание в различных форматах.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sp.counter import CounterTarget
from sp.db import User
from sp.intents import Intent
from sp.parser import UpdateData
from sp.version import VersionInfo

_VR = TypeVar("_VR")


class View(Generic[_VR], ABC):
    """Базовый класс представления.

    От него наследуются все классы представления.
    Позволяет предоставлять расписание в некотором формате.
    """

    # TODO: Отдельный метод для предоставления информации о пользователе
    @abstractmethod
    async def user(self, user: User) -> _VR:
        """Информация о пользователе."""

    @abstractmethod
    async def status(self, platform_version: VersionInfo) -> _VR:
        """Информация о платформе."""

    @abstractmethod
    def lessons(self, intent: Intent) -> _VR:
        """Расписание уроков с использованием фильтров."""

    @abstractmethod
    def today_lessons(self, intent: Intent) -> _VR:
        """Расписание уроков на сегодня/завтра с фильтрацией."""

    # TODO: Добавить типизированный параметр поиска в search.
    @abstractmethod
    def search(
        self, target: str, intent: Intent, cabinets: bool = False
    ) -> _VR:
        """Поиск по имена урока/кабинета в расписании."""

    @abstractmethod
    # TODO: Более общий аргумент вместо hide_cl
    def update(self, update: UpdateData, hide_cl: str | None = None) -> _VR:
        """Возвращает сообщение со списком изменений в расписании."""

    # TODO: Переместить метод в класс пользователя?
    @abstractmethod
    async def check_updates(self, user: User) -> _VR | None:
        """Проверяет обновления в расписании для пользователя."""

    # TODO: Исправить типизацию групп
    # TODO: Более общий аргумент вместо days_counter
    @abstractmethod
    def counter(
        self,
        groups: dict[int, dict[str, dict]],
        target: CounterTarget | None = None,
        days_counter: bool = False,
    ) -> _VR:
        """Возвращает результат работы счётчика."""
