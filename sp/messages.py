"""Генератор текстовых сообщений с использованием Schedule.

Преобразует "сырые" результаты работы методов класса Schedule
в тексовые сообщения, которые могут использваоться в чат ботах.
Например Telegram и Вконтакте.
"""

from collections import Counter, defaultdict
from datetime import datetime, time
from pathlib import Path
from typing import Any, NamedTuple, Optional, Union

from loguru import logger

from .counters import CounterTarget, reverse_counter
from .intents import Intent
from .parser import Schedule
from .utils import (check_keys, compact_updates, get_str_timedelta, load_file,
                    plural_form, save_file)

# Некоторые настройки генератора сообщений
# ========================================

users_path = "sp_data/users.json"
default_user_data = {"class_let":None, "set_class": False, "last_parse": 0,
             "join_date": 0, "notifications": True, "hours": []}
DAYS_NAMES = [
    "понедельник", "вторник", "среду", "четверг", "пятницу", "субботу"
]
_SHORT_DAYS_NAMES = ["пн", "вт", "ср", "чт", "пт", "сб"]

_EMPTY_LESSONS = ("---", "None")
# Максимальные обображаемый диапазон временного промежутка (2 дня)
_UPDATE_DELTA = 172800
# Массимальное отображамое прошедшее время обновления (24 часа)
_MAX_UPDATE_SINCE = 86400


# Расписание уроков: начало (час, минуты), конец (час, минуты)
# Расписание звонков с понедельника (22.01) и  до конца уч. года.
# 1. 8.00-8.45
# 2. 8.50-9.35
# 3. 9.50-10.35
# 4. 10.50-11.35
# 5. 11.50-12.35
# 6. 12.45-13.30
# 7. 13.40-14.25
# TODO: Написать класс для рабоыт с расписанием звонков

timetable = [
    [8, 0, 8, 45], [8, 50, 9, 35], [9, 50, 10, 35], [10, 50, 11, 35],
    [11, 50, 12, 35], [12, 45, 13, 30], [13, 40, 14, 25], [14, 35, 15, 20],
]


# Вспомогательныек функции отображения
# ====================================

class LessonTime(NamedTuple):
    """Описывает время начала и конца урока.

    Этот фрагмент должен был стать частью будущего обновления.
    Данные фрагмен будет переписан со врменем.
    Используется для более детального отображения укзаателя на
    текущий урокю

    :param start: Время начала урока.
    :type start: time
    :oaram end: Время окончания урока.
    :type end: time
    :param index: Порядковый номер текущего урока.
    :type index: int
    """

    start: time
    end: time
    index: int

def time_to_seconds(now: time) -> int:
    """Переводит datetime.time в полное количество секунд."""
    return now.hour * 3600 + now.minute * 60 + now.second

def seconds_to_time(now: int) -> time:
    """Переводит полное количество секунд в datetime.time."""
    h, d = divmod(now, 3600)
    m, s = divmod(d, 60)
    return time(h, m, s)

def get_current_lesson(now: time) -> Optional[LessonTime]:
    """Возаращет текущий урок.

    Если пары ещё не начались или уже кончились -> None.
    Если время между пар -> Специальная пара "перерыв".

    :return: Текущий урок, если он есть.
    :rtype: LessonTime | None
    """
    l_end_time = None
    for i, lesson in enumerate(timetable):
        start_time = time(lesson[0], lesson[1])
        end_time = time(lesson[2], lesson[3])

        if l_end_time is not None and now >= l_end_time and now < start_time:
            return LessonTime(l_end_time, start_time, i)
        elif now >= start_time and now < end_time:
            return LessonTime(start_time, end_time, i)

        l_end_time = end_time


# Функции отображения списка изменений
# ====================================

