"""Управление версиями.

Данный модуль позволяет взаимодействовать с версиями проекта.
Система версия используется для проверки совместимости.
К примеру проверять наличие обновлений на сервере.
"""

from enum import IntEnum
from typing import NamedTuple

import requests
import tomllib

# Откуда получать сведения об обновлениях в репозитории
UPDATES_URL = (
    "https://codeberg.org/Salormoon/sparser/raw/branch/main/pyproject.toml"
)


class VersionInfo(NamedTuple):
    """Описание версии продукта.

    Определённый этап развития проекта описывается версией.
    Состоит из строкового описания тега.
    Номера текущей сборки проекта.
    А также версии api, на котором работает проект.
    """

    version: str
    build: int
    api_version: int

    @property
    def full(self) -> str:
        """Полная версия продукта, включая номер сборки."""
        return f"{self.version} ({self.build})"

    # Методы сравнения версий по номеру сборки
    # ========================================

    def __lt__(self, other: object) -> bool:
        """Проверяет что версия меньше требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при проверке напрямую с номером сборки
        не получится проверить версию API.
        """
        if isinstance(other, VersionInfo):
            return (
                self.build < other.build or self.api_version < other.api_version
            )
        elif isinstance(other, int):
            return self.build < other
        else:
            raise ValueError("Version must be VersionInfo or integer to check")

    def __le__(self, other: object) -> bool:
        """Проверяет что версия меньше требуемой или соответствует.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при проверке напрямую с номером сборки
        не получится проверить версию API.
        """
        if isinstance(other, VersionInfo):
            return (
                self.build <= other.build
                or self.api_version <= other.api_version
            )
        elif isinstance(other, int):
            return self.build <= other
        else:
            raise ValueError("Version must be VersionInfo or integer to check")

    def __eq__(self, other: object) -> bool:
        """Проверяет что версия соответствует требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при проверке напрямую с номером сборки
        не получится проверить версию API.
        """
        if isinstance(other, VersionInfo):
            return (
                self.build == other.build
                or self.api_version == other.api_version
            )
        elif isinstance(other, int):
            return self.build == other
        else:
            raise ValueError("Version must be VersionInfo or integer to check")

    def __ne__(self, other: object) -> bool:
        """Проверяет что версия НЕ соответствует требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при проверке напрямую с номером сборки
        не получится проверить версию API.
        """
        if isinstance(other, VersionInfo):
            return (
                self.build != other.build
                or self.api_version != other.api_version
            )
        elif isinstance(other, int):
            return self.build != other
        else:
            raise ValueError("Version must be VersionInfo or integer to check")

    def __gt__(self, other: object) -> bool:
        """Проверяет что версия больше требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при проверке напрямую с номером сборки
        не получится проверить версию API.
        """
        if isinstance(other, VersionInfo):
            return (
                self.build > other.build or self.api_version > other.api_version
            )
        elif isinstance(other, int):
            return self.build > other
        else:
            raise ValueError("Version must be VersionInfo or integer to check")

    def __ge__(self, other: object) -> bool:
        """Проверяет что версия больше требуемой или соответствует.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при проверке напрямую с номером сборки
        не получится проверить версию API.
        """
        if isinstance(other, VersionInfo):
            return (
                self.build >= other.build
                or self.api_version >= other.api_version
            )
        elif isinstance(other, int):
            return self.build >= other
        else:
            raise ValueError("Version must be VersionInfo or integer to check")


# Текущая версия проекта
# ======================

PROJECT_VERSION = VersionInfo(version="v6.4.3", build=252, api_version=6)


# Вспомогательные функции
# =======================


class VersionOrd(IntEnum):
    """Статус сравнения нескольких версий.

    Может быть меньше данного, аналогичен ему или больше.
    """

    LT = 0
    EQ = 1
    GT = 2


class VersionStatus(NamedTuple):
    """Сведения о сравнении нескольких версий."""

    status: VersionOrd
    build_diff: int
    api_diff: int
    git_ver: VersionInfo


def check_updates(cur_ver: VersionInfo, dest_url: str) -> VersionStatus:
    """Проверяет наличие обновлений в удалённом сервере.

    Производит проверку с текущей версией проекта.
    В результате возвращает статус сравнения версий.
    """
    # Загружаем информацию из репозитория
    ver_file = tomllib.loads(requests.get(dest_url).text)
    git_ver = ver_file["tool"].get("sp")
    if git_ver is None:
        raise KeyError("File has no SPVersion metadata")
    ver = VersionInfo(
        version=git_ver["version"],
        build=git_ver["build"],
        api_version=git_ver["api_version"],
    )

    # Сравниваем версии
    if ver > cur_ver:
        return VersionStatus(
            status=VersionOrd.LT,
            build_diff=ver.build - cur_ver.build,
            api_diff=ver.api_version - cur_ver.api_version,
            git_ver=ver,
        )
    elif ver < cur_ver:
        return VersionStatus(
            status=VersionOrd.GT,
            build_diff=cur_ver.build - ver.build,
            api_diff=cur_ver.api_version - ver.api_version,
            git_ver=ver,
        )

    else:
        return VersionStatus(VersionOrd.EQ, 0, 0, ver)
