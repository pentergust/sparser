"""Поставщик гугл таблиц.

Загружает расписание из специальной гугл таблицы.

TODO: Хранилище расписания
TODO: Хранилище обновлений
"""

import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any, TypedDict, TypeVar

import openpyxl
import requests
import ujson
from loguru import logger

from sp.provider.base import Provider
from sp.schedule import Schedule
from sp.timetable import LessonTime, Timetable
from sp.updates import UpdateData

_MAIN_URL = "https://docs.google.com/spreadsheets/d/1pP_qEHh4PBk5Rsb7Wk9iVbJtTA11O9nTQbo1JFjnrGU/export?format=xlsx"

# TODO: Переместить в хранилище
RAW_SC_PATH = Path("sp_data/sc.xlsx")
SC_PATH = Path("sp_data/sc.json")
SC_UPDATES_PATH = Path("sp_data/updates.json")
INDEX_PATH = Path("sp_data/index.json")
TIMETABLE_PATH = Path("sp_data/timetable.json")

LoadData = dict[str, Any] | list[Any]
_T = TypeVar("_T", bound=LoadData)
LessonIndex = dict[str, list[dict[str, dict[str, list[int]]]]]
ClassIndex = dict[str, list[dict[str, dict[str, list[int]]]]]
SearchRes = list[list[list[str]]]


def save_file(path: Path, data: _T) -> _T:
    """Записывает данные в json файл.

    Используется как обёртка для более удобной упаковки данных
    в json файлы.
    Автоматически создаёт файл, если он не найден.

    .. deprecated:: 6.1
        В скором времени проект откажется от использования json.
        Данные методы будут перемещены.
    """
    logger.info("Write file {} ...", path)
    if not path.exists():
        path.parents[0].mkdir(parents=True, exist_ok=True)
        logger.info("Created not exists dirs")

    with open(path, "w") as f:
        f.write(ujson.dumps(data, indent=4, ensure_ascii=False))
    return data


def load_file(path: Path, data: _T | None = None) -> _T:
    """Читает данные из json файла.

    Используется как обёртка для более удобного чтения данных из
    json файла.
    Если переданы данные и файла не существует -> создаёт новый файл
    и записывает переданные данные.
    Если файла не существует и данные переданы или возникло исключение
    при чтении файла -> возвращаем пустой словарь.

    .. deprecated:: 6.1
        В скором времени проект откажется от использования json.
        Данные методы будут перемещены.
    """
    try:
        with open(path) as f:
            return ujson.loads(f.read())
    except FileNotFoundError:
        if data is not None:
            logger.warning("File not found {} -> create", path)
            save_file(path, data)
            return data
        logger.error("File not found {}", path)
        return data
    except Exception as e:
        logger.exception(e)
        return data


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


