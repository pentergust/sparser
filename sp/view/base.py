from abc import ABC, abstractmethod

from sp.schedule import Schedule
from sp.intents import Intent


class BaseChatView(ABC):
    @abstractmethod
    def status(self) -> str:
        pass

    # Работа с расписанием
    # ====================


    @abstractmethod
    def get_lessons(self, intent: Intent) -> str:
        pass

    @abstractmethod
    def get_today_lessons(self, intent: Intent) -> str:
        pass

    @abstractmethod
    def search(self, intent: Intent) -> str:
        pass


    # Работа со счётчиками
    # ====================

    @abstractmethod
    def get_oounter(self, groups, target) -> str:
        pass


    # Работа со списком обнолвений
    # ============================

    @abstractmethod
    def get_updates_list(self, groups, target) -> str:
        pass

    @abstractmethod
    def get_update(self, groups, target) -> str:
        pass
