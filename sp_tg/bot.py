"""Telegram-бот для доступа к SPMessages.

Полностью реализует доступ ко всем методам SPMessages.
Не считая некоторых ограничений в настройке "намерений" (Intents).

Главный файл с основными методами обработчиками доба.
"""

import sqlite3
from datetime import datetime
from os import getenv
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ErrorEvent, Message, Update
from dotenv import load_dotenv
from loguru import logger

from sp.messages import SPMessages
from sp.users import FileUserStorage, User, UserData
from sp.utils import get_str_timedelta
from sp_tg.handlers import routers
from sp_tg.keyboards import (PASS_SET_CL_MARKUP, get_main_keyboard,
                             get_other_keyboard)
from sp_tg.messages import SET_CLASS_MESSAGE, get_home_message
from sp_tg.utils.days import get_relative_day
from sp_tg.utils.intents import UserIntents

# Настройкки и константы
# ======================

load_dotenv()
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN", "")
dp = Dispatcher()
_TIMETAG_PATH = Path("sp_data/last_update")
DB_CONN = sqlite3.connect("sp_data/tg.db")
USER_STORAGE = FileUserStorage("sp_data/users/tg.json")

# Некоторые константные настройки бота
_BOT_VERSION = "v2.4.2"
_ALERT_AUTOUPDATE_AFTER_SECONDS = 3600


# Добавление Middleware
# =====================

@dp.message.middleware()
@dp.callback_query.middleware()
@dp.error.middleware()
async def user_middleware(
    handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
    event: Union[Update, CallbackQuery, ErrorEvent],
    data: Dict[str, Any],
) -> Any:
    """Добавляет экземпляр SPMessages и намерения пользователя."""
    if isinstance(event, ErrorEvent):
        if event.update.callback_query is not None:
            uid = event.update.callback_query.message.chat.id
        else:
            uid = event.update.message.chat.id
    elif isinstance(event, CallbackQuery):
        uid = event.message.chat.id
    else:
        uid = event.chat.id

    user = User(USER_STORAGE, str(uid))
    data["intents"] = UserIntents(DB_CONN, uid)
    data["user"] = user
    data["sp"] = SPMessages(user)
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
    """Отслеживает полученные ботом сообщения и callback query."""
    if isinstance(event, CallbackQuery):
        logger.info("[c] {}: {}", event.message.chat.id, event.data)
    else:
        logger.info("[m] {}: {}", event.chat.id, event.text)

    return await handler(event, data)


def get_update_timetag(path: Path) -> int:
    """Получает время последней удачной проверки обнолвений.

    Вспомогательная функция.
    Время успешой проверки используется для контроля скрипта обновлений.
    Если время последней проверки будет дольше одного часа,
    то это повод задуматься о правильноти работы скрипта.

    :param path: Путь к файлу временной метки обновлений.
    :type path: Path
    :return: UNIXtime последней удачной проверки обновлений.
    :rtype: int
    """
    try:
        with open(path) as f:
            return int(f.read())
    except (ValueError, FileNotFoundError):
        return 0

def get_status_message(sp: SPMessages, timetag_path: Path) -> str:
    """Отправляет информационно сособщение о работа бота и парсера.

    Инфомарционно сообщения содержит некоторую вспомогательную
    информацию относительно статуса и работаспособности бота.
    К примеру версия бота, время последнего обновления,
    классов и прочее.
    Также осдержит метку последнего автоматического обновления.
    Если давно не было автообновлений - выводит предупреждение.

    :param sp: Экземпляр генератора сообщений.
    :type sp: SPMessages
    :param timetag_path: Путь к файлу временной метки обновления.
    :type timetag_path: Path
    :return: Информацинное сообщение.
    :rtype: str
    """
    message = sp.send_status()
    message += f"\n⚙️ Версия бота: {_BOT_VERSION}\n🛠️ Тестер @sp6510"

    timetag = get_update_timetag(timetag_path)
    timedelta = int(datetime.now().timestamp()) - timetag
    message += f"\n📀 Проверка была {get_str_timedelta(timedelta)} назад"

    if timedelta > _ALERT_AUTOUPDATE_AFTER_SECONDS:
        message += ("\n⚠️ Автоматическая проверка была более часа назад."
            "\nПожалуйста свяжитесь с администратором бота."
        )

    return message


# Обработчики команд
# ==================

@dp.message(Command("info"))
async def info_handler(
    message: Message,
    sp: SPMessages,
    user: User
) -> None:
    """Сообщение о статусе рабты бота и парсера."""
    await message.answer(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(user.data.cl),
    )

