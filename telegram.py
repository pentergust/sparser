"""Telegram-бот для доступа к SPMessages.

Полностью реализует доступ ко всем разделам SPMessages.
Не считая некоторых ограничений в настройке "намерений" (Intents).

Команды бота для BotFather
--------------------------

sc - Уроки на сегодня
updates - Изменения в расписании
notify - Настроить уведомления
counter - Счётчики уроков/кабинетов
tutorial - Как писать запросы
set_class - Изменить класс
help - Главное меню
info - Информация о боте

Author: Milinuri Nirvalen
Ver: 2.1 +1
"""

import asyncio
from datetime import datetime
from os import getenv
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (CallbackQuery, ErrorEvent, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, Update)
from dotenv import load_dotenv
from loguru import logger

from sp.counters import (cl_counter, days_counter, group_counter_res,
                         index_counter)
from sp.intents import Intent
from sp.messages import SPMessages, send_counter, send_search_res, send_update
from sp.parser import Schedule
from sp.utils import get_str_timedelta


# Настройкки и константы
# ======================

load_dotenv()
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN", "")
dp = Dispatcher()
days_names = ("пн", "вт", "ср", "чт", "пт", "сб")
_TIMETAG_PATH = Path("sp_data/last_update")
_HOME_BUTTON = InlineKeyboardButton(text="◁", callback_data="home")

TO_HOME_MARKUP = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="🏠Домой", callback_data="home")]]
)
PASS_SET_CL_MARKUP = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Не привязывать класс", callback_data="pass"),
            InlineKeyboardButton(text="Ограничения", callback_data="cl_features"),
        ]
    ]
)
BACK_SET_CL_MARKUP = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="◁", callback_data="set_class"),
            InlineKeyboardButton(text="Не привязывать класс", callback_data="pass"),
        ]
    ]
)


# Добавление Middleware
# =====================

@dp.message.middleware()
@dp.callback_query.middleware()
async def sp_middleware(
    handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: Dict[str, Any],
) -> Any:
    """Добавляет экземпляр SPMessages в обработчик."""
    if isinstance(event, CallbackQuery):
        uid = event.message.chat.id
    else:
        uid = event.chat.id

    data["sp"] = SPMessages(str(uid))
    return await handler(event, data)

# Если вы хотите отключить логгирование в боте
# Закомментируйте необходимые вам декораторы
@dp.message.middleware()
@dp.callback_query.middleware()
async def log_middleware(
    handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: Dict[str, Any],
) -> Any:
    """Отслеживает полученные ботом сообщения и callback data."""
    if isinstance(event, CallbackQuery):
        logger.info("[cq] {}: {}", event.message.chat.id, event.data)
    else:
        logger.info("[msg] {}: {}", event.chat.id, event.text)

    return await handler(event, data)


# Статические тексты сообщений
# ============================

# Главнео сообщение справки бота
HOME_MESSAGE = ("💡 Некоторые примеры запросов:"
    "\n-- 7в 6а на завтра"
    "\n-- уроки 6а на вторник ср"
    "\n-- расписание на завтра для 8б"
    "\n-- 312 на вторник пятницу"
    "\n-- химия 228 6а вторник"
    "\n\n🏫 В запросах вы можете использовать:"
    "\n* Урок/Кабинет: Получить все его упоминания."
    "\n* Классы: для которого нужно расписание."
    "\n* Дни недели:"
    "\n-- Если день не указан - на сегодня/завтра."
    "\n-- Понедельник-суббота (пн-сб)."
    "\n-- Сегодня, завтра, неделя."
    "\n\n🌟 Как писать запросы? /tutorial"
)

# Сообщение при смене класса
SET_CLASS_MESSAGE = ("Для полноценной работы желательно указать ваш класс."
    "\nВы сможете быстро просматривать расписание и получать уведомления."
    "\nПочитать о всех преимуществах - /cl_features"
    "\n\n🌟 Просто укажите класс следующим сообщеним (\"8в\")"
    "\n\nВы можете пропустить выбор класса нажав кнопку (/pass)."
    "\n\n💡 Вы можете сменить класс позже:"
    "\n-- через команду /set_class."
    "\n-- Ещё -> сменить класс."
)

# Какие преимущества получает указавгих класс пользователь
CL_FEATURES_MESSAGE = ("🌟 Если вы укажете класс, то сможете:"
    "\n\n-- Быстро получать расписание для класса, кнопкой в главном меню."
    "\n-- Не укзаывать ваш класс в текстовых запросах (прим. \"пн\")."
    "\n-- Получать уведомления и рассылку расписание для класса."
    "\n-- Просматривать список изменений для вашего класса."
    "\n-- Использовать счётчик cl/lessons."
    "\n\n💎 Список возможностей может пополняться."
)

