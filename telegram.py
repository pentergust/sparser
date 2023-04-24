"""
Telegram бот для доступа к SPMessages.

Команды бота для BotFather:
sc - Уроки на сегодня
updates - Изменения в расписании
counter - Счётчики уроков/кабинетов
notify - Настроить уведомления
set_class - Изменить класс
help - Главное меню
info - Информация о боте

TODO: Разделить код бота на несколько файлов

Author: Milinuri Nirvalen
Ver: 1.13 (sp v5.3)
"""

from sp.counters import cl_counter
from sp.counters import days_counter
from sp.counters import group_counter_res
from sp.counters import index_counter
from sp.filters import Filters
from sp.filters import construct_filters
from sp.filters import parse_filters
from sp.parser import Schedule
from sp.spm import SPMessages
from sp.spm import send_counter
from sp.spm import send_update
from sp.utils import load_file

from contextlib import suppress
from pathlib import Path
from typing import Optional

from aiogram import Bot
from aiogram import Dispatcher
from aiogram import executor
from aiogram import types
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageCantBeDeleted
from aiogram.utils.exceptions import MessageNotModified
from gotify import AsyncGotify
from loguru import logger


config = load_file(Path("sp_data/telegram.json"),
    {"token": "YOUR TG API TOKEN",
    "gotify": {
        "enabled": False,
        "base_url": None,
        "app_token": None
    }})

if config["gotify"]["enabled"]:
    gotify = AsyncGotify(
        base_url=config["gotify"]["base_url"],
        app_token=config["gotify"]["app_token"])
else:
    gotify = None

bot = Bot(config["token"])
dp = Dispatcher(bot)
logger.add("sp_data/telegram.log")
days_names = ["понедельник", "вторник", "среда", "четверг", "пятница",
              "суббота", "сегодня", "неделя"]


# Тексты сообщений
# ================

HOME_MESSAGE = """💡 Некоторые примеры запросов:
-- 7в 6а на завтра
-- уроки 6а на вторник ср
-- расписание на завтра для 8б
-- 312 на вторник пятницу
-- химия 228 6а вторник

🏫 В запросах вы можете использовать:
Урок/Кабинет: Получить все его упоминания.

Классы: для которого нужно расписание.
-- Если класс не укзаан, подставляется ваш класс.
-- "?": для явной подставновки вашего класса.

Дни недели:
-- Если день не указан - на сегодня/завтра.
-- Понедельник-суббота (пн-сб).
-- Сегодня, завтра, неделя.

🌟 Порядок и форма аргументов не важны, балуйтесь!"""

INFO_MESSAGE = """
:: Версия бота: 1.13

👀 Сопровождающий @milinuri."""

SET_CLASS_MESSAGE = """
Для полноценной работы желательно указать ваш класс.
Для быстрого просмотра расписания и списка изменений.

🌟 Вы можете пропустить выбор класса командой /pass.
Но это накладывает некоторые ограничения.
Прочитать об ограничениях можно по команде /restrictions.

Способы указать класс:
-- В переписке с ботом: следуюшим сообщением введите ваш класс ("1а").
-- /set_class в ответ на сообщение с классом ("7а").
-- /set_class [класс] -- с явным указание класса.

💡 Вы можете сменить класс в дальнейшем:
-- через команду /set_class.
-- Ещё -> сменить класс."""

RESTRICTIONS_MESSAGE = """Всё перечисленное будет недоступно:

-- Кнопка получения расписания в справке.
-- Подстановка класса в запросах.
-- просмотр списка изменений для класса.
-- Счётчик "по классам/уроки".
-- Система уведомлений.

🌟 На этом все отличия заканчиваются."""


# Определение клавиатур бота
# ==========================

to_home_markup = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text="🏠Домой", callback_data="home"))

week_markup = [{"home": "🏠", "week {cl}": "На неделю", "select_day {cl}":"▷"}]
sc_markup = [{"home": "🏠", "sc {cl}": "На сегодня", "select_day {cl}": "▷"}]
home_murkup = [{"other": "🔧Ещё",
                "notify info": "🔔Уведомления",
                "sc {cl}": "📚Уроки {cl}"}]
other_markup = [{"home": "◁", "set_class": "Сменить класс"},
                {"count lessons main": "📊Счётчики",
                "updates last 0 None": "📜Изменения"}]


