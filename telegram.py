"""Telegram-бот для доступа к SPMessages.

Не считая некоторых ограничений в настройке "намерений" (Intents)
боя полностью реализует доступ ко всем разделам SPMessages.

Команды бота для BotFather
--------------------------

sc - Уроки на сегодня
updates - Изменения в расписании
counter - Счётчики уроков/кабинетов
notify - Настроить уведомления
set_class - Изменить класс
help - Главное меню
typehint - Как писать запросы
info - Информация о боте

Author: Milinuri Nirvalen
Ver: 2.0
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
            InlineKeyboardButton(text="Ограничения", callback_data="restrictions"),
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

HOME_MESSAGE = """💡 Некоторые примеры запросов:
-- 7в 6а на завтра
-- уроки 6а на вторник ср
-- расписание на завтра для 8б
-- 312 на вторник пятницу
-- химия 228 6а вторник

🏫 В запросах вы можете использовать:
* Урок/Кабинет: Получить все его упоминания.

* Классы: для которого нужно расписание.
-- Если класс не указан, подставляется ваш класс.
-- "?": для явной подставновки вашего класса.

* Дни недели:
-- Если день не указан - на сегодня/завтра.
-- Понедельник-суббота (пн-сб).
-- Сегодня, завтра, неделя.

🌟 Как писать запросы? /typehint"""

NO_CL_HOME_MESSAGE = """💡 Некоторые примеры запросов:
-- 7в 6а на завтра
-- уроки 6а на вторник ср
-- расписание на завтра для 8б
-- 312 на вторник пятницу
-- химия 228 6а вторник

🏫 В запросах вы можете использовать:
* Урок/Кабинет: Получить все его упоминания.
* Классы: для которых нужно расписание.
* Дни недели:
-- Если день не указан - на сегодня/завтра.
-- Понедельник-суббота (пн-сб).
-- Сегодня, завтра, неделя.

🌟 /typehint - Как писать запросы?"""

SET_CLASS_MESSAGE = """
Для полноценной работы желательно указать ваш класс.
Для быстрого просмотра расписания и списка изменений.

🌟 Вы можете пропустить выбор класса нажав кнопку (/pass).
Но это накладывает некоторые ограничения.
Прочитать об ограничениях можно нажав кнопку (/restrictions).

Чтобы указать класс следующим сообщением введите ваш класс ("1а").

💡 Вы можете сменить класс в дальнейшем:
-- через команду /set_class.
-- Ещё -> сменить класс."""


RESTRICTIONS_MESSAGE = """🚫 Ограничения не привязанного класса.
Всё перечисленное будет недоступно, пока не указан класс:

-- Быстрое получение расписания для класса.
-- Подстановка класса в текстовых запросах.
-- Просмотр списка изменений для класса.
-- Счётчик "по классам/уроки".
-- Система уведомлений.

🌟 Остальные функции работают одинаково."""

TYPEHINT_MESSAGE = """
💡 Как писать запросы?
На самом деле всё намно-о-ого легче.
Просто прочтите эти 5 пунктов и поймите суть.

1. "Посторонние" слова будут игнорироваться (можете их не писать).
-- "Уроки на завтра" ➜ "завтра".
-- "Расписание для 9в на вторник" ➜ "9в вторник".
-- "матем 8в" = "8в матем" ➜ порядок НЕ имеет значение.

2. Просто укажите класс, чтобы получить его расписание.
-- "7а" ➜ Отправит расписание для 7а на сегодня/завтра.
-- "7г 6а" ➜ Сразу для нескольких классов.

3. Вы можете добавить день.
-- "вт" ➜ Расписание для вашего класса по умолчанию на вторник.
-- "уроки для 5г на среду" ➜ "5г среда" ➜ Для 5г на среду.

4. Укажите точное название урока, чтобы найти все его упоминания.
-- "матем" ➜ Вся математика на неделю.
-- "матем вторник 10а" ➜ Вы можете уточнить запрос классом и днём.