def send_cl_updates(
    cl_updates: list[Optional[list[str]]]
) -> str:
    """Возвращет сообщение списка изменений для класса.

    В зависимости от типа изменений вид сообщений немного отличается.

    **Условные обозначения**:

    - `{l}` - Название урока.
    - `{c}` - Кабнет урока.
    - `{ol}` - Название урока до изменений.
    - `{oc}` - Кабнет урока до изменений.

    **Типы сообщений**:

    - `++{ol}:{oc}` - Добавлися урок в расписания.
    - `--{ol}:{oc}` - Урок убран из расписания.
    - `{ol} -> {l}:{c}` - Если сменился только урок, без кабинета.
    - `{l}:({oc} -> {c})` - Если сменился только кабинет, без урока.
    - `{ol}:{oc} -> {l}:{c}` - Остальные случаи.

    :param cl_updates: Список изменений для класса.
    :type cl_updates: list[Optional[list[str]]]
    :return: Сообщение со списком изменений класса.
    :rtype: str
    """
    message = ""
    for i, u in enumerate(cl_updates):
        if u is None:
            continue

        # Если сиапый урок не был выбран
        if str(u[0]) == "None":
            message += f"{i+1}: ++{u[1]}\n"
            continue

        message += f"{i+1}: "
        ol, oc = str(u[0]).split(':')
        l, c = str(u[1]).split(':') # noqa: E741

        # Если добавился урок в расписание
        if ol in _EMPTY_LESSONS:
            message += f"++{u[1]}\n"
        # Если урок удалился
        elif l in _EMPTY_LESSONS:
            message += f"--{u[0]}\n"
        # Если в расписании изменился только урок
        elif oc == c:
            message += f"{ol} ➜ {l}:{c}\n"
        # Если сменился только урок, без кабинета
        elif ol == l:
            message += f"{l}: ({oc} ➜ {c})\n"
        else:
            message += f"{u[0]} ➜ {u[1]}\n"

    return message

def get_update_header(
    update: dict[str, Union[int, dict]],
    exstend_info: Optional[bool]=True
) -> str:
    """Возвращает заголовок списка изменений.

    Собирает диноммический заголовок о списке записи изменений.

    Запись об изменениях представляет собой временной промежуток
    в пределах которого были зафиксированы некоторые изменения в
    расписании.

    **Пример заголовка**:

    > 16.02 23:37 ➜ 18.02 19:49 [🗘 44:12:02]

    **Заголовок изменений содержит**:

    - Дата начала временного промежутка.
    - Дата окончания временного промежутка.
    - Полное время временного промежутка.
    - (опционально) сколько времени прошло с окончания записи.

    полное время временног промежутка, а также время прошедшее с
    момента записи являются расширенными опциональными параметрами.

    :param update: Словарь данными записи.
    :type update: dict[str, Union[int, dict]]
    :param exstend_info: Показывать ли дополнительны информацию в шапке.
    :type exstend_info: Optional[bool]
    :return: Заголовок списка изменений.
    :rtype: str
    """
    # Получаем timestamp обновления
    end_timestamp = update.get("end_time", 0)
    start_timespamp = update.get("start_time", end_timestamp)
    etime = datetime.fromtimestamp(end_timestamp)
    stime = datetime.fromtimestamp(start_timespamp)
    message = f"📀 {stime.strftime('%d.%m %H:%M')} "

    t = etime.strftime("%d.%m %H:%M" if stime.day != etime.day else "%H:%M")
    message += f"➜ {t}"

    if exstend_info:
        update_delta = int(end_timestamp - start_timespamp)
        now_delta = int(datetime.now().timestamp() - end_timestamp)
        extend_message = ""

        if update_delta <= _UPDATE_DELTA:
            extend_message += f"🗘 {get_str_timedelta(update_delta, hours=True)}"

        if now_delta <= _MAX_UPDATE_SINCE:
            extend_message += f" ⭯ {get_str_timedelta(now_delta, hours=True)}"

        if extend_message:
            message += f" [{extend_message}]"

    return message

def send_update(
    update: dict[str, Union[int, list[dict]]],
    cl: Optional[str]=None) -> str:
    """Собирает сообщение со списком изменений в расписании.

    Собирает сообщение из записи об измении в расписании.

    Пример сообщения со списком изменений:


    :param update: Запись об изменении в расписании.
    :type update: dict[str, Union[int, list[dict]]]
    :param cl: Упоминание какого класса опускать в заголовке.
    :type cl: Optional[str]
    :return: Сообщение со списком изменений в расписании.
    :rtype: str
    """
    message = get_update_header(update)
    for day, day_updates in enumerate(update["updates"]):
        if not day_updates:
            continue

        message += f"\n🔷 На {DAYS_NAMES[day]}"
        for u_cl, cl_updates in day_updates.items():
            if cl is None or cl is not None and cl != u_cl:
                message += f"\n🔸 Для {u_cl}:"

            message += "\n" if len(cl_updates) > 1 else " "
            message += send_cl_updates(cl_updates)

    return message


