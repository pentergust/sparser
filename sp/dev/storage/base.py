from abc import ABC, abstractmethod
from typing import NamedTuple


class ScheduleStorageInfo(NamedTuple):
    last_update: int
    next_update: int
    version: str
    api_version: int


class BaseScheduleStorage(ABC):

    @abstractmethod
    def get_info(self) -> ScheduleStorageInfo:
        pass

    def load(self) -> Вср