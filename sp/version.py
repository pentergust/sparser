"""Управление версиями.

Данный модуль позволяет взаимодействовать с версиями проекта.
Система версия используется для проверки совместимости.
К примеру для проверки наличия обновлений на сервере.
"""

from enum import IntEnum
from typing import NamedTuple, Self

import requests
import tomllib

UPDATES_URL = "https://codeberg.org/Salormoon/sparser/raw/branch/main/pyproject.toml"
"""Откуда получать сведения об обновлениях в репозитории."""

class VersionInfo(NamedTuple):
    """Описание версии продукта.

    Определённый этап развития проекта описывается версией.
    Состоит из строкового описания тега.
    Номера текущей сборки проекта.
    А также версии api, на котором работает проект.
    """

    version: str
    """Строковая версия проекта."""

    build: int
    """Текущий номер сборки. Используется для сравнения."""

    api_version: int
    """Поддерживаемая версия APi приложения."""

    @property
    def full(self) -> str:
        """Возвращает полную версию проекта.

        Returns:
            str: Полная версия продукта, включая номер сборки.
        """
        return f"{self.version} ({self.build})"

    # Методы сравнения версий по номеру сборки
    # ========================================

    def __lt__(self, other: Self | int) -> bool:
        """Проверяет что версия меньше требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при сравнении с номером сборки
        не производится проверка версию API.

        Args:
            other (Self | int): Экземпляр версии или номер сборки для
                сравнения с текущей версией.

        Returns:
            bool: Версия меньше требуемой.

        Raises:
            ValueError: Если передан неправильный тип для сравнения.
        """
        if isinstance(other, VersionInfo):
            return (
                self.build < other.build
                or self.api_version < other.api_version
            )
        elif isinstance(other, int):
            return self.build < other
        else:
            raise ValueError("Version must be VersionInfo or integer to check")

    def __le__(self, other: Self | int) -> bool:
        """Проверяет что версия меньше требуемой или соответствует.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при сравнении с номером сборки
        не производится проверка версию API.

        Args:
            other (Self | int): Экземпляр версии или номер сборки для
                сравнения с текущей версией.

        Returns:
            bool: Версия меньше или равна требуемой.

        Raises:
            ValueError: Если передан неправильный тип для сравнения.
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

    def __eq__(self, other: Self | int) -> bool:
        """Проверяет что версия соответствует требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при сравнении с номером сборки
        не производится проверка версию API.

        Args:
            other (Self | int): Экземпляр версии или номер сборки для
                сравнения с текущей версией.

        Returns:
            bool: Версия соответствует требуемой.

        Raises:
            ValueError: Если передан неправильный тип для сравнения.
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

    def __ne__(self, other: Self | int) -> bool:
        """Проверяет что версия НЕ соответствует требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при сравнении с номером сборки
        не производится проверка версию API.

        Args:
            other (Self | int): Экземпляр версии или номер сборки для
                сравнения с текущей версией.

        Returns:
            bool: Версия не соответствует требуемой.

        Raises:
            ValueError: Если передан неправильный тип для сравнения.
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

    def __gt__(self, other: Self) -> bool:
        """Проверяет что версия выше требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при сравнении с номером сборки
        не производится проверка версию API.

        Args:
            other (Self | int): Экземпляр версии или номер сборки для
                сравнения с текущей версией.

        Returns:
            bool: Версия выше требуемой.

        Raises:
            ValueError: Если передан неправильный тип для сравнения.
        """
        if isinstance(other, VersionInfo):
            return (
                self.build > other.build
                or self.api_version > other.api_version
            )
        elif isinstance(other, int):
            return self.build > other
        else:
            raise ValueError("Version must be VersionInfo or integer to check")

    def __ge__(self, other: Self) -> bool:
        """Проверяет что версия выше или равна требуемой.

        Можно сравнивать с другим экземпляром, а также напрямую с
        номером сборки.
        Обратите внимание что при сравнении с номером сборки
        не производится проверка версию API.

        Args:
            other (Self | int): Экземпляр версии или номер сборки для
                сравнения с текущей версией.

        Returns:
            bool: Версия выше или равна требуемой.

        Raises:
            ValueError: Если передан неправильный тип для сравнения.
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

PROJECT_VERSION = VersionInfo(
    version="v6.3",
    build=244,
    api_version=6
)
"""Текущая версия проекта.

По совместительству это общая версия всех внутренних компонентов.
Включая класс текстового представления.
"""


# Вспомогательные функции
# =======================

class VersionOrd(IntEnum):
    """Статус сравнения нескольких версий.

    Может быть меньше данного, аналогичен ему или больше.
    Используется при сравнении нескольких версий чтобы отобразить
    разницу между версиями.
    """

    LT = 0
    EQ = 1
    GT = 2

class VersionStatus(NamedTuple):
    """Сведения о сравнении нескольких версий.

    Включает в себя результат сравнения.
    Числовую разницу между номером сборки и версией APi проекта.
    А также хранит версию с сервера, с которой производилось сравнение.
    """

    status: VersionOrd
    build_diff: int
    api_diff: int
    git_ver: VersionInfo


def check_updates(cur_ver: VersionInfo, dest_url: str) -> VersionStatus:
    """Проверяет наличие обновлений в удалённом сервере.

    Для начала подгружает TOML файл из указанной ссылки.
    Предполагается что информации об актуальной версии находится по
    ключу: `tool.sp`.
    Если такого ключа в файле нет, выдаст исключение.

    Производит сравнение версии сервера с текущей версией проекта.
    В результате возвращает статус сравнения версий.
    Это используется для "ленивой" проверки обновлений на сервере.
    Чтобы после оповестить пользователей в сообщении статуса.

    Args:
        cur_ver (VersionInfo): Текущая версия приложения.
        dest_url (str): Ссылка на загрузку файла с актуальной версией.

    Returns:
        VersionStatus: Статус сравнения локальной и версии с сервера.

    Raises:
        KeyError: Если не удалось получить информацию о версии.
    """
    # Загружаем информацию из репозитория
    ver_file = tomllib.loads(requests.get(dest_url).text)
    git_ver = ver_file["tool"].get("sp")
    if git_ver is None:
        raise KeyError("File has no SPVersion metadata")
    ver = VersionInfo(
        version=git_ver['version'],
        build=git_ver['build'],
        api_version=git_ver["api_version"]
    )

    # Сравниваем версии
    if ver > cur_ver:
        return VersionStatus(
            status=VersionOrd.LT,
            build_diff=ver.build - cur_ver.build,
            api_diff=ver.api_version - cur_ver.api_version,
            git_ver=ver
        )
    elif ver < cur_ver:
        return VersionStatus(
            status=VersionOrd.GT,
            build_diff=cur_ver.build - ver.build ,
            api_diff=cur_ver.api_version - ver.api_version,
            git_ver=ver
        )

    else:
        return VersionStatus(VersionOrd.EQ, 0, 0, ver)
