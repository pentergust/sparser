"""
Telegram обёртка над SParser.

Author: Milinuri Nirvalen
Ver: 1.10 (sp v5.2)

Команды бота для BotFather:
sc - Уроки на сегодня
updates - Изменения в расписании
counter - Счётчики
set_class - Изменить класс
help - Главное меню
info - Информация о боте
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

from pathlib import Path
from typing import Optional

from aiogram import Bot
from aiogram import Dispatcher
from aiogram import executor
from aiogram import types
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from loguru import logger
from gotify import AsyncGotify


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
-- 7в 6а
-- уроки 6а на вторник ср
-- расписание на завтра для 8б
-- 312 на вторник пятницу
-- химия 228 6а вторник

🏫 В запросе вы можете использовать:
Класс: для которого нужно расписание.
-- "?": для подставновки вашего класса
:: Дни недели:
-- понедельник-суббота (пн-сб).
-- сегодня, завтра, неделя.
:: Урок/Кабинет: Получить все его упоминания.
🌟 Порядок и форма не важны, балуйтесь!"""

INFO_MESSAGE = """
:: Версия бота: 1.10

👀 По всем вопросам к @milinuri."""

SET_CLASS_MESSAGE = """
Для полноценной работы желательно указать ваш класс.
Для быстрого просмотра расписания и списка изменений.
Пожалуйста, следуюшим сообщением введите ваш класс ("1а").

🌟 Вы можете пропустить выбор класса командой /pass.
Но это накладывает некоторые ограничения.
Прочитать о них можно по команде /restrictions.

💡 Вы всега можете сменить класс в дальнейшем:
-- через команду /set_class.
-- Ещё -> сменить класс."""

RESTRICTIONS_MESSAGE = """Всё нижеперечисленное будет недоступно:

-- Кнопка получения расписания в справке.
-- Подстановка класса в запросах.
-- просмотр списка изменений для класса.
-- Счётчик "по классам/уроки".

🌟 На этом все отличия заканчиваются."""


# Определение клавиатур бота
# ==========================

to_home_markup = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text="🏠Домой", callback_data="home"))

week_markup = [{"home": "🏠", "week {cl}": "На неделю", "select_day {cl}":"▷"}]
sc_markup = [{"home": "🏠", "sc {cl}": "На сегодня", "select_day {cl}": "▷"}]
home_murkup = [{"other": "🔧Ещё",
                "updates last 0 None": "🔔Изменения",
                "sc {cl}": "📚Уроки {cl}"}]
other_markup = [{"home": "◁", "set_class": "Сменить класс"},
                {"count lessons main": "📊Счётчики",}]

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
    markup = InlineKeyboardMarkup(row_width=4)

    row = []
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


# Вспомогательные функции
# =======================

def get_counter_message(sc: Schedule, counter: str, target: str) -> str:
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
        message = "👀 Хитро, но так не работает, хе-хе."

    message += "\n\n"
    message += HOME_MESSAGE

    return message


# Опеределение команд бота
# ========================

@dp.message_handler(commands=["start", "help"])
async def start_command(message: types.Message) -> None:
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
    await message.delete()

    if sp.user["set_class"]:
        markup = markup_generator(sp, home_murkup)
        await message.answer(text=send_home_message(sp), reply_markup=markup)
    else:
        await message.answer(text=SET_CLASS_MESSAGE)

@dp.message_handler(commands=["set_class"])
async def set_class_command(message: types.Message) -> None:
    """Удаляет данные о пользователе."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
    sp.reset_user()
    await message.answer(text=SET_CLASS_MESSAGE)

@dp.message_handler(commands=["pass"])
async def pass_commend(message: types.Message) -> None:
    """Отвязывает пользователя от класса."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
    if not sp.user["set_class"]:
        sp.user["set_class"] = True
        sp.save_user()
        markup = markup_generator(sp, home_murkup)
        await message.answer(text=send_home_message(sp), reply_markup=markup)

@dp.message_handler(commands=["restrictions"])
async def restrictions_commend(message: types.Message) -> None:
    """Отвязывает пользователя от класса."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
    await message.answer(text=RESTRICTIONS_MESSAGE)

@dp.message_handler(commands=["info"])
async def info_command(message: types.Message) -> None:
    """Отправляет статус парсера и бота."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)
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
    message = get_counter_message(sp.sc, "lessons", "main")
    markup = gen_counters_markup(sp, "lessons", "main")
    await message.answer(text=message, reply_markup=markup)

@dp.message_handler(commands=["sc"])
async def sc_command(message: types.Message) -> None:
    """Отправляет расписание на сегодня/завтра."""
    sp = SPMessages(str(message.chat.id))
    logger.info(message.chat.id)

    if sp.user["class_let"]:
        flt = construct_filters(sp.sc)
        await message.answer(text=sp.send_today_lessons(flt),
                             reply_markup=markup_generator(sp, week_markup))
    else:
        text = "⚠️ Для быстрого получения расписания вам нужно указать класс."
        await message.answer(text=text)


