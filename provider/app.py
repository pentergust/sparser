"""Главный файл приложения."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from provider.checker import Checker
from provider.provider import Provider
from provider.types import Schedule, ScheduleFilter, Status, TimeTable

provider = Provider()
checker = Checker(provider)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Жизненный цикл сервера."""
    logger.info("Start server")
    await provider.connect()
    await checker.run()

    yield

    logger.info("Stop server")
    checker.stop()
    await provider.close()


app = FastAPI(lifespan=lifespan, root_path="/api")


@app.get("/time")
async def get_timetable() -> TimeTable:
    """Возвращает расписание звонков."""
    return await provider.timetable()


@app.get("/status")
async def get_provider_status() -> Status:
    """Возвращает расписание звонков."""
    return await provider.status()


@app.get("/cl")
async def get_provider_cl() -> list[str]:
    """Возвращает расписание звонков."""
    return list(provider.sc.schedule.keys())


@app.post("/schedule")
async def get_schedule(filters: ScheduleFilter | None = None) -> Schedule:
    """Возвращает расписание уроков."""
    return await provider.schedule(filters)
