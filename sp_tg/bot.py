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
from sp.utils import get_str_timedelta
from sp_tg.handlers import routers
from sp_tg.keyboards import (PASS_SET_CL_MARKUP, get_main_keyboard,
                             get_other_keyboard)
from sp_tg.messages import SET_CLASS_MESSAGE, get_home_message
from sp_tg.utils.intents import UserIntents

# Настройкки и константы
# ======================

load_dotenv()
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN", "")
dp = Dispatcher()
_TIMETAG_PATH = Path("sp_data/last_update")
DB_CONN = sqlite3.connect("sp_data/tg.db")

# Некоторые константные настройки бота
_BOT_VERSION = "v2.3.1"
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

    data["sp"] = SPMessages(str(uid))
    data["intents"] = UserIntents(DB_CONN, uid)
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

    Args:
        path (Path): Путь к файлу временной метки обновлений.

    Returns:
        int: UNIXtime последней удачной проверки обновлений.
    
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

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.
        timetag_path (Path): Путь к файлу временной метки обновления.

    Returns:
        str: Информацинное сообщение.
    
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
async def info_handler(message: Message, sp: SPMessages) -> None:
    """Сообщение о статусе рабты бота и парсера."""
    await message.answer(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(sp.user["class_let"]),
    )

@dp.message(Command("help", "start"))
async def start_handler(message: Message, sp: SPMessages) -> None:
    """Отправляет сообщение справки и главную клавиатуру.

    Если класс не указан, отпраляет сообщение указания класса.
    """
    await message.delete()
    if sp.user["set_class"]:
        await message.answer(
            text=get_home_message(sp.user["class_let"]),
            reply_markup=get_main_keyboard(sp.user["class_let"]),
        )
    else:
        await message.answer(SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP)


# Обработчик Callback запросов
# ============================

@dp.callback_query(F.data == "delete_msg")
async def delete_msg_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Удаляет сообщение.

    Если не удалось удалить, отправляет гланый раздел.
    """
    try:
        await query.message.delete()
    except TelegramBadRequest:
        await query.message.edit_text(
            text=get_home_message(sp.user["class_let"]),
            reply_markup=get_main_keyboard(sp.user["class_let"])
    )

@dp.callback_query(F.data == "home")
async def home_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Возаращает в главный раздел."""
    await query.message.edit_text(
        text=get_home_message(sp.user["class_let"]),
        reply_markup=get_main_keyboard(sp.user["class_let"])
    )

@dp.callback_query(F.data == "other")
async def other_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Возвращает сообщение статуса и доплнительную клавиатуру."""
    await query.message.edit_text(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(sp.user["class_let"]),
    )


# Обработка исключений
# ====================

def send_error_messsage(exception: ErrorEvent, sp: SPMessages) -> str:
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
        f"\n-- Класс: {sp.user['class_let']}"
        f"\n-- ID: {chat_id}"
        "\n\n🚫 Описание ошибки:"
        f"\n-- {exception.exception}"
        "\n\n🔍 Доплнительная информаиция"
        f"\n{action}"
        "\n\nПожалуйста, свяжитесь с @milinuri для решения проблемы."
    )

@dp.errors()
async def error_handler(exception: ErrorEvent, sp: SPMessages) -> None:
    """Ловит и обрабатывает все исключения.

    Отправляет сообщение об ошибке пользователям.
    """
    logger.exception(exception.exception)
    if exception.update.callback_query is not None:
        await exception.update.callback_query.message.answer(
            send_error_messsage(exception, sp)
        )
    else:
        await exception.update.message.answer(
            send_error_messsage(exception, sp)
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