def get_sc_updates(
    a: dict[str, list], b: dict[str, list]
) -> list[dict[str, list]]:
    """Делает полное сравнение двух расписаний.

    Делает полное построчное сравнение старого и нового расписания.
    Возвращает все найденные изменения в формате.

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


def get_index(
    sp_lessons: dict[str, list[list[str]]], lessons_mode: bool | None = True
) -> dict[str, list[dict]]:
    """Преобразует словарь расписания уроков в индекс.

    В данном случае индексом называется словарь, где ключом вместо
    класса является название урока или кабинета.

    Они так же часто используются, как и само расписание.
    Например при подсчёте количества элементов или при поиске в
    расписании определённого урока или кабинета.

    **Описание индексов**:

    - Расписание: `[Класс][День][Уроки]`
    - l_mode True: `[Урок][День][Кабинет][Класс][Номер урока]`
    - l_mode False: `[Кабинет][День][Урок][Класс][Номер урока]`
    """
    logger.info("Get {}_index", "l" if lessons_mode else "c")
    index: dict[str, list[dict]] = defaultdict(
        lambda: [defaultdict(lambda: defaultdict(list)) for x in range(6)]
    )

    for cl, v in sp_lessons.items():
        for day, lessons in enumerate(v):
            for n, lesson_data in enumerate(lessons):
                lesson, cabinet = lesson_data.lower().split(":")
                lesson = lesson.strip(" .")
                for old, new in [("-", "="), (" ", "-"), (".-", ".")]:
                    lesson = lesson.replace(old, new)

                # Obj - Первичный ключ индекса, урок или кабинет.
                # another - = Вторичный ключ, противоположный первичному
                obj = [lesson] if lessons_mode else cabinet.split("/")
                another = cabinet if lessons_mode else lesson

                for x in obj:
                    index[x][day][another][cl].append(n)
    return index


def parse_lessons() -> dict[str, list[list[str]]]:  # noqa: PLR0912
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


@dataclass(slots=True, frozen=True)
class RawSchedule:
    """Сырое загруженное расписание из сети."""

    hash: str
    data: str


class ScheduleDict(TypedDict):
    """Описывает что собой представляет словарь расписание."""

    hash: str
    last_parse: int
    lessons: dict[str, list[list[str]]]


class GoogleProvider(Provider):
    """Поставщик гугл таблиц."""

    def __init__(
        self,
        url: str = _MAIN_URL,
        sc_path: Path | str = SC_PATH,
        updates_path: Path | str = SC_UPDATES_PATH,
        index_path: Path | str = INDEX_PATH,
        timetable_path: Path | str = TIMETABLE_PATH,
    ) -> None:
        self.url = url
        # Определение путей к файлам.
        self._sc_path = Path(sc_path)
        self._updates_path = Path(updates_path)
        self._index_path = Path(index_path)
        self._timetable_path = Path(timetable_path)
        self._timetable: Timetable | None = None
        self.next_parse: int | None = None
        self._schedule: Schedule | None = None
        self._updates: list[UpdateData] | None = None

    def _load_timetable(self) -> Timetable:
        file: list[list[list[int]]] = load_file(self._timetable_path)
        lessons: list[LessonTime] = []
        for start, end in file:
            lessons.append(
                LessonTime(time(start[0], start[1]), time(end[0], end[1]))
            )
        return Timetable(lessons)

    def update_timetable(self) -> None:
        """Обновляет расписание звонков."""
        self._timetable = self._load_timetable()

    async def timetable(self) -> Timetable:
        """Расписание звонков."""
        if self._timetable is None:
            self._timetable = self._load_timetable()

        return self._timetable

    # Работа с расписанием
    # ====================

    def _load_file(self) -> Schedule:
        file_data: ScheduleDict = load_file(self._sc_path)
        self._updates = load_file(self._updates_path)
        lessons: dict[str, list[list[str]]] = file_data["lessons"]
        l_index: LessonIndex = get_index(lessons)
        c_index: ClassIndex = get_index(lessons, False)

        return Schedule(
            lessons,
            file_data["hash"],
            file_data["last_parse"],
            l_index,
            c_index,
            self._updates,
        )

    def _write_file(self, schedule: Schedule) -> None:
        save_file(
            self._sc_path,
            {
                "hash": schedule.hash,
                "lessons": schedule.schedule,
                "last_parse": schedule.loaded_at,
            },
        )

    def _load_raw(self) -> RawSchedule:
        logger.info("Download schedule csv_file ...")
        # TODO:Гле асинхронность я спрашиваю тебя
        raw_data = requests.get(self.url).text
        return RawSchedule(hashlib.md5(raw_data.encode()).hexdigest(), raw_data)

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

    # 8< -----------------------------------------------------------------------

    async def _load_schedule(self, now: int) -> Schedule:
        """Полное обновление расписания, индексов, файла обновлений.

        Производит полное обновление расписания уроков.
        Загружает файл csv файла расписания.
        Если хеши не отличаются, устанавливаем время следующей
        проверки и завершаем работу.

        Если расписание изменилось, собираем новое расписание из
        csv файла, получаем файл индексов и обновляем список
        изменений.
        """
        logger.info("Start schedule update ...")
        raw = self._load_raw()
        if self._schedule is not None and self._schedule.hash == raw.hash:
            logger.info("Schedule is up to date")
            self.next_parse = now + 1800
            return self._schedule

        self.next_parse = now + 1800
        lessons = parse_lessons()
        l_index: LessonIndex = get_index(lessons)
        c_index: ClassIndex = get_index(lessons, False)

        sc = Schedule(
            lessons,
            raw.hash,
            now,
            l_index,
            c_index,
            self._updates,
        )

        self._update_diff_file(sc)
        self._write_file(sc)
        return sc

    async def update_schedule(self) -> None:
        """Обновляет расписание звонков."""
        now = int(datetime.timestamp(datetime.now(UTC)))
        self._schedule = await self._load_schedule(now)

    async def schedule(self) -> Schedule:
        """Возвращает расписание уроков."""
        now = int(datetime.timestamp(datetime.now(UTC)))
        if self._schedule is None:
            self._schedule = self._load_file()

        if self.next_parse is None or self.next_parse < now:
            self._schedule = await self._load_schedule(now)

        return self._schedule
