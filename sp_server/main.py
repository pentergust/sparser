"""Главный файл сервера."""

import asyncio
from pathlib import Path
from typing import NoReturn

import fastapi
from fastapi import HTTPException
from loguru import logger

from sp_server.provider import ScheduleProvider
from sp_server.schedule import (
    DayLessons,
    Status,
    TimeTable,
    WeekLessons,
)

provider = ScheduleProvider()
provider.load_from(Path("sp_data/"))
app = fastapi.FastAPI()


async def parse_loop(provider: ScheduleProvider) -> NoReturn:
    """Цикл обновления расписания."""
    while True:
        try:
            await provider.parse()
        except Exception as e:
            logger.exception(e)
            await asyncio.sleep(60)
            continue
        await asyncio.sleep(3600)


asyncio.create_task(parse_loop(provider))


@app.get("/time")
async def timetable() -> TimeTable:
    """Расписание звонков."""
    return provider.timetable


@app.get("/status")
async def status() -> Status:
    """Статус расписания."""
    return provider.status


@app.get("/{cl}/week")
async def week_schedule(cl: str) -> WeekLessons:
    """Расписание на неделю."""
    sc = provider.schedule.get(cl)
    if sc is None:
        raise HTTPException(404, "Class not found")
    return sc


@app.get("/{cl}/{day}")
async def day_schedule(cl: str, day: int) -> DayLessons:
    """Возвращает расписание на день."""
    sc = provider.schedule.get(cl)
    if sc is None:
        raise HTTPException(404, "Class not found")

    return sc[min(max(day, 0), 5)]
