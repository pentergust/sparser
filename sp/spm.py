"""
Генератор текстовых сообщений с использованием Schedule.

Auyhor: Milinuri Nirvalen
"""
from .filters import Filters
from .filters import construct_filters
from .utils import load_file
from .utils import save_file
from .parser import Schedule

from collections import Counter
from datetime import datetime
from datetime import time
from pathlib import Path
from typing import Optional

from loguru import logger


users_path = "sp_data/users.json"
default_user_data = {"class_let":None, "set_class": False, "last_parse": 0,
             "check_updates": 0}
days_names = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу"]

# Расписание уроков: начало (час, минуты), конец (час, минуты)
timetable = [
    [8, 0, 8, 45], [8, 55, 9, 40], [9, 55, 10, 40], [10, 55, 11, 40],
    [11, 50, 12, 35], [12, 45, 13, 30], [13, 40, 14, 25], [14, 35, 15, 20],
]


# Вспомогательныек функции отображения
# ====================================

def get_complited_lessons() -> list[int]:
    """Возвращает номера завершённых уроков."""
    now = datetime.now().time()
    first_lesson = time(*timetable[0][:1])
    last_lesson = time(*timetable[-1][2:])

    if now >= last_lesson or now < first_lesson:
        return [-1]

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
            message += f"{u[0]}: ++{u[2]}\n"
            continue

        message += f"{u[0]}: "
        ol, oc = str(u[1]).split(':')
        l, c = str(u[2]).split(':')

        if ol == "---":
            message += f"++{u[2]}\n"
        elif l == "---":
            message += f"--{u[1]}\n"
        elif oc == c:
            message += f"{ol} -> {l}:{c}\n"
        elif ol == l:
            message += f"{l}: ({oc} -> {c})\n"
        else:
            message += f"{u[1]} -> {u[2]}\n"

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
            message += f"🔸 Для {u_cl}:"
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
        cursor = "🔹" if i == complited_lessons[-1] else f"{i+1}."
        message += f"\n{cursor}"

        tt = timetable[i]
        if i not in complited_lessons:
            message += time(tt[0], tt[1]).strftime(" %H:%M -")
        message += time(tt[2], tt[3]).strftime(" %H:%M")

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
        if not lessons:
            continue

        while lessons and not lessons[-1]:
            del lessons[-1]

        message += f"\n\n📅 На {days_names[day]}:"
        message += send_day_lessons(lessons)

    return message


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

        res = "Версия sp: 5.1-Beta (63)"
        res += f"\n:: Пользователей: {len(load_file(self._users_path))}"
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
        return load_file(self._users_path).get(self.uid, default_user_data)

    def save_user(self) -> None:
        """Записывает данные пользователя в self._users_path."""
        users = load_file(self._users_path, {})
        users.update({self.uid: self.user})
        save_file(self._users_path, users)
        logger.info("Save user: {}", self.uid)

    def reset_user(self) -> None:
        """ЦУдаляет даныне о пользователе"""
        users = load_file(self._users_path, {})
        users.update({self.uid: default_user_data})
        save_file(self._users_path, users)
        logger.info("Reset user: {}", self.uid)

    def set_class(self, cl: str) -> None:
        """Изменяет класс пользователя.

        Args:
            cl (str): Целевой класс пользователя
        """
        if cl in self.sc.lessons:
            self.user["class_let"] = cl
            self.user["set_class"] = True
            self.user["last_parse"] = self.sc.schedule["last_parse"]
            self.save_user()

    def get_lessons_updates(self) -> list:
        """Возвращает дни, для которых изменилось расписание."""
        if self.sc.schedule["last_parse"] == self.user["last_parse"]:
            return []

        logger.info("Get lessons updates")
        flt = construct_filters(self.sc, cl=self.user["class_let"])
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
        cl = flt.cl or [self.user["class_let"]]
        lessons = {x: self.sc.get_lessons(x) for x in cl}
        message = ""
        for day in flt.days:
            message += f"\n📅 На {days_names[day]}:"
            for cl, cl_lessons in lessons.items():
                message += f"\n🔶 Для {cl}:"
                message += f"{send_day_lessons(cl_lessons[day])}"
            message += "\n"

        # Обновления в расписаниии
        updates = self.get_lessons_updates()
        if updates:
            message += f"\nУ вас изменилось расписание! 🎉"
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
        cl = flt.cl or [self.user["class_let"]]
        lessons = max(map(lambda x: len(self.sc.get_lessons(x)), cl))
        hour = timetable[lessons-1][2]

        if now.hour >= hour:
            today += 1

        if today > 5:
            today = 0

        flt = construct_filters(self.sc, cl=flt.cl, days=today)
        return self.send_lessons(flt)

    def search_lesson(self, lesson: str, flt: Filters) -> str:
        """Поиск упоминаний об уроке. Для обратной совместимости."""
        res = self.sc.search(lesson, flt)
        return send_search_res(flt, res)

    def search_cabinet(self, cabinet: str, flt: Filters) -> str:
        """Поиск упоминаний о кабинете. Для обратной совместимости."""
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
