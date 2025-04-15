"""Обработчики получения расписания на определённые дни.

Предоставляет обработчики для получения расписания в определённые
дни недели или на всю неделю.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message

from sp.db import User
from sp.platform import Platform
from sp_tg.keyboards import (
    get_sc_keyboard,
    get_select_day_keyboard,
    get_week_keyboard,
)

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
    """Используется для выбора дня недели при получении расписания."""

    cl: str


# Описание команд
# ===============


@router.message(Command("week"))
async def week_sc_command(
    message: Message, user: User, platform: Platform
) -> None:
    """Расписание уроков на неделю."""
    relative_day = platform.relative_day(user)
    await message.answer(
        text=platform.lessons(
            user,
            platform.view.sc.construct_intent(
                days=[0, 1, 2, 3, 4, 5], cl=user.cl
            ),
        ),
        reply_markup=get_sc_keyboard(user.cl, relative_day),
    )


# Описания Callback обработчиков
# ==============================


@router.callback_query(ScCallback.filter())
async def sc_callback(
    query: CallbackQuery,
    callback_data: ScCallback,
    user: User,
    platform: Platform,
) -> None:
    """Отправляет расписание уроков для класса в указанный день."""
    # Расписание на неделю
    if callback_data.day == "week":
        text = platform.lessons(
            user,
            platform.view.sc.construct_intent(
                days=[0, 1, 2, 3, 4, 5], cl=user.cl
            ),
        )
        relative_day = platform.relative_day(user)
        reply_markup = get_sc_keyboard(callback_data.cl, relative_day)

    # Расписание на сегодня/завтра
    elif callback_data.day == "today":
        text = platform.today_lessons(
            user, platform.view.sc.construct_intent(cl=callback_data.cl)
        )
        reply_markup = get_week_keyboard(callback_data.cl)

    # Расписание на другой день недели
    else:
        text = platform.lessons(
            user,
            platform.view.sc.construct_intent(
                cl=callback_data.cl, days=int(callback_data.day)
            ),
        )
        reply_markup = get_week_keyboard(callback_data.cl)

    await query.message.edit_text(text=text, reply_markup=reply_markup)


@router.callback_query(SelectDayCallback.filter())
async def select_day_callback(
    query: CallbackQuery,
    callback_data: ScCallback,
    user: User,
    platform: Platform,
) -> None:
    """Отображает клавиатуру для выбора дня расписания уроков."""
    relative_day = platform.relative_day(user)
    await query.message.edit_text(
        text=f"📅 на ...\n🔶 Для {callback_data.cl}:",
        reply_markup=get_select_day_keyboard(callback_data.cl, relative_day),
    )
