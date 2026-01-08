"""Поставщик расписания."""

from collections.abc import Sequence
from typing import Any

import aiohttp

from sp import types

# TODO: Добавить кеширование


class Provider:
    """Поставщик расписания.

    Получает расписание от поставщика.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """Возвращает активную сессию."""
        if self._session is None:
            raise ValueError("You need connect to provider")
        return self._session

    async def connect(self) -> None:
        """Подключается к поставщику."""
        self._session = aiohttp.ClientSession(base_url=self._url)

    async def close(self) -> None:
        """Завершает сессию с поставщиком."""
        if self._session is not None:
            await self._session.close()

    # Получение данных из поставщика
    # ==============================

    # TODO: Оборачивать в полноценное расписание

    async def schedule(
        self, filters: types.ScheduleFilter | None = None
    ) -> types.Schedule:
        """Возвращает расписание уроков."""
        resp = await self.session.post(
            "schedule",
            data=filters.model_dump() if filters is not None else None,
        )
        resp.raise_for_status()
        return types.Schedule.model_validate(await resp.json())

    # TODO: Использовать sp.timetable

    async def time(self) -> types.TimeTable:
        """Возвращает расписание звонков."""
        resp = await self.session.get("time")
        resp.raise_for_status()
        data: Sequence[Any] = await resp.json()
        return [types.LessonTime.model_validate(lesson) for lesson in data]

    # TODO: Использовать в view

    async def status(self) -> types.Status:
        """Возвращает статус поставщика и расписания."""
        resp = await self.session.get("status")
        resp.raise_for_status()
        return types.Status.model_validate(await resp.json())

    # TODO: Использовать в намерениях

    async def cl(self) -> Sequence[str]:
        """Возвращает список классов в расписании."""
        resp = await self.session.get("cl")
        resp.raise_for_status()
        return await resp.json()
