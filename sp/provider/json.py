from pathlib import Path

import ujson
from loguru import logger

from sp.provider.base import BaseProvider, BaseParser
from sp.schedule import Schedule, Lesson, DayLessons, WeekLessons


class JsonProvider(BaseProvider):
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def _load_file(self) -> dict[str, list[list[dict[str, str] | None]]] | None:
        logger.info("Load JSON from {}", self.path)
        try:
            with open(self.path) as f:
                return ujson.loads(f.read())
        except Exception as e:
            logger.error(e)

    def _dict_to_schedule(self,
        data: dict[str, list[list[dict[str, str] | None]]]
    ) -> Schedule:
        logger.info("Parse Schedule from JSON file...")
        sc_data: dict[str, WeekLessons] = {}

        for cl, week in data.items():
            week_lessons = []
            for day in week:
                day_lessons = []
                for lesson in day:
                    if lesson is None:
                        day_lessons.append(None)
                    else:
                        day_lessons.append(Lesson(
                            name=lesson.get("name"),
                            cabinet=lesson.get("cabinet")
                        ))
                week_lessons.append(DayLessons(day_lessons))
            sc_data[cl] = WeekLessons(*week_lessons)
        return Schedule(sc_data)

    def get(self) -> Schedule:
        logger.info("Get Schedule")
        file_data = self._load_file()
        if file_data is None:
            logger.error("Error load JSON file!")
            return None

        return self._dict_to_schedule(file_data)

