"""Главный файл приложения."""

from fastapi import FastAPI

from provider.types import Schedule, ScheduleFilter, Status, TimeTable

app = FastAPI()

@app.get("/time")
async def get_timetable() -> TimeTable:
    """Возвращает расписание звонков."""

@app.get("/status")
async def get_provider_status() -> Status:
    """Возвращает расписание звонков."""

@app.get("/schedule")
async def get_schedule(filter: ScheduleFilter) -> Schedule:
    """Возвращает расписание уроков."""
