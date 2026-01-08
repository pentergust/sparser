"""Поставщик расписания."""

import json
from datetime import UTC, datetime, time
from pathlib import Path

import aiohttp
import anyio
import toml
from loguru import logger

from provider import types

_TIMETABLE = (
    types.LessonTime(start=time(8, 0), end=time(8, 40)),
    types.LessonTime(start=time(8, 50), end=time(9, 30)),
    types.LessonTime(start=time(9, 50), end=time(10, 30)),
    types.LessonTime(start=time(10, 50), end=time(11, 30)),
    types.LessonTime(start=time(11, 40), end=time(12, 20)),
    types.LessonTime(start=time(12, 30), end=time(13, 10)),
    types.LessonTime(start=time(13, 20), end=time(14, 0)),
    types.LessonTime(start=time(14, 10), end=time(14, 50)),
)


class Provider:
    """Поставщик расписания."""

    def __init__(self) -> None:
        self._meta: types.ScheduleStatus | None = None
        self._sc: types.Schedule | None = None
        self._session: aiohttp.ClientSession | None = None

    @property
    def meta(self) -> types.ScheduleStatus:
        """Возвращает статус расписания."""
        if self._meta is None:
            raise ValueError("You need to update schedule")
        return self._meta

    @property
    def sc(self) -> types.Schedule:
        """Возвращает полное расписания."""
        if self._sc is None:
            raise ValueError("You need to update schedule")
        return self._sc

    async def connect(self) -> None:
        """Подключение поставщика."""
        logger.debug("Connect provider")
        self._meta = await self._load_meta(Path("sp_data/meta.toml"))
        self._sc = await self._load_schedule(Path("sp_data/sc.json"))
        self._session = aiohttp.ClientSession(base_url=self._meta.url)

    async def close(self) -> None:
        """Завершение работы."""
        logger.debug("Close provider")
        if self._session is not None:
            await self._session.close()

        if self._meta is None or self._sc is None:
            raise ValueError("You need to update schedule before close")

        async with await anyio.open_file("sp_data/meta.toml", "w") as f:
            await f.write(toml.dumps(self._meta.model_dump()))

        async with await anyio.open_file("sp_data/sc.json", "w") as f:
            await f.write(json.dumps(self._sc.model_dump()))

    async def update(self) -> None:
        """Обновление данных."""

    # Получение данных
    # ================

    async def timetable(self) -> types.TimeTable:
        """Возвращает расписание звонков."""
        return _TIMETABLE

    async def status(self) -> types.Status:
        """Возвращает статус поставщика."""
        return types.Status(
            provider=types.ProviderStatus(
                name="SProvider",
                version="v1.0 (70)",
                url="https://git.miroq.ru/splatform/telegram",
            ),
            schedule=self.meta,
        )

    async def schedule(self, filters: types.ScheduleFilter) -> types.Schedule:
        """Возвращает расписание уроков."""
        return self.sc

    # Внутренние методы
    # =================

    async def _load_meta(self, path: Path) -> types.ScheduleStatus:
        async with await anyio.open_file(path) as f:
            meta = types.ScheduleMeta.model_validate(toml.loads(await f.read()))

        now = datetime.now(UTC)
        return types.ScheduleStatus(
            source=meta.source,
            url=meta.url,
            hash=meta.hash or "",
            check_at=meta.check_at or now,
            update_at=meta.update_at or now,
            next_check=meta.next_check or now,
        )

    async def _load_schedule(self, path: Path) -> types.Schedule:
        async with await anyio.open_file(path) as f:
            return types.Schedule.model_validate(json.loads(await f.read()))