# Вспомогательные функции отображения
# ===================================

def send_day_lessons(lessons: list[Union[list[str], str]]) -> str:
    """Собирает сообщение с расписанием уроков на день.

    Возаращает сообещния со списком уроков на день.
    Помимо списка уроков укзаывает какие уроки прошли и какие ещё
    буду, а также указатель на текущий урок и время начала и конца
    уроков.

    Также можно преедавать несколько кроуов в расписании.
    Это может использоваться чтобы при просмотре результатов поиска
    в расписании.


    :param lessons: Список уроков.
    :type lessons: list[Union[list[str], str]]
    :return: Сообщение с расписанием на день.
    :rtype: str
    """
    now = datetime.now().time()
    current_lesson = get_current_lesson(now)
    message = ""

    for i, x in enumerate(lessons):
        if current_lesson is not None:
            if current_lesson.index == i and now > current_lesson.start:
                cursor = "🠗"
            elif current_lesson.index == i:
                cursor = "➜"
            else:
                cursor = f"{i+1}."
        else:
            cursor = f"{i+1}."

        message += f"\n{cursor}"

        tt = timetable[i]
        if current_lesson is not None and current_lesson.index < i:
            message += time(tt[0], tt[1]).strftime(" %H:%M -")

        message += time(tt[2], tt[3]).strftime(" %H:%M")

        if current_lesson is not None and current_lesson.index < i:
            message += " │ "
        else:
            message += " ┃ "

        # Если несколько уроков, выводим их все по порядку
        if isinstance(x, list):
            message += "; ".join(x)
        # Если есть урок
        elif len(x) > 0 and x.split(":")[0] not in ("None", "---"):
            message += x

    return message

def send_search_res(intent: Intent, res: list) -> str:
    """Собирает сообщение с результатами поиска в расписании.

    Является некоторой обёрткой над функцией send_day_lessons.
    Собирает заголовок поискового запроса и возвращает результаты
    поиска.
    Намерения используются при формировании результатов поиска.

    :oaram intent: Намерения для уточнения результатов поиска.
    :type intent: Intent
    :param res: Результаты поиска в расписании.
    :type res: list[list[list[str]]]
    :return: Сообщение с резульатами поиска в расписании.
    :rtype: str
    """
    message = "🔎 Поиск "
    if intent.cabinets:
        message += f" [{', '.join(intent.cabinets)}]"
    if intent.cl:
        message += f" ({', '.join(intent.cl)})"
    if intent.lessons:
        message += f" ({', '.join(intent.lessons)})"

    for day, lessons in enumerate(res):
        while lessons and not lessons[-1]:
            lessons.pop()

        if not lessons:
            continue

        message += f"\n\n📅 На {DAYS_NAMES[day]}:"
        message += send_day_lessons(lessons)

    return message

# TODO: AAAAAAAAAAAAAAAAAAAA
def send_counter( # noqa: PLR0912
    groups: dict[int, dict[str, dict]],
    target: Optional[CounterTarget]=None,
    days_counter: Optional[bool]=False
) -> str:
    """Возвращает сообщение с результами работы счётчика.

    Собирает сообщение со сгрупипрованными результатми работы счетчиков.
    Отображает группы счётчиков, сортрованные от больших к меньшем.
    Если указана цель (target), также отображает подгруппу
    счётчика.

    Доступные цели просмотра:

    - None: Не отображать подгруппу просмотра.
    - cl: По классам в расписании.
    - days: По дням недели (0 - понедельник, 5 - суббота).
    - lessons: По урокам.
    - cabinets: По кабинетам.
    - main: Обратный для индекса (если l_index, то по кабинетам).

    :param groups: Сгруппированные результаты работы счётчиков.
    :type groups: dict[int, dict[str, dict]]
    :param target: Режим просмотра расписания.
    :type target: str
    :param days_counter: Заменять имена групп на названия дней недели.
    :type days_counter: Optional[bool]
    :return: Сообщение с результатами работы счётчиков.
    :rtype: str
    """
    message = ""

    for group, res in sorted(groups.items(), key=lambda x: x[0], reverse=True):
        group_plural_form = plural_form(group, ["раз", "раза", "раз"])
        message += f"\n🔘 {group} {group_plural_form}:"

        # Доабвляем подгруппу
        if target is not None or target.value != "none":
            for obj, cnt in res.items():
                if len(res) > 1:
                    message += "\n--"

                # Заменям числа на название дней недели для счётчка по дням
                # Подумайте сами, что лучше, 1 или вт.
                if days_counter:
                    message += f" {_SHORT_DAYS_NAMES[int(obj)]}:"
                else:
                    message += f" {obj}:"

                cnt_groups = reverse_counter(cnt.get(target.value, {}))

                for cnt_group, k in sorted(cnt_groups.items(),
                                    key=lambda x: x[0], reverse=True):
                    # Заменяем числа на дни недели в подгруппу счётчика
                    if target == CounterTarget.DAYS:
                        count_items = " ".join((
                            _SHORT_DAYS_NAMES[int(x)] for x in k
                        ))
                    else:
                        count_items = " ".join(k)

                    if cnt_group == 1:
                        message += f" 🔸{count_items}"
                    elif cnt_group == group:
                        message += f" 🔹{count_items}"
                    else:
                        message += f" 🔹{cnt_group}:{count_items}"

            message += "\n"

        # Заменям числа на название дней недели для счётчка по дням
        elif days_counter:
            message += f" {', '.join([_SHORT_DAYS_NAMES[int(x)] for x in res])}"
        else:
            message += f" {', '.join(res)}"

    return message


