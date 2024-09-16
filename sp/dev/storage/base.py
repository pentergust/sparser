from abc import ABC, abstractmethod
from typing import NamedTuple

from sp.dev.schedule import Schedule


class StorageMetadata(NamedTuple):
    last_update: int
    api_verion: int


class BaseScheduleStorage(ABC):

    # Работа с данными в хранилище
    # ============================

    @abstractmethod
    def load_from(self) -> None:
        pass

    @abstractmethod
    def write_to(self) -> None:
        pass

    # Работа с расписанием в хранилище
    # ================================

    @abstractmethod
    def get(self) -> Schedule:
        pass

    @abstractmethod
    def set(self, sc: Schedule) -> None:
        pass
