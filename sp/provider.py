"""Поставщик расписания."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import aiohttp

from sp import types


class Provider:
    """Поставщик расписания.

    Получает расписание от поставщика.
    Автоматически кеширует расписание.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._session: aiohttp.ClientSession | None = None

        self._meta: types.Status | None = None
        self._sc: types.Schedule | None = None

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

    async def fetch_schedule(
        self, filters: types.ScheduleFilter | None = None
    ) -> types.Schedule:
        """Возвращает расписание уроков."""
        resp = await self.session.post(
            "schedule",
            data=filters.model_dump() if filters is not None else None,
        )
        resp.raise_for_status()
        return types.Schedule.model_validate(await resp.json())


    async def fetch_time(self) -> types.TimeTable:
        """Возвращает расписание звонков."""
        resp = await self.session.get("time")
        resp.raise_for_status()
        data: Sequence[Any] = await resp.json()
        return [types.LessonTime.model_validate(lesson) for lesson in data]


    async def fetch_status(self) -> types.Status:
        """Возвращает статус поставщика и расписания."""
        resp = await self.session.get("status")
        resp.raise_for_status()
        return types.Status.model_validate(await resp.json())


    async def fetch_cl(self) -> Sequence[str]:
        """Возвращает список классов в расписании."""
        resp = await self.session.get("cl")
        resp.raise_for_status()
        return await resp.json()

    # Обновление кеша
    # ===============

    async def _check_update(self) -> None:
        if self._meta is None or self._sc is None:
            await self.update()
            return

        now = datetime.now(UTC)
        if now < self._meta.schedule.next_check:
            return

    async def update(self) -> None:
        """Обновляет данные из поставщика."""
        sc_hash = self._meta.schedule.hash if self._meta is not None else None
        self._meta = await self.fetch_status()
        if sc_hash == self._meta.schedule.hash:
            return

        self._sc = await self.fetch_schedule()


    # Кешированное получение
    # ======================

    # TODO: Оборачивать в полноценное расписание

    async def schedule(self) -> types.Schedule:
        """Возвращает расписание уроков."""
        await self._check_update()
        if self._sc is None:
            raise ValueError("Error when update schedule")
        return self._sc

    # TODO: Использовать в view

    async def status(self) -> types.Status:
        """Возвращает статус поставщика и расписания."""
        await self._check_update()
        if self._meta is None:
            raise ValueError("Error when update schedule")
        return self._meta
