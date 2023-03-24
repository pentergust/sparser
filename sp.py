"""
Самостоятельный парсер школьного расписания уроков.

Author: Milinuri Nirvalen
Ver: 4.6.3
"""

import csv
import hashlib
import json
import requests

from collections import Counter
from datetime import datetime
from datetime import time
from pathlib import Path
from typing import Any
from typing import Optional

from loguru import logger


url = "https://docs.google.com/spreadsheets/d/1pP_qEHh4PBk5Rsb7Wk9iVbJtTA11O9nTQbo1JFjnrGU/export?format=csv"
users_path = "sp_data/users.json"
sc_path = "sp_data/sc.json"
sc_updates_path = "sp_data/updates.json"
index_path = "sp_data/index.json"
user_data = {"class_let":None, "set_class": False, "last_parse": 0,
             "check_updates": 0}

# Расписание уроков: начало (час, минуты), конец (час, минуты)
timetable = [
    [8, 0, 8, 45],
    [8, 55, 9, 40],
    [9, 55, 10, 40],
    [10, 55, 11, 40],
    [11, 50, 12, 35],
    [12, 45, 13, 30],
    [13, 40, 14, 25],
    [14, 35, 15, 20],
]

days_names = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу"]
days_parts = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]


def save_file(path: Path, data: dict) -> dict:
    """Записывает данные в файл.

    Args:
        path (Path): Путь к файлу для записи
        data (dict): Данные для записи

    Returns:
        dict: Данные для записи
    """

    if not path.exists():
        path.parents[0].mkdir(parents=True, exist_ok=True)

    with open(path, 'w') as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))
    return data

def load_file(path: Path, data: Optional[dict] = {}):
    """Читает данные из файла.

    Args:
        path (Path): Путь к файлу для чтения
        data (dict, optional): Данные для записи при отцуцтвии файла

    Returns:
        dict: Данные из файла/данные для записи
    """

    if path.is_file():
        with open(path) as f:
            return json.loads(f.read())

    elif data is not None:
        return save_file(path, data)

    else:
        return {}


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
    day = 0
    last_row = 8

    logger.info("Read CSV file...")
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
                lessons[k][day-1].append(f"{row[v] or None}:{row[v+1] or 0}")

        elif day == 6:
            logger.info("CSV file reading completed")
            break

    logger.info("cleanup...")
    lessons = {k: list(map(clear_day_lessons, v)) for k, v in lessons.items()}
    return lessons


class Filters:
    """Набор фильтров для получени расписания."""
    def __init__(self, sc, cl: Optional[list] = None,
                 days: Optional[list] = None, lessons: Optional[list] = None,
                 cabinets: Optional[list] = None):
        super(Filters, self).__init__()
        self.sc = sc or []
        self._days = days or []
        self.cl = cl or []
        self.lessons = lessons or []
        self.cabinets = cabinets or []

    @property
    def days(self) -> set:
        return set(filter(lambda x: x < 6, self._days))

    def get_cl(self):
        return self.cl if self.cl else [self.sc.cl]

    def parse_args(self, args: list) -> None:
        weekday = datetime.today().weekday()

        for arg in args:
            if not arg:
                continue

            if arg == "сегодня":
                self._days.append(weekday)

            elif arg == "завтра":
                self._days.append(weekday+1)

            elif arg.startswith("недел"):
                self._days = [0, 1, 2, 3, 4, 5]

            elif arg in self.sc.lessons:
                self.cl.append(arg)

            elif arg in self.sc.l_index:
                self.lessons.append(arg)

            elif arg in self.sc.c_index:
                self.cabinets.append(arg)

            else:
                # Если начало слова совпадает: пятниц... -а, -у, -ы...
                self._days += [i for i, k in enumerate(days_parts) if arg.startswith(k)]


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

    # Пробегаемся по новому расписанию
    updates = [{} for x in range(6)]
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
                    if k not in updates[day]:
                        updates[day][k] = []

                    updates[day][k].append([i, al, l])
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

def clear_empty_list(l: list) -> list:
    while l and not l[-1]:
        del l[-1]
    return l


