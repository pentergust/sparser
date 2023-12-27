"""
Самостоятельный парсер школьного расписания.

Author: Milinuri Nirvalen
"""

from .intents import Intent
from .utils import load_file
from .utils import save_file

import csv
import hashlib
import requests

from collections import deque
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

url = "https://docs.google.com/spreadsheets/d/1pP_qEHh4PBk5Rsb7Wk9iVbJtTA11O9nTQbo1JFjnrGU/export?format=csv"
sc_path = "sp_data/sc.json"
sc_updates_path = "sp_data/updates.json"
index_path = "sp_data/index.json"


# Вспомогательные функции
# =======================

def get_day_hash(day_lessons: list) -> str:
    return hashlib.md5(("".join(day_lessons)).encode()).hexdigest()

def get_sc_updates(a: dict, b: dict) -> list:
    """Делает полное сравнение расписания B и A.

    Формат списка изменений:
        [класс][день] [номер урока, старый урок, новый урок]

    Args:
        a (dict): Первое (старое) расписание
        b (dict): Второе (новое) расписание

    Returns:
        list: Список изменений в расписании
    """
    updates = [defaultdict(lambda: [None] * 8) for x in range(6)]

    for k, v in b.items():
        if not k in a:
            continue

        # Пробегаемся по дням недели в новом расписании
        av = a[k]
        for day, lessons in enumerate(v):
            if get_day_hash(lessons) == get_day_hash(av[day]):
                continue

            a_lessons = av[day]
            for i, l in enumerate(lessons):
                al = a_lessons[i] if i <= len(a_lessons)-1 else None
                if l != al:
                    updates[day][k][i] = (al, l)
    return updates

def get_index(sp_lessons: dict, lessons_mode: Optional[bool] = True) -> dict:
    """Преобразует расписание уроков в индекс предметов/кабинетов.
    Индeксом называется словарь расписания, где как ключ вместо
    классов используюся кабинеты/уроки.

    - Расписание: [Класс][День][Уроки]
    - l_index (l_mode True): [Урок][День][Кабинет][Класс][Номер урока]
    - c_index (l_mode False): [Кабинет][День][Урок][Класс][Номер урока]

    Args:
        sp_lessons (dict): Расписание уроков sp.lessons
        lessons_mode (bool, optional): Использовать как ключ уроки

    Returns:
        dict: Индекс уроков/кабинетов
    """
    logger.info("Get {}_index", "l" if lessons_mode else "c")
    res = {}
    for k, v in sp_lessons.items():
        for day, lessons in enumerate(v):
            for n, l in enumerate(lessons):
                l, c = l.lower().split(":")
                l = l.strip(" .")
                for old, new in [('-', '='), (' ', '-'), (".-", '.')]:
                    l = l.replace(old, new)

                obj = [l] if lessons_mode else c.split("/")
                another = c if lessons_mode else l

                for x in obj:
                    if x not in res:
                        res[x] = [{} for x in range(6)]

                    if another not in res[x][day]:
                        res[x][day][another] = {}

                    if k not in res[x][day][another]:
                        res[x][day][another][k] = []

                    res[x][day][another][k].append(n)
    return res


def clear_day_lessons(day_lessons: list) -> list:
    """Удаляет все пустые уроки с конца списка."""
    while day_lessons:
        l = day_lessons[-1].split(":")[0]
        if not l or l in ["---", "None"]:
            del day_lessons[-1]
        else:
            break
    return day_lessons


def parse_lessons(csv_file: str) -> dict:
    """Пересобирает CSV файл расписания в удобный формат.

    Args:
        csv_file (str): CSV файла расписания

    Returns:
        dict: Словарь расписания по классам
    """
    logger.info("Start parse lessons...")

    # lessons: Словарь расписания [Класс][День]
    # day: Номер текущего дня недели (0-5)
    # Последняя строка с указанием номера урока
    lessons = {}
    day = -1
    last_row = 8
    reader = list(csv.reader(csv_file.decode("utf-8").splitlines()))

    # Получаем словарь с классами и их столбцами в расписании
    cl_index = {v.lower(): k for k, v in enumerate(reader[1]) if v.strip()}
    for i, row in enumerate(reader[2:]):
        # Если второй элемент в ряду указывает на номер урока
        if row[1].isdigit():
            if int(row[1]) < last_row:
                day += 1
            last_row = int(row[1])

            for k, v in cl_index.items():
                # Если класса нет в расписании, то добавляем его
                if k not in lessons:
                    lessons[k] = [[] for x in range(6)]

                lesson = row[v].strip(" .-").lower() or None
                cabinet = row[v+1].strip().lower() or 0
                lessons[k][day].append(f"{lesson}:{cabinet}")

        elif day == 5:
            logger.info("CSV file reading completed")
            break

    return {k: list(map(clear_day_lessons, v)) for k, v in lessons.items()}


