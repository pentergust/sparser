"""
Telegram обёртка над SParser.

Author: Milinuri Nirvalen
Ver: 1.4.1 (sp v4.4)

Команды бота для BotFather:
sc - Уроки на сегодня
updates - Изменения в расписании
counter - Счётчик уроков/кабинетов
set_class - Изменить класс
help - Главное меню
info - ⚙Информация о боте
"""

from sp import SPMessages
from sp import Schedule
from sp import load_file

import re

from datetime import datetime
from pathlib import Path
from typing import Optional

from aiogram import types
from aiogram import Bot
from aiogram import Dispatcher
from aiogram import executor
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardRemove
from loguru import logger


API_TOKEN = load_file(Path("sp_data/token.json"),
                      {"token": "YOUR TG API TOKEN"})["token"]
bot = Bot(API_TOKEN)
dp = Dispatcher(bot)
logger.add("sp_data/telegram.log")
days_str = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]
days_names = ["понедельник", "вторник", "среда",
              "четверг", "пятница", "суббота", "сегодня", "неделя"]


# Определение клавиатур бота
# ==========================

to_home_markup = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text="🏠Домой", callback_data="home"))

week_markup = [{"home": "🏠", "week {cl}": "На неделю", "select_day {cl}":"▷"}]
sc_markup = [{"home": "🏠", "sc {cl}": "На сегодня", "select_day {cl}": "▷"}]
counter_markup = [{"home": "◁", "count": "Уроки", "count cl": "Уроки {cl}",
                   "count abinets": "Классы",
                   "count cabinets cl": "Классы {cl}"}]
home_murkup = [{"other": "🔧", "updates last 0 {cl}": "🔔", "sc {cl}": "📚"}]
other_markup = [{"home": "◁", "set_class": "Сменить класс"},
                {"count": "Счётчик",}]


def markup_generator(sp: SPMessages, pattern: dict, cl: Optional[str] = None,
                     exclude: Optional[str] = None,
                     row_width: Optional[int] = 3) -> InlineKeyboardMarkup:
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

            callback_data = callback_data.replace("{cl}", cl)
            text = text.replace("{cl}", cl)

            row.append(InlineKeyboardButton(text= text, callback_data= callback_data))
        markup.row(*row)

    return markup

def gen_updates_markup(update_index: int, updates: list) -> InlineKeyboardMarkup:
    """Собирает inline-клввиатуру для постраничного просмотра списка
    изменений расписания.

    Args:
        update_index (int): Номер текущей страницы обновлений
        updates (list): Список всех страниц

    Returns:
        InlineKeyboardMarkup: Готовая inline-клавиатура
    """
    markup = InlineKeyboardMarkup(row_width= 4)
    markup_pattern = {
            "home": "🏠",
            "updates back": "◁",
            "updates switch": f"{update_index+1}/{len(updates)}",
            "updates next": "▷",
        }

    for k, v in markup_pattern.items():
        k += f" {update_index}"
        markup.insert(InlineKeyboardButton(text= v, callback_data= k))

    return markup

def gen_select_day_markup(cl: str) -> InlineKeyboardMarkup:
    """Собирает inline-клавиатуру для выбора дня недели.

    Args:
        cl (str): Уточнение для какого класса выбиратеся день недели

    Returns:
        InlineKeyboardMarkup: inline-клавиатура для выбора для недели
    """
    markup = InlineKeyboardMarkup()

    for i, x in enumerate(days_names):
        markup.insert(InlineKeyboardButton(text= x,
                                           callback_data= f"sc_day {cl} {i}"))
    return markup


# Тексты сообщений
# ================

HOME_MESSAGE = """💡 Некоторые примеры:
-- 7в
-- уроки 6а на вторник среду
-- расписание на завтра для 8б
-- 312 на вторник
-- химия 228

🏫 Вы можете использовать:
-- Класс: для которого нужно расписание.
-- Дни: понедельник-суббота, сегодня, завтра, неделя.
-- Урок: Все его упоминания.
-- Кабинет: Расписание от его лица
🌟 Порадок и форма не имеют значения!"""

