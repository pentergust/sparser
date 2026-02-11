"""Обработчики получения расписания на определённые дни.

Предоставляет обработчики для получения расписания в определённые
дни недели или на всю неделю.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from sp.enums import SHORT_DAY_NAMES
from sp.view.messages import MessagesView
from tg.db import User
from tg.keyboards import (
    week_markup,
)

router = Router(name=__name__)


def sc_markup(cl: str, relative_day: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для получения расписания на сегодня.

    Используется в сообщениях с расписанием уроков.
    Когда режим просмотра выставлен "на неделю".
    Также содержит кнопки для возврата домой и выбора дня недели.

    Buttons:

    - home => Возврат в домашний раздел.
    - sc:{cl}:today => Получить расписание на сегодня для класса.
    - select_day:{cl} => Выбрать день недели для расписания.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠Домой", callback_data="home"),
                InlineKeyboardButton(
                    text=relative_day, callback_data=f"sc:{cl}:today"
                ),
                InlineKeyboardButton(
                    text="▷", callback_data=f"select_day:{cl}"
                ),
            ]
        ]
    )


def select_day_markup(cl: str, relative_day: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора дня недели в расписании.

    Используется в сообщения с расписанием.
    Позволяет выбрать один из дней недели.
    Автоматически подставляя указанный класс в запрос.

    Buttons:

    - sc:{cl}:{0..6} => Получить расписания для указанного дня.
    - sc:{cl}:today => Получить расписание на сегодня.
    - sc:{cl}:week => получить расписание на неделю.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=x, callback_data=f"sc:{cl}:{i}")
                for i, x in enumerate(SHORT_DAY_NAMES)
            ],
            [
                InlineKeyboardButton(text="◁", callback_data="home"),
                InlineKeyboardButton(
                    text=relative_day, callback_data=f"sc:{cl}:today"
                ),
                InlineKeyboardButton(
                    text="Неделя", callback_data=f"sc:{cl}:week"
                ),
            ],
        ]
    )


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
    message: Message, user: User, view: MessagesView
) -> None:
    """Расписание уроков на неделю."""
    await message.answer(
        text=view.lessons(
            await user.intent_or(
                view.sc.construct_intent(days=[0, 1, 2, 3, 4, 5], cl=user.cl)
            ),
        ),
        reply_markup=sc_markup(user.cl, view.relative_day(user)),
    )


# Описания Callback обработчиков
# ==============================


@router.callback_query(ScCallback.filter())
async def sc_callback(
    query: CallbackQuery,
    callback_data: ScCallback,
    user: User,
    view: MessagesView,
) -> None:
    """Отправляет расписание уроков для класса в указанный день."""
    # Расписание на неделю
    if callback_data.day == "week":
        text = view.lessons(
            await user.intent_or(
                view.sc.construct_intent(days=[0, 1, 2, 3, 4, 5], cl=user.cl)
            ),
        )
        relative_day = view.relative_day(user)
        reply_markup = sc_markup(callback_data.cl, relative_day)

    # Расписание на сегодня/завтра
    elif callback_data.day == "today":
        text = view.today_lessons(
            await user.intent_or(view.sc.construct_intent(cl=callback_data.cl))
        )
        reply_markup = week_markup(callback_data.cl)

    # Расписание на другой день недели
    else:
        text = view.lessons(
            await user.intent_or(
                view.sc.construct_intent(
                    cl=callback_data.cl, days=int(callback_data.day)
                )
            ),
        )
        reply_markup = week_markup(callback_data.cl)

    await query.message.edit_text(text=text, reply_markup=reply_markup)


@router.callback_query(SelectDayCallback.filter())
async def select_day_callback(
    query: CallbackQuery,
    callback_data: ScCallback,
    user: User,
    view: MessagesView,
) -> None:
    """Отображает клавиатуру для выбора дня расписания уроков."""
    await query.message.edit_text(
        text=f"📅 на ...\n🔶 Для {callback_data.cl}:",
        reply_markup=select_day_markup(
            callback_data.cl, view.relative_day(user)
        ),
    )