# Сообщения интерактивного обучения по запросам к расписанию
TUTORIAL_MESSAGES = [
    ("💡 Как писать запросы?"
        "\nНа самом деле всё намно-о-ого легче."
        "\nПройдите это простое обучение и убедитесь сами."
        "\n\nВы можете пройти обучение с самого начала."
        "\nИли выбрать нужную страницу, если уже проходили его."
    ),

    ("1. Будьте проще"
        "\n\nСовсем не обязательно указывать в запросах \"посторонние\" слова."
        "\nТакие как \"уроки на\", \"расписание\", \"для\" и подобные."
        "\nОни никак не влияют на сам запрос."
        "\n\n❌ уроки на завтра"
        "\n✅ Завтра"
        "\n\n❌ Расписание для 9в на вторник"
        "\n✅ 9в вторник"
        "\n\nПорядок ключевых слов не имеет значение."
        "\n-- матем 8в = 8в матем"
    ),

    ("2. Классы"
        "\n\nЧтобы получить расписание, достаточно указать нужный класс."
        "\nЕсли день не указан, будет отправлено расписание на сегодня/завтра."
        "\n🔸 На сегодня - если уроки ещё идут."
        "\n🔸 На завтра - если уроки на сегодня уже кончились."
        "\n\n-- 7а ➜ Расписание для 7а на сегодня/завтра."
        "\n-- 7г 6а ➜ Сразу для нескольких классов."
        "\n\n🔎 Также классы используются в поиске:"
        "\n\n- химия 8б ➜ Все уроки химии для 9б."
        "\n- 9в 312 ➜ Все уроки в 312 кабинете для 9в"
        "\n\n💡 Посмотреть список всех классов можно в статусе:"
        "\n-- По кнопке \"ещё\" в главном меню."
        "\n-- По команде /info"
    ),

    ("3. Дни недели"
        "\n\nВы можете более явно указаать дни недели в запросах и поиске."
        "\nЕсли указаать только день, то получите расписание для вашего класса."
        "\n\n✏️ Доступные значения:"
        "\n-- Понедельник - суббота."
        "\n-- пн - сб."
        "\n-- Сегодня, завтра, неделя."
        "\n\n-- вт ➜ Расписание для вашего класса по умолчанию на вторник."
        "\n\nНапомним про \"быть проще\":"
        "\n❌ Уроки для 5г на среду"
        "\n✅ 5г среда"
        "\n\n🔎 Если день не указан, результат выводится на неделю."
        "\n-- матем вт ➜ Все уроки математики на вторник"
        "\n-- пт 312 ➜ Все уроки в 312 кабинете на пятницу"
    ),

    ("4. Поиск по урокам"
        "\n\n🔎 Укажите точное название урока для его поиска в расписании."
        "\nЕсли не указаны прочие параметры, расписание для всех на неделю."
        "\n\n✏️ Вы можете указать класс, день, кабинет в параметрах."
        "\n\n-- матем ➜ Вся математика за неделю для всех классов."
        "\n-- химия вторник 10а ➜ Более точный поиск."
        "\n\n⚠️ Если ввести несколько уроков, будет взять только первый."
        "\nЧтобы результат поиска не было слишком длинным."
        "\n\n💡 Посмотреть все классы можно в счётчиках:"
        "\n-- По кнопке \"Ещё\" ➜ \"Счётчики\""
        "\n-- По команде /counter"
    ),

    ("5. Поиск по кабинетам"
        "\n🔎 Укажите кабинет, чтобы взглняуть на расписание от его лица."
        "\nЕсли прочие парметры не указаны, расписание для всех на неделю."
        "\n\n✏️ Вы можете указать класс, день, урок в параметрах."
        "\n\n-- 328 ➜ Всё что проходит в 328 кабинете за неделю."
        "\n-- 312 литер вторник 7а ➜ Более точный поиск."
        "\n\n⚠️ Если указаать нексколько кабинетов, будет взят только первый."
        "\nЧтобы результат поиска не было слишком длинным."
        "\nОднако можно указаать несколько предметов в поиске по кабинету."
        "\n\n💡 Посмотреть все кабинеты можно в счётчиках:"
        "\n-- По кнопке \"Ещё\" ➜ \"Счётчики\" ➜ \"По урокам\""
        "\n-- По команде /counter ➜ \"По урокам\""
    ),

    ("🎉 Поздравляем с прохождением обучения!"
        "\nТеперь вы знаете всё о составлении запросов к расписанию."
        "\nПриятного вам использования бота."
        "\nВы умничка. ❤️"
    )
]


# Динамические клавиатуры
# =======================