# Вспомогательныек функции отображения
# ====================================

def get_complited_lessons() -> list[int]:
    """Возвращает номера завершённых уроков."""
    now = datetime.now().time()
    return [i for i, x in enumerate(timetable) if now >= time(x[0], x[1])]

def send_cl_updates(cl_updates: list) -> str:
    """Возвращет сообщение списка изменений для класса.
    В зависимости от изменений вид сообщений немного отличается.

    Args:
        cl_updates (list): Список изменеий для класса

    Returns:
        str: Сообщение с изменениями в расписании для класса
    """
    message = ""
    for u in cl_updates:
        if str(u[1]) == "None":
            message += f"🔹{u[0]} +{u[2]}\n"
            continue

        ol, oc = str(u[1]).split(':')
        l, c = str(u[2]).split(':')

        if ol == "---":
            message += f"🔹{u[0]}: +{u[2]}\n"
        elif l == "---":
            message += f"🔸{u[0]}: -{u[1]}\n"
        elif oc == c:
            message += f"{u[0]}: {ol} -> {l}:{c}\n"
        elif ol == l:
            message += f"{u[0]}: {l}:({oc} -> {c})\n"
        else:
            message += f"{u[0]}: {u[1]} -> {u[2]}\n"

    return message

def send_update(update: dict) -> str:
    """Собирает сообщение со списком изменений в расписании.

    Args:
        update (ТИП): Словарь изменений в расписании
        cl (str, optional): Список изменений для выбранного класса

    Returns:
        ТИП: Готовое сообщение с изменениями в расписании
    """
    t = datetime.fromtimestamp(update["time"]).strftime("%d.%m %H:%M")
    message = f"⏰ Примерно {t}:\n"

    for day, day_updates in enumerate(update["updates"]):
        if not day_updates:
            continue

        message += f"\n🔷 На {days_names[day]}\n"
        for u_cl, cl_updates in day_updates.items():
            message += f"Для {u_cl}:"
            message += "\n" if len(cl_updates) > 1 else " "
            message += send_cl_updates(cl_updates)

    return message

def send_day_lessons(lessons: list) -> str:
    """Собирает сообщение с расписанием уроков на день.

    Args:
        lessons (list): Список уроков на день

    Returns:
        str: Сообщение с расписанием на день
    """

    message = ""
    complited_lessons = get_complited_lessons()

    for i, x in enumerate(lessons):
        message += "\n"
        message += "🔹" if i == complited_lessons[-1] else ''
        message += f"{i+1}."

        tt = timetable[i]
        if i not in complited_lessons:
            message += time(tt[0], tt[1]).strftime(" %H:%M")
        message += time(tt[2], tt[3]).strftime(" - %H:%M")

        if i == complited_lessons[-1]:
            message += " > "
        elif i in complited_lessons:
            message += " ┃ "
        else:
            message += " │ "

        message += "; ".join(x) if isinstance(x, list) else x

    return message

def send_search_res(flt: Filters, res: dict) -> str:
    """Собирает сообщение с результатами поиска в расписании.

    Args:
        flt (Filters): Использованный набор фильстров для уточнения
        res (dict): Результаты поиска в расписании

    Returns:
        str: Готовое сообщение
    """
    message = f"🔎 поиск "
    if flt.cabinets:
        message += f" [{', '.join(flt.cabinets)}]"
    if flt.cl:
        message += f" ({', '.join(flt.cl)})"
    if flt.lessons:
        message += f" ({', '.join(flt.lessons)})"
    if flt.days:
        message += f"\n* На: {', '.join(map(lambda x: days_names[x], flt.days))}"

    for day, lessons in enumerate(res):
        lessons = clear_empty_list(lessons)
        if not lessons:
            continue
        message += f"\n\n📅 На {days_names[day]}:"
        message += send_day_lessons(lessons)

    return message



