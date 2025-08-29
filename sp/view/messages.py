"""Генератор текстовых сообщений для класса Schedule.

Является прототипом первого будущего класса представления.
Является промежуточным слоем между расписанием и платформой.
Используется для преобразования необработанных результатов работы
методов класса Schedule.
Выходным результатом генератора сообщений являются строки.
Вы можете использовать их в чат-ботах, например Telegram.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, time
from typing import NamedTuple

from loguru import logger

from sp.counter import CounterTarget, reverse_counter
from sp.db import User
from sp.enums import DAY_NAMES, SHORT_DAY_NAMES, WeekDay
from sp.intents import Intent
from sp.parser import Schedule
from sp.updates import UpdateData
from sp.version import (
    PROJECT_VERSION,
    UPDATES_URL,
    VersionInfo,
    VersionOrd,
    check_updates,
)
from sp.view.base import View

# Константы
# =========

_EMPTY_LESSONS = ("---", "None")

# Максимальные отображаемый диапазон временного промежутка (2 дня)
_UPDATE_DELTA = 172800
# Максимально отображаемое прошедшее время обновления (24 часа)
_MAX_UPDATE_SINCE = 86400

# Расписание уроков: начало (час, минуты), конец (час, минуты)
# Расписание звонков с понедельника (22.01) и  до конца уч. года.
# TODO: Написать класс для работы с расписанием звонков
timetable = [
    [8, 0, 8, 45],
    [8, 55, 9, 40],
    [10, 0, 10, 45],
    [11, 5, 11, 50],
    [12, 0, 12, 45],
    [12, 55, 13, 40],
    [13, 50, 14, 35],
    [14, 45, 15, 30],
]

# Вспомогательные функции отображения
# ===================================


class LessonTime(NamedTuple):
    """Описывает время начала и конца урока.

    Этот фрагмент должен был стать частью будущего обновления.
    Данные фрагмент будет переписан со временем.
    Используется для детального отображения указателя на текущий урок.
    """

    start: time
    end: time
    lesson_index: int


def time_to_seconds(now: time) -> int:
    """Переводит datetime.time в полное количество секунд этого дня."""
    return now.hour * 3600 + now.minute * 60 + now.second


def seconds_to_time(now: int) -> time:
    """Переводит полное количество секунд в datetime.time."""
    h, d = divmod(now, 3600)
    m, s = divmod(d, 60)
    return time(h, m, s)


def get_current_lesson(now: time) -> LessonTime:
    """Возвращает текущий урок.

    Используется в функции сбора расписания на день.
    Чтобы можно было показать указатель на текущий урок.

    Если уроки ещё не начались или уже кончились -> None.
    """
    l_end_time = None
    for i, lesson in enumerate(timetable):
        start_time = time(lesson[0], lesson[1])
        end_time = time(lesson[2], lesson[3])

        if l_end_time is not None and now >= l_end_time and now < start_time:
            return LessonTime(l_end_time, start_time, i)
        if now >= start_time and now < end_time:
            return LessonTime(start_time, end_time, i)

        l_end_time = end_time

    # Костыль номер #46
    # Лучше возвращать начало и конец первого урока, чем вообще ничего
    # не возвращать
    return LessonTime(
        time(timetable[0][0], timetable[0][1]),
        time(timetable[0][2], timetable[0][3]),
        lesson_index=0,
    )


# Функции отображения списка изменений
# ====================================


def plural_form(n: int, v: tuple[str, str, str]) -> str:
    """Возвращает склонённое значение в зависимости от числа.

    Возвращает склонённое слово: "для одного", "для двух",
    "для пяти" значений.
    """
    return v[2 if (4 < n % 100 < 20) else (2, 0, 1, 1, 1, 2)[min(n % 10, 5)]]


def get_str_timedelta(s: int, hours: bool | None = True) -> str:
    """Возвращает строковый обратный отсчёт из количества секунд.

    Если hours = False -> ММ:SS.
    Если hours = True -> HH:MM:SS.
    """
    if hours:
        h, r = divmod(s, 3600)
        m, s = divmod(r, 60)
        return f"{h:02}:{m:02}:{s:02}"
    m, s = divmod(s, 60)
    return f"{m:02}:{s:02}"


def _send_cl_updates(cl_updates: list[list[str] | None]) -> str:
    """Возвращает сообщение списка изменений для класса.

    В зависимости от типа изменений вид сообщений немного отличается.

    **Условные обозначения**:

    - `{l}` - Название урока.
    - `{c}` - Кабинет урока.
    - `{ol}` - Название урока до изменений.
    - `{oc}` - Кабинет урока до изменений.

    **Типы сообщений**:

    - `++{ol}:{oc}` - Добавлен урок в расписания.
    - `--{ol}:{oc}` - Урок убран из расписания.
    - `{ol} -> {l}:{c}` - Если сменился только урок, без кабинета.
    - `{l}:({oc} -> {c})` - Если сменился только кабинет, без урока.
    - `{ol}:{oc} -> {l}:{c}` - Изменилось всё (прочий случай).
    """
    message = ""
    for i, u in enumerate(cl_updates):
        if u is None:
            continue

        # Если урок не был выбран
        if str(u[0]) == "None":
            message += f"{i + 1}: ++{u[1]}\n"
            continue

        message += f"{i + 1}: "
        ol, oc = str(u[0]).split(":")
        l, c = str(u[1]).split(":")  # noqa: E741

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


def _get_update_header(
    update: UpdateData, extend_info: bool | None = True
) -> str:
    """Возвращает заголовок списка изменений.

    Собирает динамический заголовок о списке записи изменений.

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

    полное время временного окна, а также время прошедшее с
    момента записи являются расширенными опциональными параметрами.
    """
    # Получаем timestamp обновления
    end_timestamp = update.get("end_time", 0)
    if not isinstance(end_timestamp, int):
        raise ValueError("End update timestamp value must be integer")

    start_timestamp = update.get("start_time", end_timestamp)
    if not isinstance(start_timestamp, int):
        raise ValueError("Start update timestamp value must be integer")

    e_time = datetime.fromtimestamp(end_timestamp, UTC)
    s_time = datetime.fromtimestamp(start_timestamp, UTC)
    message = f"📀 {s_time.strftime('%d.%m %H:%M')} "

    t = e_time.strftime("%d.%m %H:%M" if s_time.day != e_time.day else "%H:%M")
    message += f"➜ {t}"

    if extend_info:
        update_delta = int(end_timestamp - start_timestamp)
        now_delta = int(datetime.now().timestamp() - end_timestamp)
        extend_message = ""

        if update_delta <= _UPDATE_DELTA:
            extend_message += f"🗘 {get_str_timedelta(update_delta, hours=True)}"

        if now_delta <= _MAX_UPDATE_SINCE:
            extend_message += f" ⭯ {get_str_timedelta(now_delta, hours=True)}"

        if extend_message:
            message += f" [{extend_message}]"

    return message


# Вспомогательные функции отображения
# ===================================


def send_day_lessons(lessons: Iterable[list[str] | str]) -> str:
    """Собирает сообщение с расписанием уроков на день.

    Возвращает сообщение списка уроков на день.
    Помимо списка уроков указывает какие уроки прошли и какие ещё
    буду.
    Также указывает на текущий урок, время начало и конца уроков.

    Также можно передавать несколько уроков в рамках одного времени.
    Это может использоваться в отображении результатов поиска в
    расписании.
    """
    now = datetime.now(UTC).time()
    current_lesson = get_current_lesson(now)
    message = ""

    for i, x in enumerate(lessons):
        if current_lesson.lesson_index == i and now > current_lesson.start:
            cursor = "🠗"
        elif current_lesson.lesson_index == i:
            cursor = "➜"
        else:
            cursor = f"{i + 1}."

        message += f"\n{cursor}"

        tt = timetable[i]
        if current_lesson.lesson_index <= i:
            message += time(tt[0], tt[1]).strftime(" %H:%M -")

        message += time(tt[2], tt[3]).strftime(" %H:%M")
        message += " │ " if current_lesson.lesson_index < i else " ┃ "

        # Если несколько уроков, выводим их все по порядку
        if isinstance(x, list):
            message += "; ".join(x)
        # Если есть урок
        elif len(x) > 0 and x.split(":")[0] not in _EMPTY_LESSONS:
            message += x

    return message


def send_search_res(intent: Intent, res: list) -> str:
    """Собирает сообщение с результатами поиска в расписании.

    Является некоторой обёрткой над функцией send_day_lessons.
    Собирает заголовок поискового запроса и возвращает результаты
    поиска.
    Передайте сюда намерение, которое использовалось при поиске.
    Поскольку оно будет использовано также для сборки заголовка.
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

        message += f"\n\n📅 На {DAY_NAMES[day]}:"
        message += send_day_lessons(lessons)

    return message