def get_other_keyboard(
    cl: str, home_button: Optional[bool] = True
) -> InlineKeyboardMarkup:
    """Собирает дополнительную клавиатуру.

    Дополнительная клавиатура содержит на часто использумые разделы.
    Чтобы эти раделы не занимали место на главном экране и не пугали
    пользователей большим количеством разных кнопочек.

    Buttons:
        set_class => Сменить класс.
        count:lessons:main => Меню счётчиков бота.
        updates:last:0:{cl} => Последная сраница списка изменений.

    Args:
        cl (str): Класс пользователя для клавиатуры.
        home_button (bool, optional): Добавлять ли кнопку возврата.

    Returns:
        InlineKeyboardMarkup: Дополнительная клавиатура.
    """
    buttons = [
        [
            InlineKeyboardButton(text="Сменить класс", callback_data="set_class"),
            InlineKeyboardButton(
                text="📊 Счётчики", callback_data="count:lessons:main"
            ),
            InlineKeyboardButton(
                text="📜 Изменения", callback_data=f"updates:last:0:{cl}"
            ),
        ],
        [],
    ]

    if home_button:
        buttons[-1].append(InlineKeyboardButton(text="🏠 Домой", callback_data="home"))

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Возращает главную клавиатуру бота.

    Главная клавиатуры предоставляет доступ к самым часто используемым
    разделам бота, таким как получение расписания для класса по
    умолчанию или настройка оповщеений.

    Buttons:
        other => Вызов дополнительной клавиатуры.
        notify => Меню настройки уведомлений пользователя.
        sc:{cl}:today => Получаени расписания на сегодня для класса.

    Args:
        cl (str): Класс для подставновки в клавиатуру.

    Returns:
        InlineKeyboardMarkup: Главная клавиатура бота.
    """
    if cl is None:
        return get_other_keyboard(cl, home_button=False)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔧 Ещё", callback_data="other"),
                InlineKeyboardButton(text="🔔 Уведомления", callback_data="notify"),
                InlineKeyboardButton(
                    text=f"📚 Уроки {cl}", callback_data=f"sc:{cl}:today"
                ),
            ]
        ]
    )

def get_week_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Возращает клавиатуру, для получение расписания на неделю.

    Используется в сообщениях с расписанием уроков.
    Также содержит кнопки для возврата домой и выбора дня недели.

    Buttons:
        home => Возврат на главный экран.
        sc:{cl}:week => Получить расписание на неедлю для класса.
        select_day:{cl} => Выбрать день недели для расписания.

    Args:
        cl (str): Класс для подставновки в клавиатуру.

    Return:
        InlineKeyboardMarkup: Клавиатуру для сообщения с расписанием.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠Домой", callback_data="home"),
                InlineKeyboardButton(text="На неделю", callback_data=f"sc:{cl}:week"),
                InlineKeyboardButton(text="▷", callback_data=f"select_day:{cl}"),
            ]
        ]
    )

def get_sc_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Возаращает клавиатуру, для получения расписания на сегодня.

    Используется в сообщениях с расписанием уроков.
    Также содержит кнопки для возврата домой и выбора дня недели.

    Buttons:
        home => Возврат на главный экран.
        sc:{cl}:today => Получить расписание на сегодня для класса.
        select_day:{cl} => Выбрать день недели для расписания.

    Args:
        cl (str): Класс для подставновки в клавиатуру.

    Return:
        InlineKeyboardMarkup: Клавиатуру для сообщения с расписанием.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠Домой", callback_data="home"),
                InlineKeyboardButton(text="На сегодня", callback_data=f"sc:{cl}:today"),
                InlineKeyboardButton(text="▷", callback_data=f"select_day:{cl}"),
            ]
        ]
    )

def get_select_day_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Возаращает клавиатуру, для выбора дня недели для рассписания.

    Мспользуется в сообщения с расписанием.
    Позволяет выбрать один из дней недели.
    Автоматически подставляя укзааный класс в запрос.

    Buttons:
        sc:{cl}:{0..6} => Получить расписания для укзаанного дня.
        sc:{cl}:today => Получить расписание на сегодня.
        sc:{cl}:week => получить расписание на неделю.

    Args:
        cl (str): Класс для подставноки в клавиатуру.

    Returns:
        InlineKeyboardMarkup: Клаавиатура для выбра дня расписания.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=x, callback_data=f"sc:{cl}:{i}")
                for i, x in enumerate(days_names)
            ],
            [
                InlineKeyboardButton(text="◁", callback_data="home"),
                InlineKeyboardButton(text="Сегодня", callback_data=f"sc:{cl}:today"),
                InlineKeyboardButton(text="Неделя", callback_data=f"sc:{cl}:week"),
            ],
        ]
    )

def get_notify_keyboard(
    sp: SPMessages, enabled: bool, hours: Optional[list[int]] = None
) -> InlineKeyboardMarkup:
    """Возвращет клавиатуру для настройки уведомлений.

    Используется для управления оповещениями.
    Позволяет включить/отключить уведомления.
    Настроить дни для рассылки расписания.
    Сброисить все часы рассылки расписания.

    Buttons:
        notify:on:0 => Включить уведомления бота.
        notify:off:0 => Отключить уведомления бота.
        notify:reset:0 => Сбросить часы для рассылки расписния.
        notify:add:{hour} => Включить рассылку для указанного часа.
        notify:remove:{hour} => Отключить рассылку для указанного часа.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.
        enabled (bool): Включены ли уведомления у пользователя.
        hours (list, optional): В какой час рассылать расписание.

    Returns:
        InlineKeyboardMarkup: Клавиатура для настройки уведомлений.
    """
    inline_keyboard = [[InlineKeyboardButton(text="◁", callback_data="home")]]

    if not enabled:
        inline_keyboard[0].append(
            InlineKeyboardButton(text="🔔 Включить", callback_data="notify:on:0")
        )
    else:
        inline_keyboard[0].append(
            InlineKeyboardButton(text="🔕 Выключить", callback_data="notify:off:0")
        )
        if hours:
            inline_keyboard[0].append(
                InlineKeyboardButton(text="❌ Сброс", callback_data="notify:reset:0")
            )
        hours_line = []
        for i, x in enumerate(range(6, 24)):
            if x % 6 == 0:
                inline_keyboard.append(hours_line)
                hours_line = []

            if x in hours:
                hours_line.append(
                    InlineKeyboardButton(
                        text=f"✔️{x}", callback_data=f"notify:remove:{x}"
                    )
                )
            else:
                hours_line.append(
                    InlineKeyboardButton(text=str(x), callback_data=f"notify:add:{x}")
                )

        if len(hours_line):
            inline_keyboard.append(hours_line)

    return InlineKeyboardMarkup(row_width=6, inline_keyboard=inline_keyboard)

def get_updates_keyboard(
    page: int, updates: list, cl: Optional[str] = None
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для просмотра списка изменений.

    Используется для перемещения по списку изменений в расписании.
    Также может переключать режим просмотре с общего на для класса.

    Buttons:
        home => Возврат к главному меня бота.
        update:back:{page}:{cl} => Перещается на одну страницу назад.
        update:switch:0:{cl} => Переключает режим просмотра расписания.
        update:next:{page}:{cl} => Перемещается на страницу вперёд.

    Args:
        page (int): Номер текущей страницы списка обновлений.
        updates (list): Список всех страниц списка изменений.
        cl (str, optional): Класс для подстановки в клавиатуру.

    Returns:
        InlineKeyboardMarkup: Клавиатура просмотра списка изменений.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠", callback_data="home"),
                InlineKeyboardButton(
                    text="◁", callback_data=f"updates:back:{page}:{cl}"
                ),
                InlineKeyboardButton(
                    text=f"{page+1}/{len(updates)}",
                    callback_data=f"updates:switch:0:{cl}",
                ),
                InlineKeyboardButton(
                    text="▷", callback_data=f"updates:next:{page}:{cl}"
                ),
            ]
        ]
    )


_COUNTERS = (
    ("cl", "По классам"),
    ("days", "По дням"),
    ("lessons", "По урокам"),
    ("cabinets", "По кабинетам"),
)

_TARGETS = (
    ("cl", "Классы"),
    ("days", "Дни"),
    ("lessons", "Уроки"),
    ("cabinets", "Кабинеты"),
    ("main", "Общее"),
)

def get_counter_keyboard(cl: str, counter: str, target: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для просмотра счётчиков расписания.

    Позводяет просматривать счётчики расписания по группам и целям:

    +----------+-------------------------+
    | counter  | targets                 |
    +----------+-------------------------+
    | cl       | days, lessons. cabinets |
    | days     | cl, lessons. cabinets   |
    | lessons  | cl, days, main          |
    | cabinets | cl, days, main          |
    +----------+-------------------------+

    Buttons:
        home => Вернуться к главному сообщению бота.
        count:{counter}:{target} => Переключиться на нужный счётчик.

    Args:
        cl (str): Класс для подстановки в клавиатуру.
        counter (str): Текущая группа счётчиков.
        target (str): Текущий тип просмотра счётчика.

    Returns:
        InlineKeyboardMarkup: Клавиатура для просмотра счётчиков.
    """
    inline_keyboard = [[InlineKeyboardButton(text="◁", callback_data="home")], []]

    for k, v in _COUNTERS:
        if counter == k:
            continue

        inline_keyboard[0].append(
            InlineKeyboardButton(text=v, callback_data=f"count:{k}:{target}")
        )

    for k, v in _TARGETS:
        if target == k or counter == k:
            continue

        if k == "main" and counter not in ["lessons", "cabinets"]:
            continue

        if counter in ["lessons", "cabinets"] and k in ["lessons", "cabinets"]:
            continue

        if counter == "cl" and k == "lessons" and not cl:
            continue

        inline_keyboard[1].append(
            InlineKeyboardButton(text=v, callback_data=f"count:{counter}:{k}")
        )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_tutorial_keyboard(page: int) -> InlineKeyboardMarkup:
    """Клавиатура многостраничного обучения.

    Испльзуется для перемещения между страницами обучения.

    Buttons:
        delete_msg => Удалить сообщение.
        tutorual:{page} => Сменить страницу обучения.

    Args:
        page (int): Текущая страница справки.

    Returns:
        InlineKeyboardMarkup: Клавиатура для перемещения по справке.
    """
    inline_keyboard = []

    # Если это первая страница -> без кнопки назад
    if page == 0:
        inline_keyboard.append([
            InlineKeyboardButton(text="🚀 Начать", callback_data="tutorial:1")
        ])

    # Кнопкеи для управления просмотром
    elif page != len(TUTORIAL_MESSAGES)-1:
        inline_keyboard.append([
            InlineKeyboardButton(text="◁", callback_data=f"tutorial:{page-1}"),
            InlineKeyboardButton(text="🌟 Дальше", callback_data=f"tutorial:{page+1}")
        ])

        for i, x in enumerate(TUTORIAL_MESSAGES[1:-1]):
            if i+1 == page:
                continue
            inline_keyboard.append([InlineKeyboardButton(text=x.splitlines()[0], callback_data=f"tutorial:{i+1}")])

        inline_keyboard.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="delete_msg")])

    # Завершение обучения
    else:
        inline_keyboard.append([
            InlineKeyboardButton(text="🎉 Завершить", callback_data="delete_msg")
        ])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


