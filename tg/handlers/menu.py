"""Главное меню бота."""

from datetime import UTC, datetime
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from sp.view.messages import MessagesView, get_str_timedelta
from tg.db import User
from tg.keyboards import (
    PASS_SET_CL_MARKUP,
    get_main_keyboard,
    get_other_keyboard,
)
from tg.messages import SET_CLASS_MESSAGE, get_home_message

router = Router(name=__name__)


def get_update_timetag(path: Path) -> int:
    """Получает время последней удачной проверки обновлений.

    Вспомогательная функция.
    Время успешной проверки используется для контроля скрипта обновлений.
    Если время последней проверки будет дольше одного часа,
    то это повод задуматься о правильности работы скрипта.
    """
    try:
        with open(path) as f:
            return int(f.read())
    except (ValueError, FileNotFoundError):
        return 0


async def get_status_message(
    view: MessagesView, timetag_path: Path, user: User
) -> str:
    """Отправляет информационно сообщение о работа бота и парсера.

    Информационное сообщения содержит некоторую вспомогательную
    информацию относительно статуса и работы бота.
    К примеру версия бота, время последнего обновления,
    классов и прочее.
    Также содержит метку последнего автоматического обновления.
    Если давно не было авто обновлений - выводит предупреждение.
    """
    message = await view.get_status(user, _BOT_VERSION)
    message += f"\n⚙️ Версия бота: {_BOT_VERSION}\n🛠️ Тестер @micronuri"

    timetag = get_update_timetag(timetag_path)
    timedelta = int(datetime.now(UTC).timestamp()) - timetag
    message += f"\n📀 Проверка была {get_str_timedelta(timedelta)} назад"

    if timedelta > _ALERT_AUTO_UPDATE_AFTER_SECONDS:
        message += "\n ┗ Может что-то сломалось?.."

    return message


@router.message(Command("info"))
async def info_handler(
    message: Message, view: MessagesView, user: User
) -> None:
    """Статус работы бота и платформы."""
    await message.answer(
        text=await get_status_message(view, _TIMETAG_PATH, user),
        reply_markup=get_other_keyboard(user.cl),
    )


@router.message(Command("help", "start"))
async def start_handler(
    message: Message, user: User, view: MessagesView
) -> None:
    """Отправляет домашнее сообщение и главную клавиатуру.

    Если класс не указан - отправляет сообщение смены класса.
    """
    if not user.set_class:
        await message.answer(SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP)
        return

    await message.delete()
    await message.answer(
        text=get_home_message(user.cl),
        reply_markup=get_main_keyboard(user.cl, view.relative_day(user)),
    )


@router.callback_query(F.data == "delete_msg")
async def delete_msg_callback(
    query: CallbackQuery, user: User, view: MessagesView
) -> None:
    """Удаляет сообщение пользователя.

    Если не удалось удалить, отправляет главное сообщение.
    """
    try:
        await query.message.delete()
    except TelegramBadRequest:
        await query.message.edit_text(
            text=get_home_message(user.cl),
            reply_markup=get_main_keyboard(user.cl, view.relative_day(user)),
        )


@router.callback_query(F.data == "home")
async def home_callback(
    query: CallbackQuery, user: User, view: MessagesView
) -> None:
    """Возвращает в главный раздел."""
    await query.message.edit_text(
        text=get_home_message(user.cl),
        reply_markup=get_main_keyboard(user.cl, view.relative_day(user)),
    )


@router.callback_query(F.data == "other")
async def other_callback(
    query: CallbackQuery, view: MessagesView, user: User
) -> None:
    """Сообщение о статусе бота и платформы.

    Также предоставляет клавиатуру с менее используемыми разделами.
    """
    await query.message.edit_text(
        text=await get_status_message(view, _TIMETAG_PATH, user),
        reply_markup=get_other_keyboard(user.cl),
    )
