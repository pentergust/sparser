"""
Самостоятельный парсер школьного расписания уроков.

Author: Milinuri Nirvalen
Ver: 4.5

Modules:
     csv: Чтение CSV файла расписания
 hashlib: Работа с хеш-суммами
    json: Управление файлами
requests: Загрузка файла расписания
    Path: Проверка существования файла
datetime: Работа с датой и временем
  loguru: Ведение журнала отладки
"""

import csv
import hashlib
import json
import requests

from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import Counter

from loguru import logger


url = "https://docs.google.com/spreadsheets/d/1pP_qEHh4PBk5Rsb7Wk9iVbJtTA11O9nTQbo1JFjnrGU/export?format=csv"
users_path = "sp_data/users.json"
sc_path = "sp_data/sc.json"
sc_updates_path = "sp_data/updates.json"
index_path = "sp_data/index.json"
user_data = {"class_let":"9г", "set_class": False, "last_parse": 0,
             "check_updates": 0}
timetable = [["08:00", "08:45"],
             ["08:55", "09:40"],
             ["09:55", "10:40"],
             ["10:55", "11:40"],
             ["11:50", "12:35"],
             ["12:45", "13:30"],
             ["13:40", "14:25"],
             ["14:35", "15:20"]]

days_names = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу"]


# Управление файлами
# ==================

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



# Вспомогательныек функции отображения
# ====================================

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


class Schedule:
    """Описание расписания уроков и способы взаимодействия с ним."""

    def __init__(self, sc_file: Optional[str] = sc_path,
                updates_file: Optional[str] = sc_updates_path,
                index_path: Optional[str] = index_path):
        super(Schedule, self).__init__()
        self.sc_path = Path(sc_file)
        self.updates_path = Path(updates_file)
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
        sc_changes = load_file(self.updates_path, [None for x in range(15)])

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

    def search(self, target: str) -> dict:
        """Поиск данных в расписании.

        Args:
            target (str): Цель для поиск, кабинет или название урока

        Returns:
            dict: Результаты поиска
        """
        logger.info("Search {} in Schedule", target)
        res = {}
        index = self.c_index if target in self.c_index else self.l_index

        for day, data in enumerate(index.get(target, [])):
            for obj, obj_data in data.items():
                for another, i in obj_data.items():
                    if obj not in res:
                        res[obj] = [[[] for x in range(8)] for x in range(6)]

                    for x in i:
                        res[obj][day][x].append(another)
        return res