# Динамический сообщения
# ======================

def get_update_timetag(path: Path) -> int:
    """Получает время последней удачной проверки обнолвений.

    Вспомогательная функция.
    Время успешой проверки используется для проверки скрипта обновлений.
    Если время последней проверки будет дольше одного часа,
    то это повод задуматься о правильноти работы скрипта.

    Args:
        path (Path): Путь к файлу временной метки обновлений.

    Returns:
        int: UNIXtime последней удачной проверки обновлений.
    """
    if not path.exists():
        return 0

    try:
        with open(path) as f:
            return int(f.read())
    except ValueError:
        return 0

def get_status_message(sp: SPMessages, timetag_path: Path) -> str:
    """Отправляет информационно сособщение о работа бота и парсера.

    Инфомарционно сообщения содержит некоторую вспомогательную
    информацию относительно статуса и работаспособности бота.
    К примеру версия бота, время последнего обновления,
    классов и прочее.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.
        timetag_path (Path): Путь к файлу временной метки обновления.

    Returns:
        str: Информацинное сообщение.
    """
    message = sp.send_status()
    message += "\n⚙️ Версия бота: 2.1\n🛠️ Тестер @sp6510"

    timetag = get_update_timetag(timetag_path)
    now = datetime.now().timestamp()

    timedelta = now - timetag
    message += f"\n📀 Проверка было {get_str_timedelta(timedelta)} назад"

    if timedelta > 3600:
        message += "\n⚠️ Автоматическая проверка была более часа назад."
        message += "\nПожалуйста, проверьте работу скрипта."
        message += "\nИли свяжитесь с администратором бота."

    return message


