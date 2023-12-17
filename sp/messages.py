"""
Генератор текстовых сообщений с использованием Schedule.

Author: Milinuri Nirvalen
"""

from .intents import Intent
from .utils import load_file
from .utils import save_file
from .utils import plural_form
from .utils import check_keys
from .utils import get_str_timedelta
from .parser import Schedule
from .counters import reverse_counter

from collections import Counter
from collections import defaultdict
from datetime import datetime
from datetime import time
from pathlib import Path
from typing import Optional

from loguru import logger


users_path = "sp_data/users.json"
default_user_data = {"class_let":None, "set_class": False, "last_parse": 0,
             "join_date": 0, "notifications": True, "hours": []}
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
    for i, u in enumerate(cl_updates):
        if u is None:
            continue

        if str(u[0]) == "None":
            message += f"{i+1}: ++{u[1]}\n"
            continue

        message += f"{i+1}: "
        ol, oc = str(u[0]).split(':')
        l, c = str(u[1]).split(':')

        if ol == "---":
            message += f"++{u[1]}\n"
        elif l == "---":
            message += f"--{u[0]}\n"
        elif oc == c:
            message += f"{ol} ➜ {l}:{c}\n"
        elif ol == l:
            message += f"{l}: ({oc} ➜ {c})\n"
        else:
            message += f"{u[0]} ➜ {u[1]}\n"

    return message

def get_update_header(update: dict, extend_info: Optional[bool]=True) -> str:
    """Возвращает заголовок списка изменений.

    Args:
        update (dict): Словарь с обновлением в расписании.
        extend_info (bool): Отображать ли дополниельную информацию.

    Returns:
        str: Заголовок списка изменений.
    """

    # Получаем timestamp обновления
    end_timestamp = update.get("end_time", 0)
    start_timespamp = update.get("start_time", end_timestamp)
    etime = datetime.fromtimestamp(end_timestamp)
    stime = datetime.fromtimestamp(start_timespamp)
    message = f"📀 {stime.strftime('%d.%m %H:%M')} "

    t = etime.strftime("%d.%m %H:%M" if stime.day != etime.day else "%H:%M")
    message += f"➜ {t}"

    if extend_info:
        update_delta = end_timestamp - start_timespamp
        now_delta = datetime.now().timestamp() - end_timestamp
        extend_message = ""

        if update_delta <= 172800:
            extend_message += f"🗘 {get_str_timedelta(update_delta, hours=True)}"

        if now_delta <= 86400:
            extend_message += f" ⭯ {get_str_timedelta(now_delta, hours=True)}"

        if extend_message:
            message += f" [{extend_message}]"

    return message



def send_update(update: dict, cl: Optional[str]=None) -> str:
    """Собирает сообщение со списком изменений в расписании.

    Args:
        update (dict): Словарь изменений в расписании
        cl (str, optional): Не отображать заголовок для класса

    Returns:
        str: Готовое сообщение с изменениями в расписании
    """
    message = get_update_header(update)
    for day, day_updates in enumerate(update["updates"]):
        if not day_updates:
            continue

        message += f"\n🔷 На {days_names[day]}"
        for u_cl, cl_updates in day_updates.items():
            if cl is None or cl is not None and cl != u_cl:
                message += f"\n🔸 Для {u_cl}:"

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
        cursor = "➜" if i == complited_lessons[-1] else f"{i+1}."
        message += f"\n{cursor}"

        tt = timetable[i]
        if i not in complited_lessons:
            message += time(tt[0], tt[1]).strftime(" %H:%M -")
        message += time(tt[2], tt[3]).strftime(" %H:%M")

        if i in complited_lessons:
            message += " ┃ "
        else:
            message += " │ "

        message += "; ".join(x) if isinstance(x, list) else x

    return message

