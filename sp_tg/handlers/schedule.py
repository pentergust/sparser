"""Обработчики получения расписания на определённые дни.

Предоставляет обработчики для получения расписнаия в определённые
дни недели или на всю неделю.
"""

from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message

from sp.intents import Intent
from sp.messages import SPMessages
from sp.users.storage import User
from sp_tg.keyboards import (
    get_sc_keyboard,
    get_select_day_keyboard,
    get_week_keyboard,
)
from sp_tg.utils.days import get_relative_day

router = Router(name=__name__)


# Callback данные
# ===============

class ScCallback(CallbackData, prefix="sc"):
    """Используется при получении расписания.

    cl (str): Класс для которого получить расписание.
    day (str): Для какого дня получить расписание.

    - 0-5: понедельник - суббота.
    - today: Получить расписание на сегодня/завтра.
    - week: Получить расписание на всю неделю.
    """

    cl: str
    day: str

class SelectDayCallback(CallbackData, prefix="select_day"):
    """Используется для выбора дня недели при получении расписания.

    cl (str): Для какого класса получить расписание.
    """

    cl: str


# Описание команд
# ===============

@router.message(Command("week"))
async def week_sc_command(message: Message, sp: SPMessages, user: User):
    """Получате расписание уроков на неделю."""
    today = datetime.today().weekday()
    tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today). user)
    relative_day = get_relative_day(today, tomorrow)
    await message.answer(
        text=sp.send_lessons(
            Intent.construct(
                sp.sc, days=[0, 1, 2, 3, 4, 5], cl=user.data.cl
            ),
            user
        ),

        reply_markup=get_sc_keyboard(user.data.cl, relative_day)
    )


# Описания Callback обработчиков
# ==============================

@router.callback_query(ScCallback.filter())
async def sc_callback(
    query: CallbackQuery, callback_data: ScCallback, sp: SPMessages,
    user: User
):
    """Отправляет расписание уроков для класса в указанный день."""
    # Расписание на неделю
    if callback_data.day == "week":
        text = sp.send_lessons(
            Intent.construct(
                sp.sc, days=[0, 1, 2, 3, 4, 5], cl=callback_data.cl
            ),
            user
        )
        today = datetime.today().weekday()
        tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today), user)
        relative_day = get_relative_day(today, tomorrow)
        reply_markup = get_sc_keyboard(callback_data.cl, relative_day)

    # Расипсание на сегодня/завтра
    elif callback_data.day == "today":
        text = sp.send_today_lessons(
            Intent.construct(sp.sc,
                cl=callback_data.cl
            ),
            user
        )
        reply_markup = get_week_keyboard(callback_data.cl)

    # Расписание на другой день недели
    else:
        text = sp.send_lessons(
            Intent.construct(
                sp.sc, cl=callback_data.cl, days=int(callback_data.day)
            ),
            user
        )
        reply_markup = get_week_keyboard(callback_data.cl)

    await query.message.edit_text(text=text, reply_markup=reply_markup)

@router.callback_query(SelectDayCallback.filter())
async def select_day_callback(
    query: CallbackQuery, callback_data: ScCallback, sp: SPMessages,
    user: User
):
    """Отобржает клавиатуру для выбора дня расписания уроков."""
    today = datetime.today().weekday()
    tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today), user)
    relative_day = get_relative_day(today, tomorrow)
    await query.message.edit_text(
        text=f"📅 на ...\n🔶 Для {callback_data.cl}:",
        reply_markup=get_select_day_keyboard(callback_data.cl, relative_day),
    )