INFO_MESSAGE = """
О боте:
:: Автор: @milinuri
:: Версия: 1.4.1 (🔶Testing)

👀 По всем вопросам к @milinuri"""

SET_CLASS_MESSAGE = """
⚠️ Для полноценной работы бота ему нужно знать ваш класс.
💡 Вы всегда сможете изменить класс командой /set_class

Пожалуйста, следуюшим сообщением введите класс..."""


# Опеределение команд бота
# ========================

@dp.message_handler(commands= ["start"])
async def start_command(message: types.Message):
    sp = SPMessages(str(message.chat.id), Schedule())
    logger.info(message.chat.id)
    await message.delete()

    if sp.user["set_class"]:
        markup = markup_generator(sp, home_murkup)
        await message.answer(text= HOME_MESSAGE, reply_markup= markup)
    else:
        await message.answer(text= SET_CLASS_MESSAGE)


@dp.message_handler(commands= ["help"])
async def help_command(message: types.Message):
    sp = SPMessages(str(message.chat.id), Schedule())
    logger.info(message.chat.id)
    markup = markup_generator(sp, home_murkup)
    await message.answer(text= HOME_MESSAGE, reply_markup= markup)


@dp.message_handler(commands= ["info"])
async def info_command(message: types.Message):
    logger.info(message.chat.id)
    sp = SPMessages(str(message.chat.id), Schedule())
    await message.answer(text= sp.send_status()+INFO_MESSAGE,
                         reply_markup= to_home_markup)


@dp.message_handler(commands= ["updates"])
async def updates_command(message: types.Message):
    sp = SPMessages(str(message.chat.id), Schedule())
    logger.info(message.chat.id)
    updates = sp.sc.get_updates()
    markup = gen_updates_markup(len(updates)-1, updates)
    await message.answer(text= sp.send_updates(updates[-1]), 
                        reply_markup= markup)


@dp.message_handler(commands= ["counter"])
async def lessons_command(message: types.Message):
    sp = SPMessages(str(message.chat.id), Schedule())
    logger.info(message.chat.id)
    markup = markup_generator(sp, counter_markup,
                              exclude= "count", row_width= 4)
    await message.answer(text= sp.count_lessons(),
                         reply_markup= markup)


@dp.message_handler(commands= ["set_class"])
async def set_class_command(message: types.Message):
    sp = SPMessages(str(message.chat.id), Schedule())
    logger.info(message.chat.id)
    sp.user["set_class"] = False
    sp.save_user()
    await message.answer(text= SET_CLASS_MESSAGE)


@dp.message_handler(commands= ["sc"])
async def sc_command(message: types.Message):
    sp = SPMessages(str(message.chat.id), Schedule())
    logger.info(message.chat.id)

    if sp.user["set_class"]:
        await message.answer(text= sp.send_today_lessons(),
                             reply_markup= markup_generator(sp, week_markup))
    else:
        await message.answer(text= SET_CLASS_MESSAGE)


# Главный обработчик сообщений
# ============================

@dp.message_handler()
async def main_handler(message: types.Message):
    uid = str(message.chat.id)
    sc = Schedule()
    sp = SPMessages(uid, sc)
    logger.info("{} {}", uid, message.text)

    if sp.user["set_class"]:
        args = message.text.lower().strip().split()
        weekday = datetime.today().weekday()
        days = []
        cl = None
        lesson = None
        cabinet = None

        # Обработка входящего сообщения
        # -----------------------------

        for arg in args:
            if arg == "сегодня":
                days.append(weekday)

            elif arg == "завтра":
                days.append(datetime.today().weekday()+1)

            elif arg.startswith("недел"):
                days = [0, 1, 2, 3, 4, 5]

            elif arg in sc.lessons:
                cl = arg

            elif arg in sc.l_index:
                lesson = arg

            elif arg in sc.c_index:
                cabinet = arg

            else:
                # Если начало слова совпадает: пятниц... -а, -у, -ы...
                days += [i for i, k in enumerate(days_str) if arg.startswith(k)]

        # Отправка сообщения
        # ------------------

        logger.info(f"answer С:{cabinet} L:{lesson} D:{days} CL:{cl}")
        if cabinet:
            res = sp.search_cabinet(cabinet, lesson, days, cl)
            await message.answer(text= res, reply_markup= to_home_markup)

        elif lesson:
            res = sp.search_lesson(lesson, days, cl)
            await message.answer(text= res, reply_markup= to_home_markup)

        elif cl or days:
            markup = markup_generator(sp, week_markup, cl= cl)
            if days:
                await message.answer(text= sp.send_lessons(days= days, cl= cl),
                                     reply_markup= markup)
            else:
                await message.answer(text= sp.send_today_lessons(cl= cl),
                                     reply_markup= markup)
        else:
            await message.answer(text= "👀 Кажется, это пустой запрос...?")


    # Устаеновка класса по умолчанию
    # ==============================

    else:
        text = message.text.lower()
        await message.answer(text= sp.set_class(text))

        if text in sc.lessons:
            logger.info(f"Set class {text} ")
            markup = markup_generator(sp, home_murkup)
            await message.answer(text= HOME_MESSAGE, reply_markup= markup)