class Schedule:
    """Описание расписания уроков и способы взаимодействия с ним."""

    def __init__(self, cl: str):
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
        """Получает информацию об уроках в расписании.
        Имена уроков, для кого и когда."""
        if not self._l_index:
            self._l_index = load_file(self.index_path)[0]

        return self._l_index

    @property
    def c_index(self) -> dict:
        """Получает информацию о кабинетах в расписании.
        Какие уроки проводятся, для кого и когда."""
        if not self._c_index:
            self._c_index = load_file(self.index_path)[1]

        return self._c_index

    @property
    def updates(self) -> list:
        """Возврвщает список изменений в расписании."""
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
        sc_changes = load_file(self.updates_path, [None for x in range(30)])

        # Если есть изменения, записываем их
        updates = get_sc_updates(a.get("lessons", {}), b["lessons"])
        if sum(map(len, updates)):
            sc_changes.pop(0)
            sc_changes.append({"time": b["last_parse"], "updates": updates})
            save_file(self.updates_path, sc_changes)

    def _update_index_files(self, sp_lessons: dict) -> None:
        """Обновляет файл индексов.

        Args:
            sp_lessons (dict): Уроки в расписании
        """
        logger.info("Udate index files...")
        index = [get_index(sp_lessons),
                 get_index(sp_lessons, lessons_mode=False)]
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

            t["next_update"] = timestamp + 3600
            save_file(self.sc_path, t)

    def get(self) -> dict:
        """Получает и обновляет расписание.

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

    def get_updates(self, flt: Filters, offset: Optional[int] = None) -> list:
        """Получает список изменений расписания.

        Args:
            flt (Filters): Набор фильтров для уточнения результатов
        """
        updates = []

        for update in self.updates:
            if update is None:
                continue

            if offset is not None and update["time"] < offset:
                continue

            new_update = [{} for x in range(6)]
            for day, day_updates in enumerate(update["updates"]):
                if flt.days and day not in flt.days:
                    continue

                for cl, cl_updates in day_updates.items():
                    if flt.cl and cl not in flt.cl:
                        continue

                    new_update[day][cl] = cl_updates

            if sum(map(len, new_update)):
                updates.append({"time": update["time"], "updates": new_update})

        return updates

    def search(self, target: str, flt: Filters,
               cabinets_mode: Optional[bool]=False) -> list:
        """Поиск в расписании.
        Цель (target) Может быть кабинетом или уроком
        Obj, target = lessn -> another = cabinet
        Obj, target = cabinet -> another = lesson

        Args:
            target (str): Цель для поиска
            flt (Filters): Набор фильтров для уточнения поиска
            cabinets_mode (bool, optional): Поиск по кабинетам
        """
        res = [[[] for x in range(8)] for x in range(6)]

        if cabinets_mode:
            days = self.c_index.get(target, {})
        else:
            days = self.l_index.get(target, {})


        for day, objs in enumerate(days):
            if flt.days and day not in flt.days:
                continue

            for obj, another in objs.items():
                if cabinets_mode and flt.lessons and obj not in flt.lessons:
                    continue

                for cl, i in another.items():
                    if flt.cl and cl not in flt.cl:
                        continue

                    for x in i:
                        if flt.lessons:
                            res[day][x].append(f"{cl}")
                        elif flt.cl:
                            res[day][x].append(f"{obj}")
                        else:
                            res[day][x].append(f"{cl}: {obj}")

        return res


class SPMessages:
    """Генератор текстовых сообщений для Schedule."""

    def __init__(self, uid: str):
        """
        Args:
            uid (str): Кто пользуется расписанием
            sc (Schedule): Расписание уроков
            users_path (str, optional): Путь к файлу данных пользователей
        """
        super(SPMessages, self).__init__()

        self.uid = uid
        self._users_path = Path(users_path)
        self.user = self.get_user()
        self.sc = Schedule(self.user["class_let"])


    def send_status(self):
        """Возвращает некоторую информауию о парсере."""
        last_parse = datetime.fromtimestamp(self.sc.schedule["last_parse"])
        next_update = datetime.fromtimestamp(self.sc.schedule["next_update"])

        res = "Версия sp: 4.6.3 (57)"
        res += f"\n:: Пользователей: {len(load_file(self._users_path))}"
        res += "\n:: Автор: Milinuri Nirvalen (@milinuri)"
        res += f"\n:: Класс: {self.user['class_let']}"
        res += f"\n:: Обновлено: {last_parse.strftime('%d %h в %H:%M')}"
        res += f"\n:: Проверка: {next_update.strftime('%d %h в %H:%M')}"
        res += f"\n:: Предметов: ~{len(self.sc.l_index)}"
        res += f"\n:: Кабинетов: ~{len(self.sc.c_index)}"
        res += f"\n:: Классы: {', '.join(self.sc.lessons)}"

        return res

    def send_users_stats(self) -> str:
        """Отправяет сллюзегте с информацией о пользователях.

        Returns:
            str: Сообщение с информацией о пользователях
        """
        now = datetime.timestamp(datetime.now())
        users = load_file(self._users_path)

        # Сбор статистики о пользователях
        active_cnt = Counter()
        users_cnt = Counter()
        for k, v in users.items():
            users_cnt[v["class_let"]] += 1

            # Активным считается пользователь, у которого время
            # последнего запроса расписания не позднее трёх суток
            if now - v["last_parse"] > 259200:
                continue

            active_cnt[v["class_let"]] += 1


        # Сборка сообщения
        # ----------------

        message = f"✨ Всего пользователей {len(users)}:"
        active_users = sum(active_cnt.values())
        active_users_pr = round(active_users / len(users) * 100, 2)
        message += f"\n💡 Из них активны: {active_users} [{active_users_pr}%]\n"
        for i, item in enumerate(active_cnt.most_common()):
            k, v = item

            if i+1 == 1:
                pos = "🥇"
            elif i+1 == 2:
                pos = "🥈"
            elif i+1 == 3:
                pos = "🥉"
            else:
                pos = f"{i+1}. "

            upr = round(v / active_users * 100, 2)
            apr = round(v / users_cnt[k] * 100, 2)
            apr_str = f" ({apr}%)" if apr < 90 else ""
            message += f"\n{pos}{k} [{upr}%]: {v}/{users_cnt[k]}{apr_str}"

        message += "\n\n❄️ Неактивные пользователи:\n"
        inactive_users = users_cnt - active_cnt
        for k, v in inactive_users.most_common():
            message += f" {k}:{v}"
        return message


    # Управление данными пользователя
    # ===============================

    def get_user(self) -> dict:
        """Возвращает данные пользователя или данные по умолчанию."""
        return load_file(self._users_path).get(self.uid, user_data)

    def save_user(self) -> None:
        """Записывает данные пользователя в self._users_path."""
        users = load_file(self._users_path, {})
        users.update({self.uid: self.user})
        save_file(self._users_path, users)
        logger.info("Save user: {}", self.uid)

    def set_class(self, cl: str) -> str:
        """Изменяет класс пользователя.

        Args:
            cl (str): Целевой класс пользователя

        Returns:
            str: Сообщение с результатом работы
        """

        if cl in self.sc.lessons:
            self.user["class_let"] = cl
            self.user["set_class"] = True
            self.user["last_parse"] = self.sc.schedule["last_parse"]
            self.save_user()
            message = f"✏ Записан класс: {cl}"
        else:
            message = "🔎 Укажите класс в формате \"1А\"."
            message += f"\n🏫 Доступные классы: {'; '.join(self.sc.lessons)}"

        return message

    def get_lessons_updates(self) -> list:
        """Возвращает дни, для которых изменилось расписание."""
        if self.sc.schedule["last_parse"] == self.user["last_parse"]:
            return []

        logger.info("Get lessons updates")
        flt = Filters(self.sc, cl= [self.user["class_let"]])
        updates = self.sc.get_updates(flt, self.user["last_parse"])

        # Обновление времени последней проверки расписания
        self.user["last_parse"] = self.sc.schedule["last_parse"]
        self.save_user()

        return updates


    # Отображение расписания
    # ======================

    def send_lessons(self, flt: Filters) -> str:
        """Собирает сообщение с расписанием уроков.

        Args:
            flt (Filters): Набор фильтров для уточнения

        Returns:
            str: Сообение с расписание уроков
        """
        lessons = {x: self.sc.get_lessons(x) for x in flt.get_cl()}
        message = ""
        for day in flt.days:
            message += f"\n📅 На {days_names[day]}:"
            for cl, cl_lessons in lessons.items():
                message += f"\n🔶 Для {cl}:"
                message += f"{send_day_lessons(cl_lessons[day])}"
            message += "\n"

        # Обновления в расписаниии
        if self.user["class_let"] in flt.get_cl():
            updates = self.get_lessons_updates()

            if updates:
                message += f"\nИзменилось расписание! 🎉"
                for update in updates:
                    message += f"\n{send_update(update)}"

        return message

    def send_today_lessons(self, flt: Filters) -> str:
        """Сообщение с расписанием на сегодня/завтра.
        Есои уроки закончились, выводится расписание на завтра.

        Args:
            cl (str, optional): Для какого класса

        Returns:
            str: Сообщыение с расписанием на сегодня/завтра
        """

        now = datetime.now()
        today = min(now.weekday(), 5)
        lessons = max(map(lambda x: len(self.sc.get_lessons(x)), flt.get_cl()))
        hour = timetable[lessons-1][2]

        if now.hour >= hour:
            today += 1

        if today > 5:
            today = 0

        flt._days = [today]
        return self.send_lessons(flt)

    def search_lesson(self, lesson: str, flt: Filters) -> str:
        """Поиск упоминаний об уроке.
        Когда (день), где (кабинет), для кого (класс), каким уроком.
        Оставлена для обратной совместимости.

        Args:
            lesson (str): Урок, который нужно найти
            flt (Filters): Набор фильтров для уточнения результатов

        Returns:
            str: результаты поиска
        """
        res = self.sc.search(lesson, flt)
        return send_search_res(flt, res)

    def search_cabinet(self, cabinet: str, flt: Filters) -> str:
        """Поиск упоминаний о кабинете.
        Когда (день), что (урок), для кого (класс), каким уроком.
        Оставлена для обратной совместимости.

        Args:
            cabinet (str): Кабинет, который нужно найти
            flt (Filters): Набор фильтров для уточнения результатов

        Returns:
            str: Сообщение с результатами поиска
        """

        res = self.sc.search(cabinet, flt, cabinets_mode=True)
        return send_search_res(flt, res)


    def count_lessons(self, cabinets: Optional[bool] = False, cl: Optional[str] = None) -> str:
        """Подсчитывает число уроков/кабинетов.

        Args:
            cabinets (bool, optional): Подсчитывать кабинеты
                вместо уроков
            cl (str, optional): Для какого класса произвести подсчёт

        Returns:
            str: Сообщение с результатами
        """
        if cl:
            cl = self.sc.get_class(cl)

        index = self.sc.c_index if cabinets else self.sc.l_index
        res = {}

        for obj, days in index.items():
            cnt = Counter()
            for day, another in enumerate(days):
                for a_k, a_v in another.items():
                    if cl:
                        cnt[a_k] += len(a_v.get(cl, []))
                    else:
                        cnt[a_k] += sum(map(len, a_v.values()))

            c = sum(cnt.values())
            if c:
                if str(c) not in res:
                    res[str(c)] = {}

                res[str(c)][obj] = cnt


        # Собираем сообщение
        # ------------------

        message = "✨ Самые частые "
        if cabinets:
            message += "кабинеты"
        else:
            message += "уроки"

        if cl:
            message += f" у {cl}"


        for k, v in sorted(res.items(), key=lambda x: int(x[0]), reverse=True):
            message += f"\n\n🔘 {k} раз(а):"

            for obj, another in v.items():
                another = {k:v for k, v in another.items() if v != 0}

                if len(v) > 1:
                    message += "\n--"

                message += f" {obj}"

                for c, n in sorted(another.items(), key=lambda x: x[1], reverse=True):
                    if n == 1 and len(another) > 1:
                        message += f" 🔸{c}"
                    elif n > 1 and len(another) > 1:
                        message += f" 🔹{c}:{n}"
                    else:
                        message += f" {c}"

        return message
