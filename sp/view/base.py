"""Базовый класс представления.

Как можно представить расписание в различных форматах.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sp.counter import CounterTarget
from sp.db import CountedUsers, User
from sp.intents import Intent
from sp.parser import UpdateData
from sp.version import VersionInfo

_VR = TypeVar("_VR")


class BaseView(Generic[_VR], ABC):
    """Базовый класс представления."""

    @abstractmethod
    def send_status(
        self,
        storage_users: CountedUsers,
        user: User,
        platform_version: VersionInfo,
    ) -> _VR:
        """Возвращает информацию о платформе."""
        pass

    @abstractmethod
    def get_lessons(self, intent: Intent) -> _VR:
        """Собирает сообщение с расписанием уроков."""
        pass

    @abstractmethod
    def today_lessons(self, intent: Intent) -> _VR:
        """Расписание уроков на сегодня/завтра."""
        pass

    @abstractmethod
    def search(
        self, target: str, intent: Intent, cabinets: bool = False
    ) -> _VR:
        """Поиск по имена урока/кабинета в расписании."""
        pass

    @abstractmethod
    def get_update(self, update: UpdateData, hide_cl: str | None = None) -> _VR:
        """Собирает сообщение со списком изменений в расписании."""
        pass

    @abstractmethod
    async def check_updates(self, user: User) -> _VR | None:
        """Проверяет обновления в расписании для пользователя."""
        pass

    @abstractmethod
    def counter(
        self,
        groups: dict[int, dict[str, dict]],
        target: CounterTarget | None = None,
        days_counter: bool = False,
    ) -> _VR:
        """Возвращает результат работы счётчика."""
        pass
