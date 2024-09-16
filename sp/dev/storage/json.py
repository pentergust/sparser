from datetime import datetime
from typing import NamedTuple, TypeVar, Any
from pathlib import Path

import ujson
from loguru import logger

from sp.dev.schedule import Schedule, WeekLessons, DayLessons, LessonMini


class StorageMetadata(NamedTuple):
    last_update: int
    api_verion: int


# Вспомогательные функции работы с файлами
# ========================================

_T = TypeVar("_T")

def _load_json(file: Path, default: dict[str, _T]) -> dict[str, _T]:
    try:
        with open(file) as f:
            return ujson.loads(f.read())
    except Exception as e:
        logger.warning("Load {} caused {}, returned default", path, e)
        return default

def _write_json(file: Path, data: dict[str, Any]) -> None:
    file.parent.mkdir(exist_ok=True, parents=True)
    with open(file, "w") as f:
        f.write(ujson.dumps(data, ensure_ascii=False, indent=2))


class JsonScheduleStorage:
    def __init__(self, storage_file: Path, api_verion: int):
        self.storage_file = storage_file
        self.metadata_file = storage_file.parent / (storage_file.name + ".meta")
        self.api_verion = api_verion

        self._schedule: Schedule | None = None
        self._metadata: StorageMetadata | None = None


    @property
    def metadata(self) -> StorageMetadata:
        if self._metadata is None:
            self._metadata = self._load_meta()
        return self._metadata

    @property
    def schedule(self):
        if self._schedule is None:
            self.load_from()
        return self._schedule


    # Работа с метаданными
    # ====================

    def _load_meta(self) -> StorageMetadata:
        meta_json = _load_json(self.metadata_file,
            default={"api_version": 0, "last_update": 0}
        )
        return StorageMetadata(
            last_update=meta_json["api_version"],
            api_verion=meta_json["api_version"]
        )

    def _update_meta(self) -> None:
        _write_json(self.metadata_file,
            data={
            "api_version": self.api_verion,
            "last_update": int(datetime.now().timestamp())
        })


    # Работа с расписанием
    # ====================

    def _load(self, sc_json: dict[list[list[dict[str, str]]]]) -> Schedule:
        sc = Schedule()
        for cl. cl_days in schedule_json.items():
            wl = WeekLessons(cl)
            for day, day_lessons in enumerate(cl_days):
                dl = DayLessons(cl=cl, weekday=day)

                for lesson in day_lessons:
                    dl.add(LessonMini(
                        name = lesson["name"],
                        location = lesson["location"],
                        teacher = lesson.get("teacher"),
                        metadata = lesson.get("metadata")
                    ))
                wl.set(day, dl)
            sc.set(cl, wl)
        return sc

    def _dump(self):
        sc_json = {}

        for week in self._schedule:
            week_lessons = []
            for day in week:
                day_lessons = []
                for lesson in day:
                    day_lessons.append({
                        "name": lesson.name,
                        "location": lesson.location,
                        "teacher": lesson.teacher,
                        "metadata": lesson.metadata
                    })
                week_lessons.append(day_lessons)
            sc_json[week.cl] = week_lessons

        _write_json(self.storage_file, sc_json)


    def load_from(self) -> None:
        self._metadata = self._load_meta()
        if self._metadata.api_verion < self.api_verion:
            return None
        elif self._metadata.api_verion > self.api_verion:
            raise ValueError("The schedule has been saved in a newer version")

        self._schedule = self._load(_load_json(self.storage_file, default={}))

    def write_to(self) -> None:
        if not isinstance(self._schedule, Schedule):
            raise ValueError("Schedule must be valid Schedule instance")
        _write_json(self.storage_file, self._dump(self._schedule))


    def get(self) -> Schedule:
        if self._schedule is None:
            self.load_from()
        return self._schedule

    def set(self, sc: Schedule) -> None:
        if not isinstance(sc, Schedule):
            raise ValueError("You can only store the schedule instance")
        self._schedule = sc
