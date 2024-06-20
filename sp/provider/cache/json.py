from pathlib import Path

import ujson
from loguru import logger

from sp.provider.cache.base import BaseCacheStorage


class JsonCache(BaseCacheStorage):

    def __init__(self, path: Path | str) -> None:
        self.path = Path(ppth)

        if not self.path.exists():
            logger.info("Create cache file.")
            self.path.parent.mkdir(exist_ok=True, parents=True)


    def _load_file(self) -> dict[str, list[list[dict[str, str] | None]]] | None:
        logger.info("Load JSON cache - {}", self.path)
        try:
            with open(self.path) as f:
                return ujson.loads(f.read())
        except Exception as e:
            logger.error(e)

    def _write_file(self, data: dict[str, list[dict[str, str] | None]]) -> None:
        logger.info("Write JSON cache - {}", self.path)
        with open(self.path, "w") as f:
            f.write(ujson.dumps(data))

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

 