# Вспомогательные функции для сообщения статуса парсера
# =====================================================


def _get_next_update_str(time: datetime, now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(UTC)

    if now.day == time.day:
        res = time.strftime("в %H:%M")
    else:
        res = time.strftime("%d %h в %H:%M")

    return res


def _get_cl_counter_str(cl_counter: Counter[str]) -> str:
    groups = defaultdict(list)
    for k, v in cl_counter.items():
        groups[v].append(str(k))

    res = []
    for k, v in sorted(groups.items(), key=lambda x: int(x[0])):
        res.append(f" 🔹{k} ({', '.join(v)})")

    return "".join(res)


def _get_hour_counter_str(hour_counter: Counter[int]) -> str:
    groups: dict[int, list[str]] = defaultdict(list)
    for k, v in hour_counter.items():
        groups[v].append(str(k))

    res = []
    for k, v in groups.items():
        if k == 1:
            res.append(f" 🔸{', '.join(v)}")
        else:
            res.append(f" 🔹{k} ({', '.join(v)})")

    return "".join(res)


def _get_ver_str(cur_ver: VersionInfo, dest_url: str) -> str:
    res = cur_ver.full
    try:
        vs = check_updates(cur_ver, dest_url)
    except Exception as e:
        logger.error("Error while check updates: {}", e)
        vs = None

    if vs is None:
        res += "\n⚠️ Не удалось проверить обновления.."
    elif vs.status == VersionOrd.LT:
        res += f"\n🍰 Ура ура, доступно обновление: {vs.git_ver.full}"
    elif vs.status == VersionOrd.GT:
        res += "\n🎩 Кажется это тестовая сборка."

    return res


class MessagesView(View[str]):
    """Предоставляет методы для более удобной работы с расписанием.

    В отличие от необработанных результатов работы Schedule, данный
    генератор сообщения в своих методах возвращает строки.
    Генератор сообщений используется в чат-ботах, поскольку возвращает
    уже готовые текстовые сообщения.
    """

    # Глобальное описание версии класса представления
    # Пока что это пожалуй просто костыль, но что уж поделать
    version = PROJECT_VERSION

    def __init__(
        self,
    ) -> None:
        #: Экземпляр расписания
        self.sc: Schedule = Schedule()

    async def get_status(
        self, user: User, platform_version: VersionInfo
    ) -> str:
        """Возвращает информацию о платформе.

        Эта статистическая информация, о работа парсера, времени
        последней проверки и обновления и прочих параметрах, связанных
        с поставщиком и пользователями платформы.
        """
        storage_users = await User.get_stats(self.sc)
        now = datetime.now(UTC)
        # На случай если это первый раз когда мы получаем расписание
        if self.sc.next_parse is None:
            next_update = now
        else:
            next_update = datetime.fromtimestamp(float(self.sc.next_parse), UTC)

        last_parse = datetime.fromtimestamp(
            float(self.sc.schedule["last_parse"]), UTC
        )

        nu_str = _get_next_update_str(next_update, now)
        lp_str = _get_next_update_str(last_parse, now)

        nu_delta = get_str_timedelta(
            int((next_update - now).total_seconds()), hours=False
        )
        lp_delta = get_str_timedelta(int((now - last_parse).total_seconds()))

        # При первом запуске из консоли у нас ещё нет пользователей
        if storage_users.total > 0:
            active_pr = round(
                (storage_users.active / storage_users.total) * 100, 2
            )
        else:
            active_pr = 0

        res = (
            f"🌟 SPlatform {_get_ver_str(self.version, UPDATES_URL)}"
            f"\n☕ Версия платформы: {platform_version.full}"
            "\nРазработчик: Milinuri Nirvalen (@milinuri)"
            f"\n\n🌳 [{nu_delta}] {nu_str} проверено"
            f"\n🌳 {lp_str} обновлено ({lp_delta} назад)"
            f"\n🌳 {user.cl} класс"
            f"\n🌳 ~{len(self.sc.l_index)} пр. ~{len(self.sc.c_index)} каб."
            f"\n🌳 {storage_users.total} участников ({storage_users.notify}🔔)"
            f"\n🌳 из них {storage_users.active} активны ({active_pr}%)"
            f"\n{_get_cl_counter_str(storage_users.cl)}"
        )

        other_cl = sorted(set(self.sc.lessons) - set(storage_users.cl))
        if other_cl:
            res += f" 🔸{', '.join(other_cl)}"
        if len(storage_users.hour) > 0:
            res += "\n🌳 Уведомления пользователей:"
            res += f"\n{_get_hour_counter_str(storage_users.hour)}"

        return res

    # Отображение расписания
    # ======================

    def lessons(self, intent: Intent) -> str:
        """Собирает сообщение с расписанием уроков.

        Обёртка над методом класса Schedule для получения расписания.
        Принимает намерения, для уточнения форматов расписание.
        Форматирует сообщений с помощью send_day_lessons.
        """
        lessons = {x: self.sc.lessons(x) for x in intent.cl}
        message = ""
        for day in intent.days:
            message += f"\n📅 На {DAY_NAMES[day]}:"
            for cl, cl_lessons in lessons.items():
                message += f"\n🔶 Для {cl}:"
                message += f"{send_day_lessons(cl_lessons[day])}"
            message += "\n"
        return message

    def current_day(self, intent: Intent) -> int:
        """Получает текущий или следующий день если уроки кончились.

        Работает это так, если уроки ещё не кончились,
        то вернёт номер текущего дня.
        Иначе же прибавит +1 к текущему номер дня.
        Также автоматически происходит сдвиг на понедельник, если нужно.
        это используется при умном получении расписания на сегодня
        или завтра в зависимости от времени.
        """
        now = datetime.now(UTC)
        today = now.weekday()

        # Если сегодня воскресенье, получаем уроки на понедельник
        # В воскресение же нету уроков?
        if today == WeekDay.SATURDAY + 1:
            return 0

        if len(intent.cl) == 0:
            raise ValueError("Intent must contain at least one class let")
        max_lessons = max(map(lambda x: len(self.sc.lessons(x)), intent.cl))
        hour = timetable[max_lessons - 1][2]

        if now.hour >= hour:
            today += 1

        return 0 if today > WeekDay.SATURDAY else today

    def _get_day_str(self, today: int, relative_day: int) -> str:
        if relative_day == today:
            return "Сегодня"
        if relative_day == today + 1:
            return "Завтра"
        return WeekDay(relative_day).to_short_str()

    def relative_day(self, user: User) -> str:
        """Получает строковое название текущего дня недели.

        Возвращает Сегодня/Завтра/день недели, в зависимости от
        прошедших уроков.

        Не принимает намерение, получает день только для
        переданного пользователя.
        """
        today = datetime.now(UTC).today().weekday()
        tomorrow = today + 1
        if tomorrow > WeekDay.SATURDAY:
            tomorrow = 0

        if user.cl == "":
            return "Сегодня"

        current_day = self.current_day(
            intent=self.sc.construct_intent(cl=user.cl, days=today)
        )
        return self._get_day_str(today, current_day)

    def today_lessons(self, intent: Intent) -> str:
        """Расписание уроков на сегодня/завтра.

        Работает как lessons.
        Отправляет расписание для классов на сегодня, если уроки
        ешё идут.
        Отправляет расписание на завтра, если уроки на сегодня уже
        кончились.

        Использует намерения для уточнения расписания.
        Однако будет игнорировать указанные дни в намерении.
        Иначе используйте метод lessons.
        """
        return self.lessons(
            intent.reconstruct(self.sc, days=self.current_day(intent))
        )

    # Методы для работы с расписанием
    # ===============================

    def search(
        self, target: str, intent: Intent, cabinets: bool = False
    ) -> str:
        """Поиск по имена урока/кабинета в расписании.

        Производит поиск в расписании.
        А после собирает сообщение с результатами поиска.

        Поиск немного изменяется в зависимости от режима.

        +----------+---------+---------+
        | cabinets | obj     | another |
        +==========+=========+=========+
        | false    | lesson  | cabinet |
        +----------+---------+---------+
        | true     | cabinet | lesson  |
        +----------+---------+---------+
        """
        return send_search_res(intent, self.sc.search(target, intent, cabinets))

    def update(self, update: UpdateData, hide_cl: str | None = None) -> str:
        """Собирает сообщение со списком изменений в расписании.

        Собирает полноценное сообщение со всеми изменениями.
        Также добавляет заголовок записи об изменениях.

        Переданный класс в ``hide_cl`` не будет отображаться в
        заголовке классов.
        Это полезно если вы получаете изменения только для одного
        класса.

        Пример сообщения со списком изменений:

        ```
        📀 21.05 16:00 ➜ 05.06 18:47
        🔷 На четверг
        🔸 Для 5б:
        2: --физкульт:330
        ```

        Если `hide_cl="5б"`:

        ```
        📀 21.05 16:00 ➜ 05.06 18:47
        🔷 На четверг
        2: --физкульт:330
        ```
        """
        message = _get_update_header(update)
        updates = update.get("updates", [])
        if not isinstance(updates, (list)):
            raise ValueError("Updates must be a list of lessons")
        for day, day_updates in enumerate(updates):
            if not day_updates:
                continue

            message += f"\n🔷 На {DAY_NAMES[day]}"
            for u_cl, cl_updates in day_updates.items():
                if hide_cl is None or hide_cl is not None and hide_cl != u_cl:
                    message += f"\n🔸 Для {u_cl}:"

                message += "\n" if len(cl_updates) > 1 else " "
                message += _send_cl_updates(cl_updates)

        return message

    async def check_updates(self, user: User) -> str | None:
        """Проверяет обновления пользователя в расписании.

        Если изменения есть, добавляет заголовок и отображает
        сжатую запись со всеми изменениями в расписании.
        """
        update = await user.get_updates(self.sc)
        if update is None:
            return None

        return (
            f"🎉 У вас изменилось расписание!\n{self.update(update, user.cl)}"
        )

    def counter(  # noqa: PLR0912
        self,
        groups: dict[int, dict[str, dict]],
        target: CounterTarget | None = None,
        days_counter: bool = False,
    ) -> str:
        """Возвращает сообщение с результатами работы счётчика.

        Собирает сообщение сгруппированного результата работы счётчика.
        Отображает результаты счётчика, отсортированные от большего
        к меньшему.
        Если указана подгруппу (target), то она также буде включена в
        результаты счётчика.
        """
        message = ""

        for group, res in sorted(
            groups.items(), key=lambda x: x[0], reverse=True
        ):
            group_plural_form = plural_form(group, ("раз", "раза", "раз"))
            message += f"\n🔘 {group} {group_plural_form}:"

            # проверяем подгруппу
            if target is not None or target is CounterTarget.NONE:
                for obj, cnt in res.items():
                    if len(res) > 1:
                        message += "\n--"

                    # Заменяем числа на название дней недели для счётчика дней.
                    # Подумайте сами, что лучше, 1 или вт.
                    if days_counter:
                        message += f" {SHORT_DAY_NAMES[int(obj)]}:"
                    else:
                        message += f" {obj}:"

                    cnt_groups = reverse_counter(cnt.get(target.value, {}))

                    for cnt_group, k in sorted(
                        cnt_groups.items(), key=lambda x: x[0], reverse=True
                    ):
                        # Заменяем числа на дни недели в подгруппу счётчика
                        if target == CounterTarget.DAYS:
                            count_items = " ".join(
                                SHORT_DAY_NAMES[int(x)] for x in k
                            )
                        else:
                            count_items = " ".join(k)

                        if cnt_group == 1:
                            message += f" 🔸{count_items}"
                        elif cnt_group == group:
                            message += f" 🔹{count_items}"
                        else:
                            message += f" 🔹{cnt_group}:{count_items}"

                message += "\n"

            # Заменяем числа на название дней недели для счётчика по дням
            elif days_counter:
                message += (
                    f" {', '.join([SHORT_DAY_NAMES[int(x)] for x in res])}"
                )
            else:
                message += f" {', '.join(res)}"

        return message