def get_home_message(cl: str) -> str:
    """Отпраляет главное сообщение бота.

    Главное сообщение будет сопровождать пользователя всегда.
    Оно содержит краткую необходимую информацию.

    В шапке сообщения указывается ваш класс по умолчанию.
    В теле сообщения содержится краткая справка по использованию бота.
    Если вы не привязаны к классу, справка немного отличается.

    Args:
        cl (str): Для какого класса получить сообщение.

    Returns:
        str: Готовое главное сообщение бота.
    """
    if cl:
        message = f"💎 Ваш класс {cl}"
    else:
        message = f"🌟 Вы не привязаны к классу."

    message += f"\n\n{HOME_MESSAGE}"
    return message

def get_notify_message(sp: SPMessages) -> str:
    """Отправляет сообщение с информацией о статусе уведомлений.

    Сообщение о статусе уведомлений содержит в себе:
    Включены ли сейчас уведомления.
    Краткая инфомрация об уведомленях.
    В какие часы рассылается расписание уроков.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.

    Returns:
        str: Сообщение с информацией об уведомлениях.
    """
    if sp.user["notifications"]:
        message = "🔔 уведомления включены."
        message += "\nВы получите уведомление, если расписание изменится."
        message += "\n\nТакже вы можете настроить отправку расписания."
        message += "\nВ указанное время бот отправит расписание вашего класса."
        hours = sp.user["hours"]

        if hours:
            message += "\n\nРасписание будет отправлено в: "
            message += ", ".join(map(str, set(hours)))
    else:
        message = "🔕 уведомления отключены."
        message += "\nНикаких лишних сообщений."

    return message

def get_counter_message(sc: Schedule, counter: str, target: str) -> str:
    """Собирает сообщение с результатами работы счётчиков.

    В зависимости от выбранного счётчика использует соответствующую
    функцию счётчика.

    +----------+-----------------------------+
    | counter  | targets                     |
    +----------+-----------------------------+
    | cl       | cl, days, lessons. cabinets |
    | days     | cl, days, lessons. cabinets |
    | lessons  | cl, days. main              |
    | cabinets | cl, days. main              |
    +----------+-----------------------------+

    Args:
        sc (Schedule): Экземпляр расписания уроков.
        counter (str): Тип счётчика.
        target (str): Группа просмтора счётчика.

    Returns:
        str: Сообщение с результаатми счётчика.
    """
    intent = Intent()

    if counter == "cl":
        if target == "lessons":
            intent = Intent.construct(sc, cl=sc.cl)
        res = cl_counter(sc, intent)
    elif counter == "days":
        res = days_counter(sc, intent)
    elif counter == "lessons":
        res = index_counter(sc, intent)
    else:
        res = index_counter(sc, intent, cabinets_mode=True)

    message = f"✨ Счётчик {counter}/{target}:"
    message += send_counter(group_counter_res(res), target=target)
    return message