def send_search_res(intent: Intent, res: list) -> str:
    """Собирает сообщение с результатами поиска в расписании.

    Args:
        intent (Intent): Намерения для уточнения результатов
        res (dict): Результаты поиска в расписании

    Returns:
        str: Готовое сообщение
    """

    message = f"🔎 поиск "
    if intent.cabinets:
        message += f" [{', '.join(intent.cabinets)}]"
    if intent.cl:
        message += f" ({', '.join(intent.cl)})"
    if intent.lessons:
        message += f" ({', '.join(intent.lessons)})"

    for day, lessons in enumerate(res):
        while lessons and not lessons[-1]:
            del lessons[-1]

        if not lessons:
            continue

        message += f"\n\n📅 На {days_names[day]}:"
        message += send_day_lessons(lessons)

    return message

def send_counter(groups: dict, target: Optional[str]=None) -> str:
    """Возвращает сообщение с результами работы счётчика.

    Args:
        groups (dict): Сгруппированные резульаты работы счётчика
        target (str, optional): Вторичный ключ для отображения

    Returns:
        str: Сообщение с результатами работы счётчика
    """
    message = ""

    for group, res in sorted(groups.items(), key=lambda x: x[0], reverse=True):
        group_plural_form = plural_form(group, ["раз", "раза", "раз"])
        message += f"\n🔘 {group} {group_plural_form}:"

        if target is not None:
            for obj, cnt in res.items():
                if len(res) > 1:
                    message += "\n--"

                message += f" {obj}:"
                cnt_groups = reverse_counter(cnt.get(target, {}))

                for cnt_group, k in sorted(cnt_groups.items(),
                                    key=lambda x: x[0], reverse=True):
                    if cnt_group == 1:
                        message += f" 🔸{' '.join(k)}"
                    elif cnt_group == group:
                        message += f" 🔹{' '.join(k)}"
                    else:
                        message += f" 🔹{cnt_group}:{' '.join(k)}"

            message += "\n"

        else:
            message += f" {', '.join(res)}"

    return message


# Вспомогательные функции для сообщения статуса парсера
# =====================================================

def get_next_update_str(time: datetime, now: Optional[datetime]=None) -> str:
    if now is None:
        now = datetime.now()

    if now.day == time.day:
        res = time.strftime("в %H:%M")
    else:
        res = time.strftime("%d %h в %H:%M")

    return res

def get_cl_counter_str(cl_counter: Counter) -> str:
    groups = defaultdict(list)
    for k, v in cl_counter.items():
        groups[v].append(k)

    res = ""
    for k, v in sorted(groups.items(), key=lambda x: int(x[0])):
        res += f" 🔹{k} ({', '.join(sorted(map(str, v)))})"

    return res