5. Укажите кабинет, чтобы увидеть расписание от его лица.
-- "328" ➜ Всё что проходит в 328 кабинете за неделю.
-- "312 литер вторник 7а" ➜ Можно уточнить классом, днём, уроком."""


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
    message += "\n⚙️ Версия бота: 2.0\n🛠️ Тестер @sp6510"

    timetag = get_update_timetag(timetag_path)
    now = datetime.now().timestamp()

    timedelta = now - timetag
    message += f"\n📀 Проверка было {get_str_timedelta(timedelta)} назад"

    if timedelta > 3600:
        message += "\n⚠️ Автоматическая проверка была более часа назад."
        message += "\nПожалуйста, проверьте работу скрипта."
        message += "\nИли свяжитесь с администратором бота."

    return message


def get_home_message(sp: SPMessages) -> str:
    """Отпраляет главное сообщение бота.

    Главное сообщение будет сопровождать пользователя всегда.
    Оно содержит краткую необходимую информацию.

    В шапке сообщения указывается ваш класс по умолчанию.
    В теле сообщения содержится краткая справка по использованию бота.
    Если вы не привязаны к классу, справка немного отличается.

    Args:
        sp (SPMessages): Экземпляр генератор сообщений.

    Returns:
        str: Готовое главное сообщение бота.
    """
    cl = sp.user["class_let"]

    if cl:
        message = f"💎 Ваш класс {cl}.\n\n{HOME_MESSAGE}"
    elif sp.user["set_class"]:
        message = f"🌟 Вы не привязаны к классу.\n\n{NO_CL_HOME_MESSAGE}"
    else:
        message = "👀 Хитро, но это так не работает."
        message += "\n💡 Установить класс по умолчанию: /set_class"

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
    intent = Intent.new()

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

@dp.message(Command("restrictions"))
async def restrictions_handler(message: Message) -> None:
    """Отправляет список ограничений на использование бота
    без указанного класса по умолчанию.
    """
    await message.answer(text=RESTRICTIONS_MESSAGE)

@dp.message(Command("typehint"))
async def typehint_handler(message: Message) -> None:
    """Отпаврляет подсказку по использованию бота."""
    await message.answer(text=TYPEHINT_MESSAGE)

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
    if sp.user["set_class"]:
        await message.answer(
            text=get_home_message(sp),
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
        text=get_home_message(sp),
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
            text=sp.send_today_lessons(Intent.new()),
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
async def notyfi_handler(message: Message, sp: SPMessages):
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
        markup = get_main_keyboard(sp.user["class_let"])
        await message.answer(text=get_home_message(sp), reply_markup=markup)

    elif message.chat.type == "private":
        text = "👀 Такого класса не существует."
        text += f"\n💡 Доступных классы: {', '.join(sp.sc.lessons)}"
        await message.answer(text=text)


# Обработчик Callback запросов
# ============================

@dp.callback_query(F.data == "home")
async def home_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Возаращает в главное меню."""
    await query.message.edit_text(
        text=get_home_message(sp), reply_markup=get_main_keyboard(sp.user["class_let"])
    )

@dp.callback_query(F.data == "other")
async def other_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Возвращает сообщение статуса и доплнительную клавиатуру."""
    await query.message.edit_text(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(sp.user["class_let"]),
    )

@dp.callback_query(F.data == "restrictions")
async def restrictions_callback(query: CallbackQuery) -> None:
    """Возвращает сообщение с ограничениями при отсутствии класса."""
    await query.message.edit_text(
        text=RESTRICTIONS_MESSAGE, reply_markup=BACK_SET_CL_MARKUP
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
        text=get_home_message(sp), reply_markup=get_main_keyboard(sp.user["class_let"])
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
        intent = Intent.new()

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


@dp.callback_query()
async def callback_handler(query: CallbackQuery) -> None:
    """Перехватывает все прочие callback_data."""
    logger.warning("Unprocessed query - {}", query.data)


# Обработчик ошибок
# =================

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
