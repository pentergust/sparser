"""Поставщик расписания."""

import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
import openpyxl
import orjson
from loguru import logger

from sp.updates import UpdateData
from sp_server.schedule import LessonTime, Schedule, Status, TimeTable

LoadData = dict[str, Any] | list[Any]
LessonIndex = dict[str, list[dict[str, dict[str, list[int]]]]]
ClassIndex = dict[str, list[dict[str, dict[str, list[int]]]]]
SearchRes = list[list[list[str]]]


@dataclass(slots=True, frozen=True)
class RawSchedule:
    """Сырое загруженное расписание."""

    hash: str
    data: str


def _get_day_hash(day_lessons: list) -> str:
    return hashlib.md5(("".join(day_lessons)).encode()).hexdigest()


def _clear_day_lessons(day_lessons: list[str]) -> list[str]:
    """Удаляет все пустые уроки с конца списка."""
    while day_lessons:
        lesson = day_lessons[-1].split(":")[0]
        if lesson and lesson not in ("---", "None"):
            return day_lessons
        day_lessons.pop()
    return []


def get_sc_updates(a: Schedule, b: Schedule) -> list[dict[str, list]]:
    """Полное сравнение двух расписаний.


    ```py
        [
            // дни ...
            {
                // классы ...
                "9в" [
                    // уроки ...
                    null, // Ничего не изменилось
                    ["старый:12", "новый:132"] // Предмет изменился
                ]
            }
        ]
    ```
    """
    updates: list[dict] = [defaultdict(lambda: [None] * 8) for x in range(6)]
    # Проходимся по классам в новом расписании
    for k, v in b.items():
        if k not in a:
            continue

        # Пробегаемся по дням недели в новом расписании
        av = a[k]
        for day, lessons in enumerate(v):
            if _get_day_hash(lessons) == _get_day_hash(av[day]):
                continue

            a_lessons = av[day]
            for i, lesson in enumerate(lessons):
                al = a_lessons[i] if i <= len(a_lessons) - 1 else None
                if lesson != al:
                    updates[day][k][i] = (al, lesson)
    return updates


def parse_lessons() -> dict[str, list[list[str]]]:
    """Разбирает XLSX файл в словарь расписания.

    Расписание в XLSX файле представлено подобным образом.

    +--+-------+---------+
    |  | класс |         | <- Шапка с классами в расписание
    +--+-------+---------+
    | 1| урок  | кабинет | <- Первый урок понедельника.
    | n| ...   | ...     |
    +--+-------+---------+
    | 1| урок  | кабинет | <- Первый урок вторника.
    | n| ...   | ...     |
    +--+-------+---------+

    Задача этой функции преобразовать таблицу выше в словарь расписания
    уроков формата:


    ```py
    {
        // Классы
        "класс" {
            // Дни
            [
                // Уроки в днях
                "урок:кабинет"
            ]
        }
    }
    ```
    """
    logger.info("Start parse lessons...")

    # lessons: Словарь расписания [Класс][День]
    lessons: dict[str, list] = defaultdict(lambda: [[] for x in range(6)])
    day = -1
    last_row = 8
    sheet = openpyxl.load_workbook(str(RAW_SC_PATH)).active
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

    # построчно читаем расписание уроков
    for row in row_iter:
        # Первый элемент строки указывает на день недели.
        if isinstance(row[0].value, str) and len(row[0].value) > 0:
            logger.info("Process group {} ...", row[0].value)

        # Если второй элемент в ряду указывает на номер урока
        if isinstance(row[1].value, int | float):
            # Если вдруг номер урока стал меньше, начался новый день
            if row[1].value < last_row:
                day += 1
            last_row = int(row[1].value)

            for cl, i in cl_header:
                # Если класса нет в расписании, то добавляем его
                # А если строка зачёркнута, то также пропускаем
                if row[i].value is None or row[i].font.strike:
                    lesson = None
                else:
                    lesson = str(row[i].value).strip(" .-").lower() or None

                # Кабинеты иногда представлены числом, иногда строкой
                # Спасибо электронные таблицы, раньше было проще
                if row[i + 1].value is None:
                    cabinet = "None"
                elif isinstance(row[i + 1].value, float):
                    cabinet = str(int(row[i + 1].value))
                elif isinstance(row[i + 1].value, str):
                    cabinet = str(row[i + 1].value).strip().lower() or "0"
                else:
                    raise ValueError(f"Invalid cabinet format: {row[i + 1]}")

                lessons[cl][day].append(f"{lesson}:{cabinet}")

        elif day == 5:  # noqa
            logger.info("CSV file reading completed")
            break

    return {k: [_clear_day_lessons(x) for x in v] for k, v in lessons.items()}


