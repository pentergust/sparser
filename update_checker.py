"""Скрипт проверки обновлений.

Позволят проверять наличие обновлений в репозитории, относительно
текущей версии проекта.
"""

import tomllib
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import aiohttp

UPDATES_URL = (
    "https://codeberg.org/Salormoon/sparser/raw/branch/main/pyproject.toml"
)


@dataclass(slots=True, frozen=True)
class Version:
    """Описание версии проекта."""

    version: str
    build: int
    api_version: int

    @property
    def full(self) -> str:
        """Полная версия, включая номер сборки."""
        return f"{self.version} ({self.build})"

    def __lt__(self, other: "Version | int") -> bool:
        """Версия меньше требуемой."""
        if isinstance(other, Version):
            return (
                self.build < other.build or self.api_version < other.api_version
            )
        return self.build < other

    def __le__(self, other: "Version | int") -> bool:
        """Проверяет что версия меньше требуемой или соответствует."""
        if isinstance(other, Version):
            return (
                self.build <= other.build
                or self.api_version <= other.api_version
            )
        return self.build <= other

    def __gt__(self, other: "Version | int") -> bool:
        """Проверяет что версия больше требуемой."""
        if isinstance(other, Version):
            return (
                self.build > other.build or self.api_version > other.api_version
            )
        return self.build > other

    def __ge__(self, other: "Version | int") -> bool:
        """Проверяет что версия больше требуемой или соответствует."""
        if isinstance(other, Version):
            return (
                self.build >= other.build
                or self.api_version >= other.api_version
            )
        return self.build >= other


def local_version(path: Path) -> Version:
    """Загружает информацию о версии из pyproject файла."""
    with path.open() as f:
        data: dict[str, Any] | None = tomllib.loads(f.read())["tool"].get("sp")

    if data is None:
        raise ValueError("Version not found in pyproject file")

    return Version(data["version"], data["build"], data["api_version"])


async def remote_version(url: str) -> Version:
    """Загружает версию из удалённого источника."""
    async with aiohttp.ClientSession() as session:
        res = await session.get(url)
        res.raise_for_status()
        ver_file = tomllib.loads(await res.text())

    git_ver = ver_file["tool"].get("sp")
    if git_ver is None:
        raise KeyError("File has no SPVersion metadata")
    return Version(
        version=git_ver["version"],
        build=git_ver["build"],
        api_version=git_ver["api_version"],
    )


class VersionOrd(IntEnum):
    """Статус сравнения нескольких версий.

    Может быть меньше данного, аналогичен ему или больше.
    """

    LT = 0
    EQ = 1
    GT = 2


@dataclass(slots=True, frozen=True)
class VersionStatus:
    """Сведения о сравнении нескольких версий."""

    status: VersionOrd
    build_diff: int
    api_diff: int
    git_ver: Version


async def check_updates(
    path: Path = Path("./pyproject.toml"), url: str = UPDATES_URL
) -> VersionStatus:
    """Проверяет наличие обновлений в удалённом сервере.

    Производит проверку с текущей версией проекта.
    В результате возвращает статус сравнения версий.
    """
    cur_ver = local_version(path)
    ver = await remote_version(url)

    if ver > cur_ver:
        return VersionStatus(
            status=VersionOrd.LT,
            build_diff=ver.build - cur_ver.build,
            api_diff=ver.api_version - cur_ver.api_version,
            git_ver=ver,
        )
    if ver < cur_ver:
        return VersionStatus(
            status=VersionOrd.GT,
            build_diff=cur_ver.build - ver.build,
            api_diff=cur_ver.api_version - ver.api_version,
            git_ver=ver,
        )

    return VersionStatus(VersionOrd.EQ, 0, 0, ver)