class Schedule:
    """Расписания уроков и способы взаимодействия с ним."""
    def __init__(self, cl: str) -> None:
        super(Schedule, self).__init__()
        self.cl = cl

        self.sc_path = Path(sc_path)
        self.updates_path = Path(sc_updates_path)
        self.index_path = Path(index_path)

        self._l_index = None
        self._c_index = None
        self._updates = None

        self.schedule = self.get()
        self.lessons = self.schedule["lessons"]

    @property
    def l_index(self) -> dict:
        """Информация об уроках. Имена, для кого, когда."""
        if not self._l_index:
            self._l_index = load_file(self.index_path)[0]
        return self._l_index

    @property
    def c_index(self) -> dict:
        """Информацию о кабинетах. Какие уроки, для кого, когда."""
        if not self._c_index:
            self._c_index = load_file(self.index_path)[1]
        return self._c_index

    @property
    def updates(self) -> list:
        """Список изменений в расписании."""
        if self._updates is None:
            self._updates = load_file(self.updates_path)
        return self._updates


    # Получаем расписание
    # ===================

    def _update_diff_file(self, a: dict, b: dict) -> None:
        """Обновляет файл изменений в расписании.

        Args:
            a (dict): Старое расписание
            b (dict): Новое расписание
        """
        logger.info("Update diff file...")
        sc_changes = deque(load_file(self.updates_path, []), 30)
        updates = get_sc_updates(a.get("lessons", {}), b["lessons"])
        if sum(map(len, updates)):
            if len(sc_changes):
                start_time = sc_changes[-1]["end_time"]
            else:
                start_time = b["last_parse"]

            sc_changes.append({
                "start_time": start_time,
                "end_time": b["last_parse"],
                "updates": updates}
            )
            save_file(self.updates_path, list(sc_changes))

    def _update_index_files(self, sp_lessons: dict) -> None:
        """Обновляет файл индексов.

        Args:
            sp_lessons (dict): Уроки в расписании
        """
        logger.info("Udate index files...")
        index = [get_index(sp_lessons), get_index(sp_lessons, False)]
        save_file(self.index_path, index)

    def _process_update(self, t: dict) -> None:
        """Полное обновление расписания, индексов, файла обновлений.

        Args:
            t (dict): Расписание уроков
        """
        logger.info("Start schedule update...")
        now = datetime.now()
        timestamp = datetime.timestamp(now)

        # Скачяиваем файла с расписанием
        try:
            logger.info("Download schedule csv_file")
            csv_file = requests.get(url).content
        except Exception as e:
            logger.exception(e)

            # Откладываем обновление на минуту
            t["next_update"] = timestamp+60
            self.save_file(self.sc_path, t)
        else:
            old_t = t.copy()
            h = hashlib.md5(csv_file).hexdigest()

            # Сравниваем хеши расписаний
            if t.get("hash", "") == h:
                logger.info("Schedule is up to date")
            else:
                t["hash"] = h
                t["lessons"] = parse_lessons(csv_file)
                t["last_parse"] = datetime.timestamp(now)

                self._update_diff_file(old_t, t)
                self._update_index_files(t["lessons"])

            t["next_update"] = timestamp + 1800
            save_file(self.sc_path, t)

    def get(self) -> dict:
        """Получает и запускает процесс обновления расписания.

        Returns:
            dict: Расписание уроков
        """
        now = datetime.timestamp(datetime.now())
        t = load_file(self.sc_path)

        if not t or t.get("next_update", 0) < now:
            self._process_update(t)

        return t


    # Получение данных из расписания
    # ==============================

    def get_class(self, cl: str) -> str:
        """Вовращает введённый класс или класс по умолчанию."""
        return cl if cl in self.lessons else self.cl

    def get_lessons(self, cl: Optional[str] = None) -> dict:
        """Получает расписание уроков на неделю для класса."""
        return self.lessons.get(self.get_class(cl), [[], [], [], [], [], []])

    def get_updates(self, intent: Intent, offset: Optional[int] = None) -> list:
        """Получает список изменений расписания.

        Args:
            intent (Intent): Намерения для уточнения результатов
        """
        updates = []

        for update in self.updates:
            if update is None:
                continue

            if offset is not None and update["end_time"] < offset:
                continue

            new_update = [{} for x in range(6)]
            for day, day_updates in enumerate(update["updates"]):
                if intent.days and day not in intent.days:
                    continue

                for cl, cl_updates in day_updates.items():
                    if intent.cl and cl not in intent.cl:
                        continue

                    new_update[day][cl] = cl_updates

            if sum(map(len, new_update)):
                updates.append({
                    "start_time": update["start_time"],
                    "end_time": update["end_time"],
                    "updates": new_update
                })

        return updates

    def search(self, target: str, intent: Intent,
               cabinets_mode: Optional[bool]=False) -> list:
        """Поиск в расписании.
        Цель (target) Может быть кабинетом или уроком
        Obj, target = lessn -> another = cabinet
        Obj, target = cabinet -> another = lesson

        Args:
            target (str): Цель для поиска
            intent (Intent): Намерения для уточнения результатов
            cabinets_mode (bool, optional): Поиск по кабинетам
        """
        res = [[[] for x in range(8)] for x in range(6)]

        if cabinets_mode:
            days = self.c_index.get(target, {})
        else:
            days = self.l_index.get(target, {})

        for day, objs in enumerate(days):
            if intent.days and day not in intent.days:
                continue

            for obj, another in objs.items():
                if cabinets_mode and intent.lessons and obj not in intent.lessons:
                    continue

                for cl, i in another.items():
                    if intent.cl and cl not in intent.cl:
                        continue

                    for x in i:
                        if len(intent.cabinets) == 1 and len(intent.lessons):
                            res[day][x].append(f"{cl}")
                        elif len(intent.cl) == 1:
                            res[day][x].append(f"{obj}")
                        else:
                            res[day][x].append(f"{cl}:{obj}")
        return res