def markup_generator(sp: SPMessages, pattern: dict, cl: Optional[str]=None,
        exclude: Optional[str]=None, row_width: Optional[int]=3
        ) -> InlineKeyboardMarkup:
    """Собиарает inline-клавиатуру по шаблону.

    Args:
        sp (SPMessages): Описание
        cl (str, optional): Выбранный класс для передачи в callback_data
        pattern (dict): Шаблон для сборки клавиатуры
        exclude (str, optional): Ключ кнопки для исключения
        row_width (int, optional): Количество кнопок в одной строке

    Returns:
        InlineKeyboardMarkup: Собранная клавиатура
    """
    markup = InlineKeyboardMarkup(row_width)
    cl = cl if cl is not None else sp.user["class_let"]

    for group_row in pattern:
        row = []

        for callback_data, text in group_row.items():
            if exclude is not None and callback_data == exclude:
                continue

            if cl is None and "{cl}" in callback_data:
                continue

            if cl is None and "{cl}" in text:
                continue

            callback_data = callback_data.replace("{cl}", cl or "")
            text = text.replace("{cl}", cl or "")

            row.append(InlineKeyboardButton(text= text, callback_data= callback_data))
        markup.row(*row)

    return markup

def gen_updates_markup(update_index: int, updates: list,
                       cl: Optional[str]=None) -> InlineKeyboardMarkup:
    """Собирает inline-клввиатуру для просмотра списка изменений
    в расписании.

    Args:
        update_index (int): Номер текущей страницы обновлений
        updates (list): Список всех страниц
        cl (str, optional): Для какого класс собрать клавиатуру

    Returns:
        InlineKeyboardMarkup: Готовая inline-клавиатура
    """
    markup = InlineKeyboardMarkup(row_width=4)
    markup_pattern = {
            "home": "🏠",
            "updates back": "◁",
            "updates switch": f"{update_index+1}/{len(updates)}",
            "updates next": "▷",
        }

    for k, v in markup_pattern.items():
        k += f" {update_index} {cl}"
        markup.insert(InlineKeyboardButton(text=v, callback_data=k))

    return markup

def select_day_markup(cl: str) -> InlineKeyboardMarkup:
    """Собирает inline-клавиатуру для выбора дня недели.

    Args:
        cl (str): Уточнение для какого класса выбиратеся день недели

    Returns:
        InlineKeyboardMarkup: inline-клавиатура для выбора для недели
    """
    markup = InlineKeyboardMarkup()
    for i, x in enumerate(days_names):
        markup.insert(
            InlineKeyboardButton(text=x, callback_data=f"sc_day {cl} {i}"))
    return markup

def gen_counters_markup(sp: SPMessages, counter: str, target: str) -> InlineKeyboardMarkup:
    """Собирает клавиатуру для счётчиков.

    Args:
        sp (SPMessages): Генератор сообщений
        counter (str): Название текущего счётчика
        target (str): Названеи текущего режима просмотра

    Returns:
        InlineKeyboardMarkup: Собранная клавиатура
    """
    markup = InlineKeyboardMarkup(row_width=4)

    row = [InlineKeyboardButton(text="◁", callback_data="home")]
    counters = {"cl": "по классам",
                "days": "По дням",
                "lessons": "По урокам",
                "cabinets": "По кабинетам"}

    for k, v in counters.items():
        if counter == k:
            continue

        row.append(InlineKeyboardButton(text=v,
                                        callback_data=f"count {k} {target}"))
    markup.add(*row)

    row = []
    targets = {"cl": "Классы",
               "days": "дни",
               "lessons": "Уроки",
               "cabinets": "Кабинеты",
               "main": "Общее"}

    for k, v in targets.items():
        if target == k:
            continue

        if counter == k:
            continue

        if k == "main" and counter not in ["lessons", "cabinets"]:
            continue

        if counter in ["lessons", "cabinets"] and k in ["lessons", "cabinets"]:
            continue

        if counter == "cl" and k == "lessons" and not sp.user["class_let"]:
            continue

        row.append(InlineKeyboardButton(text=v,
                                        callback_data=f"count {counter} {k}"))
    markup.add(*row)

    return markup