# Вспомогательные функции для сообщения статуса парсера
# =====================================================

def _get_next_update_str(time: datetime, now: Optional[datetime]=None) -> str:
    if now is None:
        now = datetime.now()

    if now.day == time.day:
        res = time.strftime("в %H:%M")
    else:
        res = time.strftime("%d %h в %H:%M")

    return res

def _get_cl_counter_str(cl_counter: Counter) -> str:
    groups = defaultdict(list)
    for k, v in cl_counter.items():
        groups[v].append(k)

    res = ""
    for k, v in sorted(groups.items(), key=lambda x: int(x[0])):
        res += f" 🔹{k} ({', '.join(sorted(map(str, v)))})"

    return res

def _get_hour_counter_str(hour_counter: Counter) -> Optional[str]:
    groups = defaultdict(list)
    for k, v in hour_counter.items():
        groups[v].append(k)

    res = ""
    for k, v in sorted(groups.items(), key=lambda x: int(x[0])):
        if k == 1:
            res += f" 🔸{', '.join(sorted(map(str, v)))}"
        else:
            res += f" 🔹{k} ({', '.join(sorted(map(str, v)))})"

    return res



class SPMessages:
    """Предоставляет методы для более удобной работы с расписанием.

    Позводяет взаимодействовать с пользователями расписнаия.
    Сохранять их класс по умолчанию и отслеживать их расписание.
    Методы возвращают текстовые сообщенияю. которые после можно
    использовать напрмиер в чат ботах.

    :param uid: User ID, уникальные идентификатор пользователя.
    :type uid: str
    :param user_data: Установленные данные пользователя.
    :type user_data: Optional[dict[str, Any]]
    """

    def __init__(
        self,
        uid: str,
        user_data: Optional[dict[str, Any]]=None
    ) -> None:
        super(SPMessages, self).__init__()

        self.uid = uid
        self._users_path = Path(users_path)
        #: Денные пользователя.
        self.user: Optional[dict[str, Any]] = self.get_user(user_data)
        #: Экземпдяр расписания.
        self.sc: Schedule = Schedule(self.user["class_let"])
        if self.user["class_let"] is not None:
            self.user_intent: Intent = self.sc.construct_intent(
                cl=self.user["class_let"]
            )
        else:
            self.user_intent: Intent = Intent()

    def send_status(self) -> str:
        """Возвращает информацию о парсере и пользователях.

        Эта статистическая информация, о работа парсера, времени
        послдней проерки и обновления и прочих параметрах, связанных
        с парсером и пользователями обёрток.

        :return: Статус парсера и пользователей.
        :rtype: str
        """
        now = datetime.now()
        next_update = datetime.fromtimestamp(self.sc.schedule["next_parse"])
        last_parse = datetime.fromtimestamp(self.sc.schedule["last_parse"])

        nu_str = _get_next_update_str(next_update, now)
        lp_str = _get_next_update_str(last_parse, now)

        nu_delta = get_str_timedelta(
            int((next_update - now).seconds),
            hours=False
        )
        lp_delta = get_str_timedelta(int((now - last_parse).seconds))

        cl_counter = Counter()
        hour_counter = Counter()
        notify_count = 0
        active_users = 0
        users = load_file(self._users_path)
        for k, v in users.items():
            if v["last_parse"] == self.sc.schedule["last_parse"]:
                active_users += 1
            if v.get("notifications") and v.get("set_class"):
                notify_count += 1
                for h in v.get("hours"):
                    hour_counter[h] += 1

            cl_counter[v["class_let"]] += 1

        active_pr = round(active_users/len(users)*100, 2)

        res = "🌟 Версия sp: 5.8.12 (149)"
        res += "\n\n🌲 Разработчик: Milinuri Nirvalen (@milinuri)"
        res += f"\n🌲 [{nu_delta}] {nu_str} проверено"
        res += f"\n🌲 {lp_str} обновлено ({lp_delta} назад)"
        res += f"\n🌲 {len(users)} пользователей ({notify_count}🔔)"
        res += f"\n🌲 из них {active_users} активны ({active_pr}%)"
        if len(hour_counter) > 0:
            res += "\n🌲 Уведомления пользователей:"
            res += f"\n🔔 {_get_hour_counter_str(hour_counter)}"
        res += f"\n🌲 {self.user['class_let']} класс"
        res += f"\n🌲 ~{len(self.sc.l_index)} пр. ~{len(self.sc.c_index)} каб."
        res += f"\n🌲 {_get_cl_counter_str(cl_counter)}"

        other_cl = sorted(set(self.sc.lessons) - set(cl_counter))
        if other_cl:
            res += f" 🔸{', '.join(other_cl)}"

        return res


    # Управление данными пользователя
    # ===============================

    def get_user(self, user_data: Optional[dict[str, Any]]=None
    ) -> dict[str, Any]:
        """Возвращает данные пользователя или данные по умолчанию.

        :param user_data: Данные пользователя по умолчанию.
        :type user_data: Optional[dict[str, Any]]
        :return: Данные пользователя или данные по умолчанию.
        :rtype: dict[str, Any]
        """
        if user_data is None:
            user_data = load_file(self._users_path).get(self.uid)
            if user_data is None:
                return default_user_data.copy()

        return check_keys(user_data, default_user_data)

    def save_user(self) -> None:
        """Записывает данные пользователя в файл."""
        users: dict[str, Any] = load_file(self._users_path)
        users.update({self.uid: self.user})
        save_file(self._users_path, users)
        logger.info("Save user: {}", self.uid)

    def reset_user(self) -> None:
        """Сбрасывает данные пользователя до значений по умолчанию."""
        users: dict[str, Any] = load_file(self._users_path)
        users.update({self.uid: default_user_data.copy()})
        save_file(self._users_path, users)
        logger.info("Reset user: {}", self.uid)

    def set_class(self, cl: Optional[str]=None) -> bool:
        """Изменяет класс пользователя.

        Изменяет класс пользователя на укащанный.
        Выставляет временную метку join_data на данный момент.
        Устанавливает флаг set_class в True.
        Перемещаеь временную метку проверки расписания на данный
        момент.

        Если передать None - переходит в состояние "отвязанного класса".

        :param cl: Какой класс установить пользователю.
        :type cl: Optional[str]
        :return: Установился ли класс пользователю.
        :rtupe: bool
        """
        if cl is None or cl in self.sc.lessons:
            self.user["join_date"] = datetime.now().timestamp()
            self.user["class_let"] = cl
            self.user["set_class"] = True
            self.user["last_parse"] = self.sc.schedule["last_parse"]
            self.save_user()
            return True
        return False

    def get_lessons_updates(self) -> Optional[dict]:
        """Возвращает упаковынный списк изменний пользователя.

        Проверяет наличие новых обнволений по временной метке.
        Если расписание изменилось, получает список исземеий для класса.
        После упаковывает список изменений.
        Наконец, выравнивает временную метку последнего обновления
        пользователя с временной меткой послдней проверки расписания.

        :return: Упокаванный список изменений расписания расписания.
        :rtype: dict[str, Any]
        """
        if self.user["class_let"] is None:
            return

        if self.sc.schedule["last_parse"] <= self.user["last_parse"]:
            return

        logger.info("Get lessons updates")
        updates = self.sc.get_updates(self.user_intent, self.user["last_parse"])

        # Обновление времени последней проверки расписания
        self.user["last_parse"] = self.sc.schedule["last_parse"]+1
        self.save_user()

        if len(updates) > 0:
            return compact_updates(updates)


    # Отображение расписания
    # ======================

    def send_lessons(self, intent: Intent) -> str:
        """Собирает сообщение с расписанием уроков.

        Обрётка над методов Schedule для получения расписания.
        Принимает намерения, чтобы уточнить какое нужно расписание.
        Форматирует сообщений с помощью send_day_lessons.

        :param intent: Намерения для уточнения параметров расписания.
        :type intent: Intent
        :return: Сообщение с расписанием уроков.
        :rtype: str
        """
        cl = intent.cl or (self.user["class_let"],)
        lessons = {x: self.sc.get_lessons(x) for x in cl}
        message = ""
        for day in intent.days:
            message += f"\n📅 На {DAYS_NAMES[day]}:"
            for cl, cl_lessons in lessons.items():
                message += f"\n🔶 Для {cl}:"
                message += f"{send_day_lessons(cl_lessons[day])}"
            message += "\n"

        # Обновления в расписаниии
        update = self.get_lessons_updates()
        if update is not None:
            message += "\nУ вас изменилось расписание! 🎉"
            message += f"\n{send_update(update, cl)}"
        return message

    def get_current_day(self, intent: Intent) -> int:
        """Получате текщий или следующий день если уроки кончились.

        Работает это так, что если уроки ещё не кончились,
        то метод вернёт номер текущего дня.
        Иначе же прибавит +1 к текущему.
        Также автоматически происходи сдвиг на понедельник, если нужно.
        это используется при умном получении расписания на сегодня
        или завтра в зависимости от времени.

        :param intent: Намерение для получения расписания
        :type intent: Intent
        :return: Номер дня недели, для которого получать расписание
        :rtype: int
        """
        now = datetime.now()
        today = now.weekday()

        # Если сегодня воскресенье, получаем уроки на понедельник
        # В воскресение же нету уроков?
        if today == 6: # noqa: PLR2004
            return 0

        cl = intent.cl or (self.user["class_let"],)
        max_lessons = max(map(lambda x: len(self.sc.get_lessons(x)), cl))
        hour = timetable[max_lessons-1][2]

        if now.hour >= hour:
            today += 1

        # Опять же, в воскресение не может быть уроков, не шутите так
        # Ааааааа, опять вы со своими магическими числами.
        # Да не будет такого, что конец недели передвинется.
        # Всё, не надо мне тут начинать.
        return 0 if today > 5 else today # noqa: PLR2004

    def send_today_lessons(self, intent: Intent) -> str:
        """Расписание уроков на сегодня/завтра.

        Работает как send_lessons.
        Отправляет расписание для классов на сегодня, если уроки
        ешё идут.
        Отпрвялет расписание на завтра, если уроки на сегодня уже
        кончились.

        Использует намерения для уточнения расписания.
        Однако будет игнорировать указанные дни в намерении.
        Иначе используйте метод send_lessons.

        :param intent: Намерения для уточнения расписания.
        :type intent: Intent
        :return: Расписание уроков на сегодня/завтра.
        :rtype: str
        """
        return self.send_lessons(intent.reconstruct(
            self.sc, days=self.get_current_day(intent)
        ))


    # Методы для работы с расписанием
    # ===============================

    def search(
        self, target: str, intent: Intent,
        cabinets: Optional[bool]=False
    ) -> str:
        """Явялется сокращение для поиска в расписании.

        Производит поиск в расписании.
        А после собирает сообщение с резульатами поиска в расписании.

        Поиск немного изменяется в зависимости от режима.

        .. table::

            +----------+---------+---------+
            | cabinets | obj     | another |
            +==========+=========+=========+
            | false    | lesson  | cabinet |
            +----------+---------+---------+
            | true     | cabinet | lesson  |
            +----------+---------+---------+

        :param target: Цель для поиска, урок или кабинет.
        :type target: str
        :param intent: Намерения для уточнения результатов поиска.
        :type intent: Intent
        :param cabinets: Что ищём, урок или кабинет. Обычно урок.
        :type cabinets: bool
        :return: Результаты поиска в расписании
        :rtype: list[list[list[str]]]
        """
        return send_search_res(
            intent, self.sc.search(target, intent, cabinets)
        )