# Обработчики команд
# ==================

# Простая отправка сообщений -------------------------------------------

@dp.message(Command("cl_features"))
async def restrictions_handler(message: Message) -> None:
    """Отправляет список примуществ при указанном классе."""
    await message.answer(text=CL_FEATURES_MESSAGE)

@dp.message(Command("tutorial"))
async def tutorial_handler(message: Message) -> None:
    """Отправляет интерактивное обучение по составлению запросов."""
    await message.delete()
    await message.answer(
        text=TUTORIAL_MESSAGES[0],
        reply_markup=get_tutorial_keyboard(0)
    )

@dp.message(Command("info"))
async def info_handler(message: Message, sp: SPMessages) -> None:
    """Сообщение о статусе рабты бота и парсера."""
    await message.answer(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(sp.user["class_let"]),
    )

# Help команда ---------------------------------------------------------

@dp.message(Command("help", "start"))
async def start_handler(message: Message, sp: SPMessages) -> None:
    """Отправляет сообщение справки и главную клавиатуру.
    Если класс не указан, отпраляет сообщение указания класса."""
    await message.delete()
    if sp.user["set_class"]:
        await message.answer(
            text=get_home_message(sp.user["class_let"]),
            reply_markup=get_main_keyboard(sp.user["class_let"]),
        )
    else:
        await message.answer(text=SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP)

# Изменение класса пользователя ----------------------------------------

@dp.message(Command("set_class"))
async def set_class_command(message: Message, sp: SPMessages) -> None:
    """Изменяет класс или удаляет данные о пользователе."""
    sp.reset_user()
    await message.answer(text=SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP)

@dp.message(Command("pass"))
async def pass_handler(message: Message, sp: SPMessages) -> None:
    """Отвязывает пользователя от класса по умолчанию."""
    sp.set_class(None)
    await message.answer(
        text=get_home_message(sp.user["class_let"]),
        reply_markup=get_main_keyboard(sp.user["class_let"]),
    )

# Получить расписание уроков -------------------------------------------

@dp.message(Command("sc"))
async def sc_handler(message: Message, sp: SPMessages) -> None:
    """Отправляет расписание уроков пользовтелю.
    Отправляет предупреждение, если у пользователя не укзаан класс.
    """
    if sp.user["class_let"]:
        await message.answer(
            text=sp.send_today_lessons(Intent()),
            reply_markup=get_week_keyboard(sp.user["class_let"]),
        )
    else:
        await message.answer(
            text="⚠️ Для быстрого получения расписания вам нужно указать класс."
        )

# Переход к разделам бота ----------------------------------------------

@dp.message(Command("updates"))
async def updates_handler(message: Message, sp: SPMessages) -> None:
    """Оправляет последную страницу списка изменений в расписании."""
    updates = sp.sc.updates
    markup = get_updates_keyboard(max(len(updates) - 1, 0), updates)
    if len(updates):
        text = send_update(updates[-1])
    else:
        text = "Нет новых обновлений."

    await message.answer(text=text, reply_markup=markup)

@dp.message(Command("counter"))
async def counter_handler(message: Message, sp: SPMessages) -> None:
    """Переводит в меню просмора счётчиков расписания."""
    await message.answer(
        text=get_counter_message(sp.sc, "lessons", "main"),
        reply_markup=get_counter_keyboard(sp.user["class_let"], "lessons", "main"),
    )

@dp.message(Command("notify"))
async def notify_handler(message: Message, sp: SPMessages):
    """Переводит в менюя настройки уведомлений."""
    enabled = sp.user["notifications"]
    hours = sp.user["hours"]
    await message.answer(
        text=get_notify_message(sp),
        reply_markup=get_notify_keyboard(sp, enabled, hours),
    )



# Обработчик текстовых запросов
# =============================

def process_request(sp: SPMessages, request_text: str) -> Optional[str]:
    """Обрабатывает текстовый запрос к расписанию.

    Преобразует входящий текст в набор намерений или запрос.
    Производит поиск по урокам/кабинетам
    или получает расписание, в зависимости от намерений.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.
        request_text (str): Текст запроса к расписанию.

    Returns:
        str: Ответ от генератора сообщений.
    """
    intent = Intent.parse(sp.sc, request_text.split())

    # Чтобы не превращать бота в машину для спама
    # Будет использоваться последний урок/кабинет из фильтра
    if len(intent.cabinets):
        res = sp.sc.search(list(intent.cabinets)[-1], intent, True)
        text = send_search_res(intent, res)

    elif len(intent.lessons):
        res = sp.sc.search(list(intent.lessons)[-1], intent, False)
        text = send_search_res(intent, res)

    elif intent.cl or intent.days:
        text = sp.send_lessons(intent) if intent.days else sp.send_today_lessons(intent)
    else:
        text = None

    return text