def get_notifications_markup(sp: SPMessages, enabled: bool,
        hours: Optional[list[int]] = None) -> InlineKeyboardMarkup:
    """Возвращетс клавиатуру для настройки уведомлений.

    Args:
        sp (SPMessages): Генератор сообщенийц
        enabled (bool): Включены ли уведомления
        hours (list, optional): В какой час отправлять уведомления

    Returns:
        InlineKeyboardMarkup: Готовая клавитура для настройки
    """
    inline_keyboard = [[InlineKeyboardButton(text="◁", callback_data="home")]]

    if not enabled:
        inline_keyboard[0].append(
            InlineKeyboardButton(text="🔔Включить", callback_data="notify on")
        )

    else:
        inline_keyboard[0].append(
            InlineKeyboardButton(text="🔕Выключить", callback_data="notify off")
        )

        if hours:
            inline_keyboard[0].append(
                InlineKeyboardButton(text="❌", callback_data="notify reset")
            )

        hours_line = []
        for i, x in enumerate(range(6, 24)):
            if str(x) in hours:
                continue

            if x % 6 == 0:
                inline_keyboard.append(hours_line)
                hours_line = []

            hours_line.append(
                InlineKeyboardButton(text=x, callback_data=f"notify add {x}")
            )

        if len(hours_line):
            inline_keyboard.append(hours_line)

    return InlineKeyboardMarkup(row_width=6, inline_keyboard=inline_keyboard)

def get_home_markup(sp: SPMessages) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для сообщения справки.
    Если класс не указан, возвращает клавиатуру допллнительных опций.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений

    Returns:
        InlineKeyboardMarkup: Клавиатуру для сообщения справки
    """
    cl = sp.user["class_let"]

    if cl is None:
        markup = markup_generator(sp, other_markup, exclude="home")
    else:
        markup = markup_generator(sp, home_murkup)

    return markup


# Вспомогательные функции
# =======================

def send_notification_message(sp: SPMessages, enabled: bool,
        hours: Optional[list[int]] = None) -> str:
    """Отправляет сообщение с информацией об уведомлениях.

    Args:
        sp (SPMessages): Генератор сообщений
        enabled (bool): Включены ли уведомления
        hours (list[int], optional): В какоие часы отправлять расписание

    Returns:
        str: Сообщение с информацией об уведомлениях.
    """
    message = "Вы получени уведомление, если расписание изменится.\n"

    if enabled:
        message += "\n🔔 уведомления включены."
        message += "\n\nТакже вы можеете настроить отправку расписания."
        message += "\nВ указанное время бот отправит расписание вашего класса."

        if hours:
            message += "\n\nРасписани будет отправлено в: "
            message += ", ".join(map(str, set(hours)))
    else:
        message += "\n🔕 уведомления отключены."

    return message

def get_counter_message(sc: Schedule, counter: str, target: str) -> str:
    """Собирает сообщение с результатами работы счётчиков.

    Args:
        sc (Schedule): Расписание уроков
        counter (str): Тип счётчика
        target (str): Режим просмотра счётчика

    Returns:
        str: Готовое сообщение
    """
    flt = construct_filters(sc)

    if counter == "cl":
        if target == "lessons":
            flt = construct_filters(sc, cl=sc.cl)
        res = cl_counter(sc, flt)
    elif counter == "days":
        res = days_counter(sc, flt)
    elif counter == "lessons":
        res = index_counter(sc, flt)
    else:
        res = index_counter(sc, flt, cabinets_mode=True)

    groups = group_counter_res(res)
    message = f"✨ Счётчик {counter}/{target}:"
    message += send_counter(groups, target=target)
    return message

def send_home_message(sp: SPMessages) -> str:
    """Отпавляет сообщение со справкой об использовании бота.

    Args:
        sp (SPMessages): Генератор сообщений

    Returns:
        str: Готовое сообщение
    """
    cl = sp.user["class_let"]

    if cl:
        message = f"💎 Ваш класс {cl}."
    elif sp.user["set_class"]:
        message = "🌟 Вы не привязаны к классу."
    else:
        message = "👀 Хитро, но так не работает."
        message += "\n💡 Установить класс по умолчанию: /set_class"

    message += "\n\n"
    message += HOME_MESSAGE

    return message

def process_request(sp: SPMessages, request_text: str) -> str:
    """Обрабатывает текстовый запрос к расписанию.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений
        request_text (str): Текст запроса к расписанию

    Returns:
        str: Результат запроса к расписанию
    """

    flt = parse_filters(sp.sc, request_text.split())

    # Чтобы не превращать бота в машину для спама
    # Будет использоваться последний урок/кабинет из фильтра
    if len(flt.cabinets):
        res = sp.search_cabinet(list(flt.cabinets)[-1], flt)
    elif len(flt.lessons):
        res = sp.search_lesson(list(flt.lessons)[-1], flt)
    elif flt.cl or flt.days:
        text = sp.send_lessons(flt) if flt.days else sp.send_today_lessons(flt)
    else:
        text = "👀 Кажется это пустой запрос..."

    return text


# Опеределение команд бота
# ========================

@dp.message_handler(commands=["start", "help"])
async def start_command(message: types.Message) -> None:
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
    with suppress(MessageCantBeDeleted):
        await message.delete()

    if sp.user["set_class"]:
        markup = get_home_markup(sp)
        await message.answer(text=send_home_message(sp), reply_markup=markup)
    else:
        await message.answer(text=SET_CLASS_MESSAGE)

@dp.message_handler(commands=["set_class"])
async def set_class_command(message: types.Message) -> None:
    """Изменяет класс или удаляет данные о пользователе."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)

    if message.reply_to_message and message.reply_to_message.from_user.id != bot.id:
        content = message.reply_to_message.text
    else:
        content = message.get_args()

    if content:
        if content in sp.sc.lessons:
            sp.set_class(content)
            text = f"✏️ Класс изменён на {content}"
        else:
            text = "👀 Такого класса не существует."
    else:
        sp.reset_user()
        text = SET_CLASS_MESSAGE

    await message.answer(text=text)

