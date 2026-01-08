"""Главный файл приложения."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from provider.provider import Provider
from provider.types import Schedule, ScheduleFilter, Status, TimeTable

provider = Provider()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Жизненный цикл сервера."""
    logger.info("Start server")
    await provider.connect()

    yield

    logger.info("Stop server")
    await provider.close()


app = FastAPI(lifespan=lifespan)


@app.get("/time")
async def get_timetable() -> TimeTable:
    """Возвращает расписание звонков."""
    return await provider.timetable()


@app.get("/status")
async def get_provider_status() -> Status:
    """Возвращает расписание звонков."""
    return await provider.status()


@app.get("/schedule")
async def get_schedule(filters: ScheduleFilter) -> Schedule:
    """Возвращает расписание уроков."""
    return await provider.schedule(filters)