class SPMessages:
    """Генератор текстовых сообщений для Schedule."""

    def __init__(self, uid: str, user_data: Optional[dict]=None) -> None:
        """
        Args:
            uid (str): Кто пользуется расписанием
            sc (Schedule): Расписание уроков
            users_path (str, optional): Путь к файлу данных пользователей
        """
        super(SPMessages, self).__init__()

        self.uid = uid
        self._users_path = Path(users_path)
        self.user = self.get_user(user_data)
        self.sc = Schedule(self.user["class_let"])
        self.user_intent = Intent.construct(
            self.sc, cl=self.user["class_let"]
        )

    def send_status(self) -> str:
        """Возвращает некоторую информауию о парсере."""
        now = datetime.now()
        next_update = datetime.fromtimestamp(self.sc.schedule["next_update"])
        last_parse = datetime.fromtimestamp(self.sc.schedule["last_parse"])

        nu_str = get_next_update_str(next_update, now)
        lp_str = get_next_update_str(last_parse, now)

        nu_delta = get_str_timedelta((next_update - now).seconds, False)
        lp_delta = get_str_timedelta((now - last_parse).seconds)

        cl_counter = Counter()
        notify_count = 0
        active_users = 0
        users = load_file(self._users_path, {})
        for k, v in users.items():
            if v["last_parse"] == self.sc.schedule["last_parse"]:
                active_users += 1
            if v.get("notifications") and v.get("set_class"):
                notify_count += 1
            cl_counter[v["class_let"]] += 1

        active_pr = round(active_users/len(users)*100, 2)

        res = "🌟 Версия sp: 5.7 +8b (110)"
        res += "\n\n🌲 Разработчик: Milinuri Nirvalen (@milinuri)"
        res += f"\n🌲 [{nu_delta}] {nu_str} проверено"
        res += f"\n🌲 {lp_str} обновлено ({lp_delta} назад)"
        res += f"\n🌲 {len(users)} пользователей ({notify_count}🔔)"
        res += f"\n🌲 из них {active_users} активны ({active_pr}%)"
        res += f"\n🌲 {self.user['class_let']} класс"
        res += f"\n🌲 ~{len(self.sc.l_index)} пр. ~{len(self.sc.c_index)} каб."
        res += f"\n🌲 {get_cl_counter_str(cl_counter)}"

        other_cl = sorted(set(self.sc.lessons) - set(cl_counter))
        if other_cl:
            res += f" 🔸{', '.join(other_cl)}"

        return res


    # Управление данными пользователя
    # ===============================

    def get_user(self, user_data: Optional[dict]=None) -> dict:
        """Возвращает данные пользователя или данные по умолчанию.

        Args:
            user_data (dict): Переданный данные пользователя.

        Returns:
            dict: Данные пользователя
        """

        if user_data is None:
            user_data = load_file(self._users_path).get(self.uid)
            if user_data is None:
                return default_user_data.copy()

        return check_keys(user_data, default_user_data)

    def save_user(self) -> None:
        """Записывает данные пользователя в self._users_path."""
        users = load_file(self._users_path, {})
        users.update({self.uid: self.user})
        save_file(self._users_path, users)
        logger.info("Save user: {}", self.uid)

    def reset_user(self) -> None:
        """ЦУдаляет даныне о пользователе"""
        users = load_file(self._users_path, {})
        users.update({self.uid: default_user_data.copy()})
        save_file(self._users_path, users)
        logger.info("Reset user: {}", self.uid)

    def set_class(self, cl: str | None) -> bool:
        """Изменяет класс пользователя.

        Args:
            cl (str): Целевой класс пользователя
        """
        if cl is None or cl in self.sc.lessons:
            self.user["join_date"] = datetime.now().timestamp()
            self.user["class_let"] = cl
            self.user["set_class"] = True
            self.user["last_parse"] = self.sc.schedule["last_parse"]
            self.save_user()
            return True
        else:
            return False

    def get_lessons_updates(self) -> list:
        """Возвращает дни, для которых изменилось расписание."""
        if self.user["class_let"] is None:
            return []

        if self.sc.schedule["last_parse"] <= self.user["last_parse"]:
            return []

        logger.info("Get lessons updates")
        updates = self.sc.get_updates(self.user_intent, self.user["last_parse"])

        # Обновление времени последней проверки расписания
        self.user["last_parse"] = self.sc.schedule["last_parse"]+1
        self.save_user()
        return updates


    # Отображение расписания
    # ======================

    def send_lessons(self, intent: Intent) -> str:
        """Собирает сообщение с расписанием уроков.

        Args:
            intent (Intent): Намерения для уточнения расписания

        Returns:
            str: Сообщение с расписание уроков
        """

        cl = intent.cl or (self.user["class_let"],)
        lessons = {x: self.sc.get_lessons(x) for x in cl}
        message = ""
        for day in intent.days:
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
                message += f"\n{send_update(update, cl)}"
        return message

    def send_today_lessons(self, intent: Intent) -> str:
        """Сообщение с расписанием на сегодня/завтра.
        Если уроки закончились, отправляется расписание на завтра.

        Args:
            intent (Intent): Намерения для уточнения расписания

        Returns:
            str: Сообщение с расписанием на сегодня/завтра
        """

        now = datetime.now()
        today = now.weekday()

        if today == 6:
            today = 0
        else:
            cl = intent.cl or (self.user["class_let"],)
            max_lessons = max(map(lambda x: len(self.sc.get_lessons(x)), cl))
            hour = timetable[max_lessons-1][2]

            if now.hour >= hour:
                today += 1

            if today > 5:
                today = 0

        return self.send_lessons(intent.reconstruct(self.sc, days=today))
