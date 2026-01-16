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
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
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
    """Возвращает общее расписание звонков для расписания."""
    return await provider.timetable()


@app.get("/status")
async def get_provider_status() -> Status:
    """Возвращает статус расписания.

    Содержит техническую информацию о поставщике.
    А также статус расписания.
    Может быть использовано для автоматической проверки обновлений.
    """
    return await provider.status()


@app.get("/cl")
async def get_provider_cl() -> list[str]:
    """Возвращает полный список всех классов в расписании."""
    return list(provider.sc.schedule.keys())


@app.get("/schedule")
async def get_schedule() -> Schedule:
    """Возвращает полное расписание уроков."""
    return await provider.schedule()


@app.post("/schedule")
async def filter_schedule(filters: ScheduleFilter | None = None) -> Schedule:
    """Возвращает отфильтрованное или расписание уроков.

    Вы можете передать фильтры чтобы получить расписание для получения
    расписания для определённых классов/дней недели.
    """
    return await provider.schedule(filters)
