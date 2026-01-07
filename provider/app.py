"""Главный файл приложения."""

from fastapi import FastAPI

from provider.provider import Provider
from provider.types import Schedule, ScheduleFilter, Status, TimeTable

app = FastAPI()
provider = Provider()


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