@dp.message()
async def main_handler(message: Message, sp: SPMessages) -> None:
    """Главный обработчик сообщений бота.
    Перенаправляет входящий текст в запросы к расписанию.
    Устанавливает калсс, если он не установлен.
    """
    if message.text is None:
        return

    text = message.text.strip().lower()

    # Если у пользователя установлек класс -> создаём запрос
    if sp.user["set_class"]:
        answer = process_request(sp, text)

        if answer is not None:
            await message.answer(text=answer)
        elif message.chat.type == "private":
            await message.answer(text="👀 Кажется это пустой запрос...")

    elif text in sp.sc.lessons:
        logger.info("Set class {}", text)
        sp.set_class(text)
        await message.answer(
            text=get_home_message(so.user["class_let"]),
            reply_markup=get_main_keyboard(sp.user["class_let"])
        )

    elif message.chat.type == "private":
        text = "👀 Такого класса не существует."
        text += f"\n💡 Доступныe классы: {', '.join(sp.sc.lessons)}"
        await message.answer(text=text)


# Обработчик Callback запросов
# ============================

@dp.callback_query(F.data == "delete_msg")
async def delete_msg_callback(query: CallbackQuery) -> None:
    await query.message.delete()

@dp.callback_query(F.data == "home")
async def home_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Возаращает в главное меню."""
    await query.message.edit_text(
        text=get_home_message(sp.user["class_let"]),
        reply_markup=get_main_keyboard(sp.user["class_let"])
    )

@dp.callback_query(F.data == "other")
async def other_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Возвращает сообщение статуса и доплнительную клавиатуру."""
    await query.message.edit_text(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(sp.user["class_let"]),
    )

@dp.callback_query(F.data == "cl_features")
async def restrictions_callback(query: CallbackQuery) -> None:
    """Возвращает сообщение с преимуществами указанного класса."""
    await query.message.edit_text(
        text=CL_FEATURES_MESSAGE, reply_markup=BACK_SET_CL_MARKUP
    )

@dp.callback_query(F.data == "set_class")
async def set_class_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Сбрасывает класс пользователя."""
    sp.reset_user()
    await query.message.edit_text(
        text=SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP
    )

@dp.callback_query(F.data == "pass")
async def pass_class_callback(query: CallbackData, sp: SPMessages) -> None:
    """Отвязывает пользователя от класса."""
    sp.set_class(None)
    await query.message.edit_text(
        text=get_home_message(sp.user["class_let"]),
        reply_markup=get_main_keyboard(sp.user["class_let"])
    )


class ScCallback(CallbackData, prefix="sc"):
    """Используется при получении расписания.

    cl (str): Класс для которого получить расписание.
    day (str): Для какого дня получить расписание.

    - 0-5: понедельник - суббота.
    - today: Получить расписание на сегодня/завтра.
    - week: Получить расписание на всю неделю."""
    cl: str
    day: str

@dp.callback_query(ScCallback.filter())
async def sc_callback(
    query: CallbackQuery, callback_data: ScCallback, sp: SPMessages
) -> None:
    """Отпарвляет расписание уроков для класса в указанный день."""
    if callback_data.day == "week":
        text = sp.send_lessons(
            Intent.construct(sp.sc, days=[0, 1, 2, 3, 4, 5], cl=callback_data.cl)
        )
        reply_markup = get_sc_keyboard(callback_data.cl)
    elif callback_data.day == "today":
        text = sp.send_today_lessons(Intent.construct(sp.sc, cl=callback_data.cl))
        reply_markup = get_week_keyboard(callback_data.cl)
    else:
        text = sp.send_lessons(
            Intent.construct(sp.sc, cl=callback_data.cl, days=int(callback_data.day))
        )
        reply_markup = get_week_keyboard(callback_data.cl)

    await query.message.edit_text(text=text, reply_markup=reply_markup)


class SelectDayCallback(CallbackData, prefix="select_day"):
    """Используется для выбора дня недели при получении расписания.

    cl (str): Для какого класса получить расписание.
    """
    cl: str

@dp.callback_query(SelectDayCallback.filter())
async def select_day_callback(
    query: CallbackQuery, callback_data: ScCallback, sp: SPMessages
) -> None:
    """Отобржает клавиатуру для выбора дня расписания уроков."""
    await query.message.edit_text(
        text=f"📅 на ...\n🔶 Для {callback_data.cl}:",
        reply_markup=get_select_day_keyboard(callback_data.cl),
    )


class NotifyCallback(CallbackData, prefix="notify"):
    """Испольуется при настройке уведомлений пользователя.

    action (str): Какое выполнить действие: add, remove, on, off.
    hour (int): Для какого часа применять изменение.

    - on: Включить увдомления.
    - off: Откплючить уведомления.
    - add: Включить рассылку расписания в указанный час.
    - remove: Отключить рассылку расписания в указанный час.
    """
    action: str
    hour: int

@dp.callback_query(F.data == "notify")
async def notify_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Отправляет настройки увдеомлений."""
    enabled = sp.user["notifications"]
    hours = sp.user["hours"]
    await query.message.edit_text(
        text=get_notify_message(sp),
        reply_markup=get_notify_keyboard(sp, enabled, hours),
    )