class SPMessages:
    """Генератор текстовых сообщений для Schedule."""

    def __init__(self, uid: str, sc: Schedule,
                 users_path: Optional[str] = users_path):
        """
        Args:
            uid (str): Кто пользуется расписанием
            sc (Schedule): Расписание уроков
            users_path (str, optional): Путь к файлу данных пользователей
        """
        super(SPMessages, self).__init__()

        self.uid = uid
        self.sc = sc
        self._users_path = Path(users_path)

        self.user = self.get_user()


    def send_status(self):
        """Возвращает некоторую информауию о парсере."""
        last_parse = datetime.fromtimestamp(self.sc.schedule["last_parse"])
        next_update = datetime.fromtimestamp(self.sc.schedule["next_update"])

        res = "Версия sp: 4.5 (44)"
        res += f"\n:: Участников: {len(load_file(self._users_path))}"
        res += "\n:: Автор: Milinuri Nirvalen (@milinuri)"
        res += f"\n:: Класс: {self.user['class_let']}"
        res += f"\n:: Обновлено: {last_parse.strftime('%d %h в %H:%M')}"
        res += f"\n:: Проверка: {next_update.strftime('%d %h в %H:%M')}"
        res += f"\n:: Предметов: ~{len(self.sc.l_index)}"
        res += f"\n:: Кабинетов: ~{len(self.sc.c_index)}"
        res += f"\n:: Классы: {', '.join(self.sc.lessons)}"

        return res


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
            message = f"✏ Установлен класс {cl}"

        else:
            message = "🔎 Укажите свой класс в формате \"1А\"."
            message += f"\n🏫 Доступные классы: {'; '.join(self.sc.lessons)}"

        return message


    # Получение данных из расписания
    # ==============================

    def get_class(self, cl: str) -> str:
        """Проверяет наличие класса.
        Вовращает введённый класс или класс пользователя."""
        return cl if cl in self.sc.lessons else self.user["class_let"]

    def get_lessons(self, cl: str = "") -> dict:
        """Получает расписание уроков на неделю для класса."""
        return self.sc.lessons[self.get_class(cl)]

    def get_lessons_updates(self) -> set:
        """Возвращает дни, для которых изменилось расписание."""

        # Если расписание не обновилось, значит и хеши дней тоже
        if self.sc.schedule["last_parse"] == self.user["last_parse"]:
            return set()

        logger.info("Get lessons updates")
        updates = load_file(self.sc.updates_path)
        lessons = self.get_lessons()
        days = []

        # Обновление времени последней проверки расписания
        self.user["last_parse"] = self.sc.schedule["last_parse"]
        self.save_user()

        # Пробегаемся по списку измененийй
        for x in updates:
            # Пропускаем изменния, которые мы уже смотрели
            if x is None or x["time"] < self.user["last_parse"]:
                continue

            # Пробеаемся по каждой записи с изменениями
            for day, day_updates in enumerate(x["updates"]):
                if self.user["class_let"] in day_updates:
                    days.append(day)

        return set(days)


    # Отображение расписания
    # ======================

    def send_update(self, update: dict) -> str:
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

    def send_day_lessons(self, today: int, cl: Optional[str] = None) -> str:
        """Сообщение с расписанием уроков на день.

        Args:
            today (int): День недели (0-5)
            cl (str, optional): Для какого класса

        Returns:
            str: Сообщение с расписанием на день
        """
        if today > 5:
            today = 0

        cl = self.get_class(cl)
        lessons = self.get_lessons(cl)[today]
        message = f"\n🔶 На {days_names[today]}:"

        # Собираем сообщение с расписанием
        for i, x in enumerate(lessons):
            tt = ""
            if i < len(timetable):
                tt = f" {timetable[i][0]}"

            message += f"\n{i+1}{tt} | {x}"

        return message

    def send_lessons(self, days: list[int], cl: Optional[str] = None) -> str:
        """Сообщение с расписанием уроков.

        Args:
            day (list[int]): Для каких дней расписание
            cl (str, optional): Для каких классов

        Returns:
            str: Сообение с расписание уроков
        """

        days = set(filter(lambda x: x < 6, days)) or {0}
        cl = self.get_class(cl)
        message = f"🏫 Для {cl}:"

        for day in days:
            message += f"{self.send_day_lessons(day, cl)}\n"

        # Обновления в расписаниии
        # ------------------------

        if self.user["set_class"]:
            updates = self.get_lessons_updates()

            if updates:
                message += f"\n🎉 Изменилось расписание!"

                updates = updates - days
                if len(updates) < 3:
                    for day in updates:
                        message += f"{self.send_day_lessons(day)}\n"
                else:
                    message += f"\nНа {', '.join(map(lambda x: days_names[x], updates))}."

        return message

    def send_today_lessons(self, cl: Optional[str] = "") -> str:
        """Сообщение с расписанием на сегодня/завтра.
        Есои уроки закончились, выводится расписание на завтра.

        Args:
            cl (str, optional): Для какого класса

        Returns:
            str: Сообщыение с расписанием на сегодня/завтра
        """

        now = datetime.now()
        today = min(now.weekday(), 5)
        lessons = self.get_lessons(cl)
        hour = int(timetable[len(lessons[today])-1][1].split(':')[0])

        if now.hour >= hour:
            today += 1

        if today > 5:
            today = 0

        return self.send_lessons([today], cl)

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
            cl = self.get_class(cl)

        index = self.sc.c_index if cabinets else self.sc.l_index
        message = ""
        res = {}

        for obj, days in index.items():
            cnt = Counter()
            for day, another in enumerate(days):
                for a_k, a_v in another.items():
                    if cl:
                        cnt[a_k] += len(a_v.get(cl, []))
                    else:
                        cnt[a_k] += sum(map(len, a_v.values()))

            c = cnt.total()
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


    # Поиск в расписании
    # ==================

    def search_lesson(self, lesson: str, days: Optional[list[int]] = [], cl: Optional[str] = None):
        """Поиск упоминаний об уроке.
        Когда (день), где (кабинет), для кого (класс), каким уроком.

        Args:
            lesson (str): Урок, который нужно найти
            days (list[int], optional): Для каких дней нужно найти
            cl (str, optional): Для какого класса нужно найти

        Returns:
            str: результаты поиска
        """

        if lesson not in self.sc.l_index:
            message = f"❗Неправильно указан предмет."
            message += f"\n🏫 Доступные предметы: {'; '.join(self.sc.l_index)}"
            return message

        if cl is not None:
            cl = self.get_class(cl)

        res = self.sc.search(lesson)
        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))

        # Собираем сообщение
        # ------------------

        search_str = f"🔎 Поиск [{lesson}]"
        if days == {0, 1, 2, 3, 4, 5}:
            search_str += f" за неделю"
        elif days:
            search_str += f" за {', '.join(map(lambda x: days_names[x], days))}"

        if cl:
            search_str += f" для {cl}"

        message = search_str

        # Пробегаемся по результатам поиска
        for cabinet, v in res.items():
            cabinet_str = ""

            # Пробегаемся по указанным дням
            for day in days:
                ln = v[day]
                day_str = ""

                for i, cs in enumerate(ln):
                    if cl and cl not in cs:
                        continue

                    if cs:
                        tt = ""

                        if i < len(timetable):
                            tt = f' {timetable[i][0]}'

                        day_str += f"\n{i+1}{tt}| {', '.join(cs)}"

                if day_str:
                    cabinet_str += f'\n⏰ На {days_names[day]}:{day_str}'
            if cabinet_str:
                message += f"\n\n🔶 Кабинет {cabinet}:{cabinet_str}"

        return message

    def search_cabinet(self, cabinet: str, lesson: Optional[str] = "", days: Optional[list[int]] = [], cl: Optional[str] = None):
        """Поиск упоминаний о кабинете.
        Когда (день), что (урок), для кого (класс), каким уроком.

        :param cabinet: Кабинет, который нужно найти
        :param lesson: Для какого урока отображать результат
        :param days: Для каких дней отображать результат поиска
        :param cl: Для какого класса отображать результаты

        :returns: Сообщение с результатами поиска."""

        if cabinet not in self.sc.c_index:
            message = f"❗Неправильно указан кабинет."
            message += f"\n🏫 Доступные кабинеты: {'; '.join(self,c_index)}"
            return message


        if cl is not None:
            cl = self.get_class(cl)
        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))
        data = self.sc.search(cabinet)

        # Собираем сообщение
        # ------------------

        message = f"🔎 Поиск кабнета [{cabinet}]"
        if days == {0, 1, 2, 3, 4, 5}:
            message += f" за неделю"
        elif days:
            message += f" за {', '.join(map(lambda x: days_names[x], days))}"

        if cl:
            message += f" для {cl}"

        if lesson:
            message += f" ({lesson})"

         # Пробегаемся по результатам поиска
        res = [[[] for x in range(8)] for x in range(6)]
        for l, v in data.items():
            if lesson and lesson != l:
                continue

            # Пробегаемся по указанным дням
            for day in days:
                ln = v[day]

                for i, cs in enumerate(ln):
                    if cl and cl not in cs:
                        continue

                    if cs:
                        res[day][i].append(f"{l}:{', '.join(cs)}")

        for day, lessons in enumerate(res):
            if lessons:
                while lessons:
                    if not lessons[-1]:
                        lessons.pop()
                    else:
                        break

                day_str = ""
                for i, l in enumerate(lessons):
                    tt = ""

                    if i < len(timetable):
                        tt = f'В {timetable[i][0]} '

                    if l:
                        day_str += f"\n{i+1} {tt}| {', '.join(l)}"
                    else:
                        day_str += f"\n{i+1} {tt}| ==="

                if day_str:
                    message += f"\n\n🔶На {days_names[day]}:{day_str}"

        return message
