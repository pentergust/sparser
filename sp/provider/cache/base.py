from datetime import datetime
from typing import NamedTuple
from abc import ABC, abstractmethod

# from pathlib import Path
from sp.lesson import Schedule


class CacheMetadata(NamedTuple):
    index: int
    update: datetime
    hash: str


class BaseCacheStorage(ABC):

    @abstractmethod
    def get(self, index: int | None = None) -> Schedule:
        pass

    @abstractmethod
    def add(self, sc: Schedule) -> CacheMetadata:
        pass

    @abstractmethod
    def update(self, index: int, sc: Schedule) -> CacheMetadata:
        pass

    @abstractmethod
    def remove(self, index: int) -> None:
        pass

    @abstractmethod
    def list_cache(self) -> list[CacheMetadata]:
        pass


# class SingleCacheStorage(ABC):
#     @abstractmethod
#     def get(self) -> Schedule:
#         pass

#     @abstractmethod
#     def update(self, sc: Schedule) -> CacheMetadata:
#         pass

#     @abstractmethod
#     def remove(self) -> None:
#         pass

#     @abstractmethod
#     def list_cache(self) -> CacheMetadata:
#         pass


