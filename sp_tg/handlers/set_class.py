"""Предоставляет возможного изменять класс пользователя.

Предоставляет команды и обработчики для смены пользовательского
класса по умолчанию.

Класс по умолчанию повсеместно используется для боеле удобного
использованияб бота.
"""

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from sp.messages import SPMessages
from sp.users.storage import User
from sp_tg.keyboards import PASS_SET_CL_MARKUP, get_main_keyboard
from sp_tg.messages import SET_CLASS_MESSAGE, get_home_message
from sp_tg.utils.days import get_relative_day

router = Router(name=__name__)

# Статические клавиатуры при выборе класса
# pass => Пропустить смену класс и установить None
# cl_features => Список преимуществ если указать класс
BACK_SET_CL_MARKUP = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="◁", callback_data="set_class"),
            InlineKeyboardButton(text="Без класса", callback_data="pass"),
        ]
    ]
)


# Какие преимущества получает указавшие класс пользователь
# Это сообщение должно побуждать пользователей укащываит свой класс
# по умолчанию чтобы получать преимущества
CL_FEATURES_MESSAGE = ("🌟 Если вы укажете класс, то сможете:"
    "\n\n-- Быстро получать расписание для класса, кнопкой в главном меню."
    "\n-- Не укзаывать ваш класс в текстовых запросах (прим. \"пн\")."
    "\n-- Получать уведомления и рассылку расписания для класса."
    "\n-- Просматривать список изменений для вашего класса."
    "\n-- Использовать счётчик cl/lessons."
    "\n\n💎 Список возможностей может пополняться."
)


# Описание команд
# ===============

@router.message(Command("cl_features"))
async def restrictions_handler(message: Message):
    """Отправляет список примуществ при указанном классе."""
    await message.answer(text=CL_FEATURES_MESSAGE)

@router.message(Command("set_class"))
async def set_class_command(message: Message, sp: SPMessages, user: User,
    command: CommandObject
):
    """Изменяет класс или удаляет данные о пользователе.

    - Если такого класса не существует, показывает список доступных
      классов.
    - Указывать класс можно передавая его как аргумент.
    - Если не укзаать класс, сбрасывает данные пользователя и
      пепеводит его в состояние выбора класса.
    """
    # Если указали класс в команде
    if command.args is not None:
        if user.set_class(command.args, sp.sc):
            today = datetime.today().weekday()
            tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today))
            relative_day = get_relative_day(today, tomorrow)
            await message.answer(
                text=get_home_message(command.args),
                reply_markup=get_main_keyboard(command.args, relative_day)
            )
        # Если такого класса не существует
        else:
            text = "👀 Такого класса не существует."
            text += f"\n💡 Доступныe классы: {', '.join(sp.sc.lessons)}"
            await message.answer(text=text)

    # Сбрасываем пользвоателя и переводим в состояние выбора класса
    else:
        user.unset_class()
        await message.answer(
            text=SET_CLASS_MESSAGE,
            reply_markup=PASS_SET_CL_MARKUP
        )

@router.message(Command("pass"))
async def pass_handler(message: Message, sp: SPMessages, user: User):
    """Отвязаывает пользователя от класса по умолчанию.

    Если более конкретно, то устанавливает калсс пользователя в
    None и отправляет главное сообщение и клавиатуру.
    """
    today = datetime.today().weekday()
    tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today))
    relative_day = get_relative_day(today, tomorrow)
    user.set_class(None, sp.sc)
    await message.answer(
        text=get_home_message(user.data.cl),
        reply_markup=get_main_keyboard(user.data.cl, relative_day),
    )


# Обработчики Callback клавиатуры
# ===============================

@router.callback_query(F.data == "cl_features")
async def cl_features_callback(query: CallbackData, sp: SPMessages):
    """Отправляет сообщения с преимуществами указанного класса."""
    await query.message.edit_text(
        text=CL_FEATURES_MESSAGE,
        reply_markup=BACK_SET_CL_MARKUP
    )

@router.callback_query(F.data == "set_class")
async def set_class_callback(query: CallbackQuery, user: User):
    """Сбрасывает класс пользователя.

    Сбрасывает данные пользователя и переводит в состояние выбора
    класса по умолчанию.
    """
    user.unset_class()
    await query.message.edit_text(
        text=SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP
    )

@router.callback_query(F.data == "pass")
async def pass_class_callback(query: CallbackData, sp: SPMessages, user: User):
    """Отвязывает пользователя от класса.

    Как и в случае с командой /pass.
    Просто устанавливает класс пользвотеля в None и отправляет
    главное сообщение с основной клавиатурой бота.
    """
    today = datetime.today().weekday()
    tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today))
    relative_day = get_relative_day(today, tomorrow)
    user.set_class(None, sp.sc)
    await query.message.edit_text(
        text=get_home_message(user.data.cl),
        reply_markup=get_main_keyboard(user.data.cl, relative_day)
    )