# Главный обработчик сообщений
# ============================

@dp.message_handler()
async def main_handler(message: types.Message) -> None:
    uid = str(message.chat.id)
    sp = SPMessages(uid)
    text = message.text.strip().lower()
    logger.info("{} {}", uid, text)

    if sp.user["set_class"]:
        flt = parse_filters(sp.sc, text.split())

        # Чтобы не превращать бота в машину для спама
        # Будет использоваться последний урок/кабинет из фильтра
        if len(flt.cabinets):
            res = sp.search_cabinet(list(flt.cabinets)[-1], flt)
            await message.answer(text=res, reply_markup=to_home_markup)

        elif len(flt.lessons):
            res = sp.search_lesson(list(flt.lessons)[-1], flt)
            await message.answer(text=res, reply_markup=to_home_markup)

        elif flt.cl or flt.days:
            text = sp.send_lessons(flt) if flt.days else sp.send_today_lessons(flt)
            await message.answer(text=text)
        else:
            await message.answer(text="👀 Кажется это пустой запрос...")


    # Устаеновка класса по умолчанию
    # ==============================

    elif text in sp.sc.lessons:
        logger.info("Set class {}", text)
        sp.set_class(text)
        markup = markup_generator(sp, home_murkup)
        await message.answer(text=send_home_message(sp), reply_markup=markup)


# Обработчик inline-кнопок
# ========================

@dp.callback_query_handler()
async def callback_handler(callback: types.CallbackQuery) -> None:
    header, *args = callback.data.split()
    uid = str(callback.message.chat.id)
    sp = SPMessages(uid)
    logger.info("{}: {} {}", uid, header, args)

    if header == "home":
        markup = markup_generator(sp, home_murkup)
        await callback.message.edit_text(text=send_home_message(sp),
                                         reply_markup=markup)

    # Счётчик уроков/кабинетов
    elif header == "count":
        if args[0] == args[1]:
            args[1] = None

        if args[0] == "cl" and args[1] == "lessons" and not sp.user["class_let"]:
            args[1] = None

        text = get_counter_message(sp.sc, args[0], args[1])
        markup = gen_counters_markup(sp, args[0], args[1])
        await callback.message.edit_text(text=text, reply_markup=markup)

    # Расписание на сегодня
    elif header == "sc":
        text = sp.send_today_lessons(construct_filters(sp.sc, cl=[args[0]]))
        markup = markup_generator(sp, week_markup, cl=args[0])
        await callback.message.edit_text(text=text, reply_markup=markup)

    # Расписание на неделю
    elif header == "week":
        flt = construct_filters(sp.sc, days=[0, 1, 2, 3, 4, 5], cl=args[0])
        text = sp.send_lessons(flt)
        markup = markup_generator(sp, sc_markup, cl=args[0])
        await callback.message.edit_text(text=text, reply_markup=markup)

    # Клавиатура для выбора дня
    elif header == "select_day":
        markup = select_day_markup(args[0])
        await callback.message.edit_text(text=f"📅 на ...\n🔶 Для {args[0]}:",
                                         reply_markup=markup)

    # Расписани на определённый день
    elif header == "sc_day":
        day = int(args[1])
        flt = construct_filters(sp.sc, days=day, cl=args[0])

        if day == 6:
            text = sp.send_today_lessons(flt)
        elif day == 7:
            flt._days = [0, 1, 2, 3, 4, 5]
            text = sp.send_lessons(flt)
        else:
            text = sp.send_lessons(flt)

        markup = markup_generator(sp, sc_markup, cl=args[0])
        await callback.message.edit_text(text=text, reply_markup=markup)

    # Отправка списка изменений
    elif header == "updates":
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

        if text != callback.message.text:
            markup = gen_updates_markup(i, updates, cl)
            await callback.message.edit_text(text=text, reply_markup=markup)

    # Вызоы меню инстрментов
    elif header == "other":
        text = sp.send_status() + INFO_MESSAGE
        markup = markup_generator(sp, other_markup)
        await callback.message.edit_text(text=text, reply_markup=markup)

    # Смена класса пользователя
    elif header == "set_class":
        sp.user["set_class"] = False
        sp.save_user()
        await callback.message.edit_text(text=SET_CLASS_MESSAGE)

    else:
        logger.warning("Unknown header - {}", header)

    await callback.answer()


@dp.errors_handler()
async def errors_handler(update: types.Update, exception: Exception):
    try:
        raise exception
    except Exception as e:
        logger.exception("Cause exception {} in u:{}", e, update)
        if gotify is not None:
            await gotify.create_message(str(e),
                title="Oops!",
                priority=5)
    return True


# Запуск бота
# ===========

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
