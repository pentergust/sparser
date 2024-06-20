from abc import ABC, abstractmethod

from sp.schedule import Schedule


class BaseProvider(ABC):
    @abstractmethod
    def get(self) -> Schedule | None:
        pass


class BaseParser(BaseProvider):
    @abstractmethod
    def cache_write(self, sc: Schedule) -> None:
        pass

    @abstractmethod
    def cache_load(self) -> Schedule | None:
        pass

    @abstractmethod
    def fetch(self) -> Schedule | None:
        pass

    @abstractmethod
    def get_or_update(self) -> Schedule | None:
        pass