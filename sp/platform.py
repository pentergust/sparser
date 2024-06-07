"""Класс описания платформы.

Проводником между пользователем и расписанием является некотороая
платформа-посредник.
Это может быть как Telegram бот, web-приложение или просто консоль.
Данный модуль помогает настроить платформу, коотрая будет иметь
доступ к расписанию.
"""

from typing import Optional

from sp.exceptions import ViewNotCompatible, ViewNotSelected
from sp.messages import SPMessages
from sp.users.storage import FileUserStorage, User
from sp.users.intents import UserIntentsStorage

from loguru import logger


class Platform():
    """Описание платформфы, на котороы було запущено расписание.

    Автоматически настраивает хранилище пользователей и намерений.

    :param pid: Уникальный id платформы.
    :type pid: int
    :param name: Название платформы.
    :type name: str
    :param api_version: Поддверживаемая версия API расписания
    :type api_verion: int
    """

    def __init__(self, pid: int, name: str, version: str, api_version: int):
        self.pid = pid
        self.name = name
        self.version = version
        self.api_version = api_version
        self.users = FileUserStorage(f"sp_data/users/{pid}.json")
        self._view = None


    # Работа с классом просмотра
    # ==========================

    def _check_api_version(self, api_verion: int) -> bool:
        if api_verion < self.api_version:
            raise ViewNotCompatible("Platform API is higher than view API")
        elif api_verion == self.api_version:
            return True
        else:
            logger.warning("Platform API is lower than view")
            logger.warning("Some functions may not work correctly.")
            return False

    @property
    def view(self) -> SPMessages | None:
        if self._view is not None:
            return view
        else:
            raise ViewNotSelected("Yot must set View before use it")

    @view.setter
    def view(self, view: SPMessages) -> None:
        if not isinstance(view, SPMessages):
            return
        self._check_api_version(view.API_VERSION)
        self._view = view


    # Получение хранилищ пользователей
    # ================================

    def get_user(self, uid: str) -> User:
        return User(self.users, uid)

    def get_intents(self, uid: int) -> UserIntentsStorage:
        return UserIntentsStorage(f"sp_data/users/{self.pid}.db", uid)


    # Абстрактное представление представления
    # =======================================

    def get_default_intent(self, intent: Optional[Intent]) -> Intent:
        return self.view.sc.construct_intent(
            cl=self.user.data.cl
        ) if intent is None else intent