@dp.message(Command("help", "start"))
async def start_handler(
    message: Message,
    sp: SPMessages,
    user: User
) -> None:
    """Отправляет сообщение справки и главную клавиатуру.

    Если класс не указан, отпраляет сообщение смены класса.
    """
    await message.delete()
    if user.data.set_class:
        today = datetime.today().weekday()
        tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today))
        relative_day = get_relative_day(today, tomorrow)
        await message.answer(
            text=get_home_message(user.data.cl),
            reply_markup=get_main_keyboard(user.data.cl, relative_day),
        )
    else:
        await message.answer(SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP)


# Обработчик Callback запросов
# ============================

@dp.callback_query(F.data == "delete_msg")
async def delete_msg_callback(
    query: CallbackQuery,
    sp: SPMessages,
    user: User
) -> None:
    """Удаляет сообщение.

    Если не удалось удалить, отправляет гланый раздел.
    """
    try:
        await query.message.delete()
    except TelegramBadRequest:
        today = datetime.today().weekday()
        tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today))
        relative_day = get_relative_day(today, tomorrow)
        await query.message.edit_text(
            text=get_home_message(user.data.cl),
            reply_markup=get_main_keyboard(user.data.cl, relative_day)
    )

@dp.callback_query(F.data == "home")
async def home_callback(
    query: CallbackQuery,
    sp: SPMessages,
    user: User
) -> None:
    """Возаращает в главный раздел."""
    today = datetime.today().weekday()
    tomorrow = sp.get_current_day(sp.sc.construct_intent(days=today))
    relative_day = get_relative_day(today, tomorrow)

    await query.message.edit_text(
        text=get_home_message(user.data.cl),
        reply_markup=get_main_keyboard(user.data.cl, relative_day)
    )

@dp.callback_query(F.data == "other")
async def other_callback(
    query: CallbackQuery,
    sp: SPMessages,
    user: User
) -> None:
    """Возвращает сообщение статуса и доплнительную клавиатуру."""
    await query.message.edit_text(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(user.data.cl),
    )


# Обработка исключений
# ====================

def send_error_messsage(exception: ErrorEvent, user: User) -> str:
    """Отпрвляет отладочное сообщние об ошибке пользователю.

    Data:
        user_name => Кто вызвал ошибку.
        user_id => Какой пользователь вызвал ошибку.
        class_let => К какому класс относился пользователь.
        chat_id => Где была вызвана ошибка.
        exception => Описание текста ошибки.
        action => Callback data или текст сообщение, вызвавший ошибку.

    Args:
        exception (ErrorEvent): Событие ошибки aiogram.
        sp (SPMessage): Экземпляр генератора сообщений пользователя.

    Returns:
        str: Отладочное сообщение с данными об ошибке в боте.
    
    """
    if exception.update.callback_query is not None:
        action = f"-- Данные: {exception.update.callback_query.data}"
        message = exception.update.callback_query.message
    else:
        action = f"-- Текст: {exception.update.message.text}"
        message = exception.update.message

    user_name = message.from_user.first_name
    chat_id = message.chat.id

    return ("⚠️ Произошла ошибка в работе бота."
        f"\n-- Версия: {_BOT_VERSION}"
        "\n\n👤 Пользователь"
        f"\n-- Имя: {user_name}"
        f"\n-- Класс: {user.data.cl}"
        f"\n-- ID: {chat_id}"
        "\n\n🚫 Описание ошибки:"
        f"\n-- {exception.exception}"
        "\n\n🔍 Доплнительная информаиция"
        f"\n{action}"
        "\n\nПожалуйста, свяжитесь с @milinuri для решения проблемы."
    )

@dp.errors()
async def error_handler(exception: ErrorEvent, user: User) -> None:
    """Ловит и обрабатывает все исключения.

    Отправляет сообщение об ошибке пользователям.
    """
    logger.exception(exception.exception)
    if exception.update.callback_query is not None:
        await exception.update.callback_query.message.answer(
            send_error_messsage(exception, user)
        )
    else:
        await exception.update.message.answer(
            send_error_messsage(exception, user)
        )


# Запуск бота
# ===========

async def main() -> None:
    """Главная функция запуска бота."""
    bot = Bot(TELEGRAM_TOKEN)

    # Загружаем обработчики.
    for r in routers:
        logger.info("Include router: {} ...", r.name)
        dp.include_router(r)

    # Запускаем бота.
    logger.info("Start polling ...")
    await dp.start_polling(bot)