@dp.callback_query(NotifyCallback.filter())
async def notify_mod_callback(
    query: CallbackQuery, sp: SPMessages, callback_data: NotifyCallback
) -> None:
    """Применяет настройки к уведомлениям."""
    if callback_data.action == "on":
        sp.user["notifications"] = True

    elif callback_data.action == "off":
        sp.user["notifications"] = False

    elif callback_data.action == "add":
        if callback_data.hour not in sp.user["hours"]:
            sp.user["hours"].append(callback_data.hour)

    elif callback_data.action == "remove":
        if callback_data.hour in sp.user["hours"]:
            sp.user["hours"].remove(callback_data.hour)

    elif callback_data.action == "reset":
        sp.user["hours"] = []

    sp.save_user()
    enabled = sp.user["notifications"]
    hours = sp.user["hours"]

    await query.message.edit_text(
        text=get_notify_message(sp),
        reply_markup=get_notify_keyboard(sp, enabled, hours),
    )


class UpdatesCallback(CallbackData, prefix="updates"):
    """Используется при просмотре списка изменений.

    action (str): back, mext, last, switch.

    - back: Переместитсья на одну страницу назад.
    - next: Переместиться на одну страницу вперёд.
    - last: Переместиться на последную страницу расписания.
    - swith: Переключить режим просмотра с общего на для класса.

    page (int): Текущаю страница списка изменений.
    cl (str): Для какого класса отображать список изменений.
    """
    action: str
    page: int
    cl: str

@dp.callback_query(UpdatesCallback.filter())
async def updates_callback(
    query: CallbackQuery, sp: SPMessages, callback_data: NotifyCallback
) -> None:
    text = "🔔 Изменения "

    # Смена режима просмотра: только для класса/всего расписния
    if callback_data.action == "switch":
        cl = sp.user["class_let"] if callback_data.cl == "None" else None
    else:
        cl = None if callback_data.cl == "None" else callback_data.cl

    # Дополняем шапку сообщения
    if cl is not None and sp.user["class_let"]:
        text += f"для {cl}:\n"
        intent = Intent.construct(sp.sc, cl)
    else:
        text += "в расписании:\n"
        intent = Intent()

    # Полчуаем список изменений
    updates = sp.sc.get_updates(intent)
    i = max(min(int(callback_data.page), len(updates) - 1), 0)

    if len(updates):
        if callback_data.action in ("last", "switch"):
            i = len(updates) - 1

        elif callback_data.action == "next":
            i = (i + 1) % len(updates)

        elif callback_data.action == "back":
            i = (i - 1) % len(updates)

        update_text = send_update(updates[i], cl=cl)
        if len(update_text) > 4000:
            text += "\n < слишком много изменений >"
        else:
            text += update_text

    else:
        text += "Нет новых обновлений."

    await query.message.edit_text(
        text=text, reply_markup=get_updates_keyboard(i, updates, cl)
    )


class CounterCallback(CallbackData, prefix="count"):
    """Используется в клавиатуре просмотра счётчиков расписания.

    counter (str): Тип счётчика.
    target (str): Цль для отображения счётчика.

    +----------+-------------------------+
    | counter  | targets                 |
    +----------+-------------------------+
    | cl       | days, lessons. cabinets |
    | days     | cl, lessons. cabinets   |
    | lessons  | cl, days, main          |
    | cabinets | cl, days, main          |
    +----------+-------------------------+
    """
    counter: str
    target: str

@dp.callback_query(CounterCallback.filter())
async def counter_callback(
    query: CallbackQuery, sp: SPMessages, callback_data: NotifyCallback
) -> None:
    """Клавитура для просмотра счётчиков расписания."""
    counter = callback_data.counter
    target = callback_data.target

    if counter == target:
        target = None

    if counter == "cl" and target == "lessons" and not sp.user["class_let"]:
        target = None

    await query.message.edit_text(
        text=get_counter_message(sp.sc, counter, target),
        reply_markup=get_counter_keyboard(sp.user["class_let"], counter, target),
    )



class TutorlailCallback(CallbackData, prefix="tutorial"):
    """Используется при просмотре постраничной справки.

    page (int): Текущая страница справки.
    """
    page: int

@dp.callback_query(TutorlailCallback.filter())
async def tutorail_callback(query: CallbackQuery,
    callback_data: TutorlailCallback) -> None:
    """Отправляет страницу интерактивного обучения."""
    await query.message.edit_text(
        text=TUTORIAL_MESSAGES[callback_data.page],
        reply_markup=get_tutorial_keyboard(callback_data.page)
    )


@dp.callback_query()
async def callback_handler(query: CallbackQuery) -> None:
    """Перехватывает все прочие callback_data."""
    logger.warning("Unprocessed query - {}", query.data)


@dp.errors()
async def error_handler(exception: ErrorEvent) -> None:
    logger.exception(exception.exception)


# Запуск бота
# ===========

async def main() -> None:
    bot = Bot(TELEGRAM_TOKEN)
    logger.info("Bot started.")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
