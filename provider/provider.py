"""Поставщик расписания."""

import hashlib
import io
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import aiohttp
import anyio
import openpyxl
import toml
from loguru import logger

from provider import types
from sp.counter import defaultdict


@dataclass(slots=True, frozen=True)
class RawSchedule:
    """Сырое загруженное расписание из сети."""

    hash: str
    data: bytes


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


def _clear_day_lessons(day_lessons: types.DayLessons) -> types.DayLessons:
    """Удаляет все пустые уроки с конца списка."""
    while day_lessons:
        lesson = day_lessons[-1]
        if lesson and lesson.name not in ("---", "None"):
            return day_lessons
        day_lessons.pop()
    return []


def parse_lessons(data: io.BytesIO) -> types.ScheduleT:
    """Разбирает XLSX файл в словарь расписания.

    Расписание в XLSX файле представлено подобным образом.
    """
    logger.info("Start parse lessons...")
    lessons: types.ScheduleT = defaultdict(lambda: [[] for _ in range(6)])
    day = -1
    last_row = 8
    sheet = openpyxl.load_workbook(data).active
    if sheet is None:
        raise ValueError("Loaded Schedule active tab is wrong")
    row_iter = sheet.iter_rows()

    # Получает кортеж с именем класса и индексом
    # соответствующего столбца расписания
    next(row_iter)
    cl_header: list[tuple[str, int]] = []
    for i, cl in enumerate(next(row_iter)):
        if isinstance(cl.value, str) and cl.value.strip():
            cl_header.append((cl.value.lower(), i))

    for row in row_iter:
        # Первый элемент строки указывает на день недели.
        if isinstance(row[0].value, str) and len(row[0].value) > 0:
            logger.debug("Process group {} ...", row[0].value)

        # Если второй элемент в ряду указывает на номер урока
        if isinstance(row[1].value, int | float):
            # Если вдруг номер урока стал меньше, начался новый день
            if row[1].value < last_row:
                day += 1
            last_row = int(row[1].value)

            for cl, i in cl_header:
                if row[i].value is None or row[i].font.strike:
                    lesson = None
                else:
                    lesson = str(row[i].value).strip(" .-").lower() or None

                # Кабинеты иногда представлены числом, иногда строкой
                # Спасибо электронные таблицы, раньше было проще
                if row[i + 1].value is None:
                    cabinet = []
                elif isinstance(row[i + 1].value, float):
                    cabinet = [str(int(row[i + 1].value))]
                elif isinstance(row[i + 1].value, str):
                    cabinet = [str(row[i + 1].value).strip().lower()]
                else:
                    raise ValueError(f"Invalid cabinet format: {row[i + 1]}")

                lessons[cl][day].append(
                    types.Lesson(name=lesson, cabinets=cabinet)
                )

        elif day == 5:  # noqa: PLR2004
            logger.info("CSV file reading completed")
            break

    return {k: [_clear_day_lessons(x) for x in v] for k, v in lessons.items()}


def _filter_cl(
    sc: types.ScheduleT, cl: Sequence[str] | None
) -> types.ScheduleT:
    if cl is None or len(cl) == 0:
        return sc
    return {k: v for k, v in sc.items() if k in cl}


def _filter_days(
    sc: types.ScheduleT, days: Sequence[int] | None
) -> types.ScheduleT:
    if days is None or len(days) == 0:
        return sc
    return {
        k: [day_lessons for day, day_lessons in enumerate(v) if day in days]
        for k, v in sc.items()
    }


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

        await self._save_files()

    async def _load_raw(self) -> RawSchedule:
        logger.info("Download schedule csv_file ...")
        assert self._session is not None  # noqa: S101
        resp = await self._session.get("export?format=xlsx")
        resp.raise_for_status()
        raw_data = await resp.content.read()
        return RawSchedule(
            hashlib.md5(raw_data, usedforsecurity=False).hexdigest(),
            raw_data,
        )

    async def update(self) -> None:
        """Обновление данных."""
        logger.debug("Start schedule update...")
        if self._meta is None:
            raise ValueError("You need to connect provider before update")

        now = datetime.now(UTC)
        if now < self.meta.next_check:
            logger.debug("Not now -> sleep")
            return

        raw = await self._load_raw()
        if self._meta.hash == raw.hash:
            logger.info("Schedule is up to date")
            self._meta.next_check = now + timedelta(minutes=30)
            return

        self._meta.next_check = now + timedelta(minutes=30)
        self._sc = types.Schedule(
            schedule=parse_lessons(io.BytesIO(initial_bytes=raw.data))
        )

        await self._save_files()

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
        sc = _filter_cl(self.sc.schedule, filters.cl)
        sc = _filter_days(sc, filters.days)
        return types.Schedule(schedule=sc)

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

    async def _save_files(self) -> None:
        if self._meta is None or self._sc is None:
            raise ValueError("You need to update schedule before close")

        async with await anyio.open_file("sp_data/meta.toml", "w") as f:
            await f.write(toml.dumps(self._meta.model_dump()))

        async with await anyio.open_file("sp_data/sc.json", "w") as f:
            await f.write(json.dumps(self._sc.model_dump()))