@dp.message_handler(commands=["pass"])
async def pass_commend(message: types.Message) -> None:
    """Отвязывает пользователя от класса."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
    if not sp.user["set_class"]:
        sp.user["set_class"] = True
        sp.save_user()
        markup = get_home_markup(sp)
        await message.answer(text=send_home_message(sp), reply_markup=markup)

@dp.message_handler(commands=["restrictions"])
async def restrictions_commend(message: types.Message) -> None:
    await message.answer(text=RESTRICTIONS_MESSAGE)

@dp.message_handler(commands=["info"])
async def info_command(message: types.Message) -> None:
    """Отправляет статус парсера и бота."""
    sp = SPMessages(str(message.chat.id))
    await message.answer(text=sp.send_status()+INFO_MESSAGE,
                         reply_markup=to_home_markup)

@dp.message_handler(commands=["updates"])
async def updates_command(message: types.Message) -> None:
    """Оправляет список изменений в расписании/"""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
    updates = sp.sc.updates
    markup = gen_updates_markup(max(len(updates)-1, 0), updates)
    if len(updates):
        text = send_update(updates[-1])
    else:
        text = "Нет новых обновлений."

    await message.answer(text=text, reply_markup=markup)

@dp.message_handler(commands=["counter"])
async def counter_command(message: types.Message) -> None:
    """Отправялет счётчик уроков/кабинетов."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
    text = get_counter_message(sp.sc, "lessons", "main")
    markup = gen_counters_markup(sp, "lessons", "main")
    await message.answer(text=text, reply_markup=markup)

@dp.message_handler(commands=["sc"])
async def sc_command(message: types.Message) -> None:
    """Отправляет расписание на сегодня/завтра."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)

    if message.reply_to_message and message.reply_to_message.from_user.id != bot.id:
        content = message.reply_to_message.text
    else:
        content = message.get_args()

    if content:
        text = process_request(sp, content)
        await message.answer(text=text)

    elif sp.user["class_let"]:
        flt = construct_filters(sp.sc)
        await message.answer(text=sp.send_today_lessons(flt),
                             reply_markup=markup_generator(sp, week_markup))
    else:
        text = "⚠️ Для быстрого получения расписания вам нужно указать класс."
        await message.answer(text=text)

@dp.message_handler(commands=["notify"])
async def notify_command(message: types.Message) -> None:
    """Отправляет расписание на сегодня/завтра."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)

    enabled = sp.user["notifications"]
    hours = sp.user["hours"]

    text = send_notification_message(sp, enabled, hours)
    markup = get_notifications_markup(sp, enabled, hours)
    await message.answer(text=text, reply_markup=markup)


# Главный обработчик сообщений
# ============================

@dp.message_handler()
async def main_handler(message: types.Message) -> None:
    uid = str(message.chat.id)
    sp = SPMessages(uid)
    text = message.text.strip().lower()
    logger.info("{} {}", uid, text)

    if sp.user["set_class"]:
        text = process_request(sp, text)
        await message.answer(text=text)

    elif text in sp.sc.lessons:
        logger.info("Set class {}", text)
        sp.set_class(text)
        markup = get_home_markup(sp)
        await message.answer(text=send_home_message(sp), reply_markup=markup)


# Обработчик inline-кнопок
# ========================