# Обработчик inline-кнопок
# ========================

@dp.callback_query_handler()
async def callback_handler(callback: types.CallbackQuery):
    header, *args = callback.data.split()
    uid = str(callback.message.chat.id)
    sp = SPMessages(uid, Schedule())
    logger.info("{}: {} {}", uid, header, args)

    # Вызов справки
    if header == "home":
        markup = markup_generator(sp, home_murkup)
        await callback.message.edit_text(text=HOME_MESSAGE, reply_markup= markup)

    # Вызов счётчика
    if header == "count":
        cabinets = True if "cabinets" in args else False
        cl = sp.user["class_let"] if "cl" in args else None
        text = sp.count_lessons(cabinets= cabinets, cl= cl)
        markup = markup_generator(sp, counter_markup, exclude= callback.data,
                                  row_width= 4)
        await callback.message.edit_text(text= text, reply_markup=markup)

    # Расписание на сегодня
    if header == "sc":
        text = sp.send_today_lessons(cl= args[0])
        markup = markup_generator(sp, week_markup, cl= args[0])
        await callback.message.edit_text(text= text, reply_markup= markup)

    # Расписание на неделю
    if header == "week":
        text = sp.send_lessons(days= [0, 1, 2, 3, 4, 5], cl= args[0])
        markup = markup_generator(sp, sc_markup, cl= args[0])
        await callback.message.edit_text(text= text, reply_markup= markup)

    # Клавиатура для выбора дня
    if header == "select_day":
        markup = gen_select_day_markup(args[0])
        await callback.message.edit_text(text= f"🏫 Для {args[0]}: ...",
                                         reply_markup= markup)

    # Расписани на определённый день
    if header == "sc_day":
        cl = args[0]
        day = int(args[1])

        if day == 6:
            text = sp.send_today_lessons(cl= cl)
        elif day == 7:
            text = sp.send_lessons(days=[0, 1, 2, 3, 4, 5], cl= cl)
        else:
            text = sp.send_lessons(days= [day], cl=cl)

        markup = markup_generator(sp, sc_markup, cl= cl)
        await callback.message.edit_text(text= text, reply_markup= markup)

    # Вызов меню обновлений
    if header == "updates":
        i = int(args[1])
        text = "🔔 Изменения в расписании:\n"
        updates = sp.sc.updates

        if args[0] == "next":
            i = (i+1) % len(updates)

        elif args[0] == "back":
            i = (i-1) % len(updates)

        elif args[0] == "last":
            i = len(updates)-1

        text += sp.send_update(updates[i])
        markup = gen_updates_markup(i, updates)
        await callback.message.edit_text(text= text, reply_markup= markup)

    # Вызоы меню инстрментов
    if header == "other":
        text = sp.send_status() + INFO_MESSAGE
        markup = markup_generator(sp, other_markup)
        await callback.message.edit_text(text= text, reply_markup= markup)

    # Смена класса пользователя
    if header == "set_class":
        sp.user["set_class"] = False
        sp.save_user()
        await callback.message.edit_text(text= SET_CLASS_MESSAGE)

    await callback.answer()


# Запуск бота
# ===========

if __name__ == "__main__":
    executor.start_polling(dp)