class ScheduleProvider:
    """Поставляет расписание из стороннего источника."""

    def __init__(self, data_path: Path) -> None:
        self._data_path = data_path
        self._schedule: Schedule | None = None
        self._status: Status | None = None
        self._timetable: TimeTable | None = None

        self._session = aiohttp.ClientSession()

    @property
    def status(self) -> Status:
        """Возвращает статус расписания."""
        if self._status is None:
            raise ValueError("Status is None")
        return self._status

    @property
    def schedule(self) -> Schedule:
        """Возвращает расписание уроков."""
        if self._schedule is None:
            raise ValueError("Schedule is None")
        return self._schedule

    def load_from(self) -> None:
        """Загружает данные из файлов."""
        with (self._data_path / "status.json").open() as f:
            self._status = Status.model_validate(orjson.loads(f.read()))

        with (self._data_path / "schedule.json").open() as f:
            self._schedule = orjson.loads(f.read())

        with (self._data_path / "timetable.json").open() as f:
            raw_time: list[list[int]] = orjson.loads(f.read())

        timetable: TimeTable = []
        for row in raw_time:
            timetable.append(
                LessonTime(start=(row[0], row[1]), end=(row[2], row[3]))
            )
        self._timetable = timetable

    def _write_to(self) -> None:
        """Записывает данные поставщика в файла."""
        with (self._data_path / "status.json").open("w") as f:
            f.write(self.status.model_dump_json())

    async def _load_raw(self) -> RawSchedule:
        logger.info("Download schedule csv_file ...")
        resp = await self._session.get(self.status.url)
        resp.raise_for_status()
        raw_data = await resp.text()
        return RawSchedule(hashlib.md5(raw_data.encode()).hexdigest(), raw_data)

    async def parse(self) -> None:
        """Загружает новую версию расписания."""
        logger.info("Start schedule update ...")
        raw = await self._load_raw()
        if self._schedule is not None and self.status.hash == raw.hash:
            logger.info("Schedule is up to date")
            return

        sc = parse_lessons()
        self._schedule = sc
        self._update_diff_file(sc)
        self._write_to()

    @property
    def timetable(self) -> TimeTable:
        """Расписание звонков."""
        if self._timetable is None:
            raise ValueError("Timetable is None")

        return self._timetable

    def _update_diff_file(self, a: ScheduleDict, b: ScheduleDict) -> None:
        """Обновляет файл списка изменений расписания.

        Производит полное сравнение старого и нового расписания.
        После сравнения создаёт новую запись о найденных изменениях и
        добавляет её в файл списка изменений.
        """
        logger.info("Update diff file ...")
        sc_changes: deque[UpdateData] = deque(
            load_file(self._updates_path, []), 30
        )
        updates = get_sc_updates(a.get("lessons", {}), b["lessons"])
        if not sum(map(len, updates)):
            return

        if len(sc_changes):
            start_time = sc_changes[-1]["end_time"]
        else:
            start_time = b["last_parse"]

        sc_changes.append(
            {
                "start_time": start_time,
                "end_time": b["last_parse"],
                "updates": updates,
            }
        )
        save_file(self._updates_path, list(sc_changes))