@dp.callback_query_handler()
async def callback_handler(callback: types.CallbackQuery) -> None:
    header, *args = callback.data.split()
    uid = str(callback.message.chat.id)
    sp = SPMessages(uid)

    if header == "home":
        text = send_home_message(sp)
        markup = get_home_markup(sp)

    # Вызоы меню инстрментов
    elif header == "other":
        text = sp.send_status() + INFO_MESSAGE
        markup = markup_generator(sp, other_markup)

    # Счётчик уроков/кабинетов
    elif header == "count":
        logger.info("{}: count {}", uid, args)

        if args[0] == args[1]:
            args[1] = None

        if args[0] == "cl" and args[1] == "lessons" and not sp.user["class_let"]:
            args[1] = None

        text = get_counter_message(sp.sc, args[0], args[1])
        markup = gen_counters_markup(sp, args[0], args[1])

    # Расписание на сегодня
    elif header == "sc":
        logger.info("{}: Sc", uid)
        text = sp.send_today_lessons(construct_filters(sp.sc, cl=[args[0]]))
        markup = markup_generator(sp, week_markup, cl=args[0])

    # Расписание на неделю
    elif header == "week":
        logger.info("{}: sc: week", uid, args)
        flt = construct_filters(sp.sc, days=[0, 1, 2, 3, 4, 5], cl=args[0])
        text = sp.send_lessons(flt)
        markup = markup_generator(sp, sc_markup, cl=args[0])

    # Клавиатура для выбора дня
    elif header == "select_day":
        text = f"📅 на ...\n🔶 Для {args[0]}:"
        markup = select_day_markup(args[0])

    # Расписани на определённый день
    elif header == "sc_day":
        logger.info("{}: sc: {}", uid, args)
        day = int(args[1])

        if day == 7:
            day = [0, 1, 2, 3, 4, 5]

        flt = construct_filters(sp.sc, days=day, cl=args[0])

        if day == 6:
            text = sp.send_today_lessons(flt)
            markup = markup_generator(sp, week_markup, cl=args[0])
        else:
            text = sp.send_lessons(flt)
            markup = markup_generator(sp, sc_markup, cl=args[0])

    # Отправка списка изменений
    elif header == "updates":
        logger.info("{}: updates: {}", uid, args)
        text = "🔔 Изменения "

        # Смена режима просмотра: только для класса/всего расписния
        if args[0] == "switch":
            cl = sp.user["class_let"] if args[2] == "None" else None
        else:
            cl = None if args[2] == "None" else args[2]

        # Доплняем шапку сообщения
        if cl is not None and sp.user["set_class"]:
            text += f"для {cl}:\n"
            flt = construct_filters(sp.sc, cl=args[2])
        else:
            text += "в расписании:\n"
            flt = construct_filters(sp.sc)

        updates = sp.sc.get_updates(flt)
        i = max(min(int(args[1]), len(updates)-1), 0)

        if len(updates):
            if args[0] in ["last", "switch"]:
                i = len(updates)-1

            elif args[0] == "next":
                i = (i+1) % len(updates)

            elif args[0] == "back":
                i = (i-1) % len(updates)

            text += send_update(updates[i])
        else:
            text += "Нет новых обновлений."

        markup = gen_updates_markup(i, updates, cl)

    # Смена класса пользователя
    elif header == "set_class":
        logger.info("{}: Reset user", uid)
        sp.reset_user()
        text = SET_CLASS_MESSAGE
        markup = to_home_markup

    elif header == "notify":
        command, *arg_hours = args
        logger.info("{}: notify {} {}", uid, command, arg_hours)

        if command == "on":
            sp.user["notifications"] = True
            sp.save_user()
        elif command == "off":
            sp.user["notifications"] = False
            sp.save_user()
        elif command == "add":
            for x in arg_hours:
                if x not in sp.user["hours"]:
                    sp.user["hours"].append(x)

            sp.save_user()

        elif command == "reset":
            sp.user["hours"] = []
            sp.save_user()

        enabled = sp.user["notifications"]
        hours = sp.user["hours"]

        text = send_notification_message(sp, enabled, hours)
        markup = get_notifications_markup(sp, enabled, hours)

    else:
        text = "👀 Упс, эта клавиатура устарела."
        markup = to_home_markup
        logger.warning("Unknown header - {}", header)

    with suppress(MessageNotModified):
        await callback.message.edit_text(text=text, reply_markup=markup)

    await callback.answer()


@dp.errors_handler()
async def errors_handler(update: types.Update, exception: Exception):
    logger.exception("Cause exception {} in u:{}", exception, update)
    if gotify is not None:
        await gotify.create_message(
            str(exception), title="Oops!", priority=5
        )
    return True


# Запуск бота
# ===========

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
