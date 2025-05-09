"""Главный файл Telegram бота для работы с SPlatform.

Полностью реализует доступ ко всем методам MessagesView.
Не считая некоторых ограничений в настройке "намерений" (Intents).
Также это касается ограничения текстовых сообщений.

Получает обновления в первую очередь.
Является основной платформой для работы расписания.

Это главный файл с самыми необходимыми обработчиками.
С функцией для загрузки всех дополнительных роутеров и последующего
запуска бота.

Предоставляет:

- /start /help (home): Главное сообщение бота.
- /info: Статус работы платформы и бота.
- delete_msg: Удалить сообщение или отправить главный раздел.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from os import getenv
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ErrorEvent, Message, Update
from dotenv import load_dotenv
from loguru import logger
from tortoise import Tortoise

from sp.db import User
from sp.utils import get_str_timedelta
from sp.version import VersionInfo
from sp.view.messages import MessagesView
from sp_tg.handlers import routers
from sp_tg.keyboards import (
    PASS_SET_CL_MARKUP,
    get_main_keyboard,
    get_other_keyboard,
)
from sp_tg.messages import SET_CLASS_MESSAGE, get_home_message

# Настройки и константы
# =====================

load_dotenv()
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN", "")
_TIMETAG_PATH = Path("sp_data/last_update")
# Используются для отладки сообщений об исключениях
_DEBUG_MODE = getenv("DEBUG_MODE")
_ADMIN_ID = getenv("ADMIN_ID")
_DB_URL = getenv("DB_URL")

# Некоторые константные настройки бота
_BOT_VERSION = VersionInfo("v2.7", 0, 7)
_ALERT_AUTO_UPDATE_AFTER_SECONDS = 3600


# Настраиваем диспетчер бота
# ==========================

dp = Dispatcher(view=MessagesView())


# Добавление Middleware
# =====================


@dp.message.middleware()
@dp.callback_query.middleware()
@dp.error.middleware()
async def user_middleware(
    handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: dict[str, Any],
) -> Awaitable[Any]:
    """Добавляет экземпляр пользователя и хранилище намерений."""
    # Это выглядит как костыль, работает примерно так же
    if isinstance(event, ErrorEvent):
        if event.update.callback_query is not None:
            uid = event.update.callback_query.message.chat.id
        else:
            uid = event.update.message.chat.id
    elif isinstance(event, CallbackQuery):
        uid = event.message.chat.id
    elif isinstance(event, Message):
        uid = event.chat.id
    else:
        raise ValueError("Unknown event type")

    user, _ = await User.get_or_create(id=uid)
    data["user"] = user
    return await handler(event, data)


# Если вы хотите отключить ведение журнала в боте
# Закомментируйте необходимые вам декораторы
@dp.message.middleware()
@dp.callback_query.middleware()
async def log_middleware(
    handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: dict[str, Any],
) -> Awaitable[Any]:
    """Отслеживает полученные ботом сообщения и callback query."""
    if isinstance(event, CallbackQuery):
        logger.info("[c] {}: {}", event.message.chat.id, event.data)
    elif isinstance(event, Message):
        logger.info("[m] {}: {}", event.chat.id, event.text)

    return await handler(event, data)


# Сообщение статуса
# =================


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


# Обработчики команд
# ==================


@dp.message(Command("info"))
async def info_handler(
    message: Message, view: MessagesView, user: User
) -> None:
    """Статус работы бота и платформы."""
    await message.answer(
        text=await get_status_message(view, _TIMETAG_PATH, user),
        reply_markup=get_other_keyboard(user.cl),
    )


@dp.message(Command("help", "start"))
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


# Обработчик Callback запросов
# ============================


@dp.callback_query(F.data == "delete_msg")
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


@dp.callback_query(F.data == "home")
async def home_callback(
    query: CallbackQuery, user: User, view: MessagesView
) -> None:
    """Возвращает в главный раздел."""
    await query.message.edit_text(
        text=get_home_message(user.cl),
        reply_markup=get_main_keyboard(user.cl, view.relative_day(user)),
    )


@dp.callback_query(F.data == "other")
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


# Обработка исключений
# ====================


def send_error_message(exception: ErrorEvent, user: User) -> str:
    """Отправляет отладочное сообщение об ошибке пользователю.

    Предоставляемые данные:

    - new => Когда вызвано исключение.
    - user_name => Кто вызвал исключение.
    - user_id => Какой пользователь вызвал исключение.
    - class_let => К какому класс относился пользователь.
    - set_class => Установлен ли класс.
    - chat_id => Где была вызвана ошибка.
    - exception => Описание исключения.
    - action => Callback data или текст сообщение, вызвавший ошибку.
    """
    if exception.update.callback_query is not None:
        action = f"-- Данные: {exception.update.callback_query.data}"
        message = exception.update.callback_query.message
    else:
        action = f"-- Текст: {exception.update.message.text}"
        message = exception.update.message

    if message is None:
        raise ValueError("Message is None")

    user_name = message.from_user.first_name
    chat_id = message.chat.id
    now = datetime.now(UTC).strftime(
        "%Y-%m-%d %H:%M:%S"
    )  # 2024-08-23 21:12:40.383
    set_class_flag = "да" if user.set_class else "нет"

    return (
        "⚠️ Произошла ошибка в работе бота."
        f"\n-- Версия: {_BOT_VERSION}"
        f"\n-- Время: {now}"
        "\n\n👤 Пользователь"
        f"\n-- Имя: {user_name}"
        f"\n-- Класс: {user.cl} (установлен: {set_class_flag})"
        f"\n-- ID: {chat_id}"
        f"\n{action}"
        f"\n\n🚫 Возникло исключение  {exception.exception.__class__.__name__}:"
        f"\n-- {exception.exception}"
        "\n\nПожалуйста, отправьте @milinuri данное сообщение."
        "\nЭто очень поможет сделать бота стабильнее."
    )


@dp.errors()
async def error_handler(exception: ErrorEvent, user: User) -> None:
    """Ловит и обрабатывает все исключения.

    Отправляет сообщение об ошибке пользователям.
    Некоторое исключения будут подавляться, поскольку не предоставляют
    ничего интересного.
    """
    if isinstance(
        exception.exception, TelegramBadRequest | TelegramNetworkError
    ):
        return logger.error(exception)

    logger.exception(exception.exception)
    if exception.update.callback_query is not None:
        message = exception.update.callback_query.message
    else:
        message = exception.update.message

    # Не исключено что сообщение может быть пустым
    if message is None:
        return None

    await message.answer(send_error_message(exception, user))
    if not _DEBUG_MODE and _ADMIN_ID is not None:
        await message.bot.send_message(
            chat_id=_ADMIN_ID, text=send_error_message(exception, user)
        )


# Запуск бота
# ===========


async def main() -> None:
    """Главная функция запуска бота.

    Подключает роутеры из других файлов к диспетчеру.
    Запускает обработку событий.
    """
    bot = Bot(TELEGRAM_TOKEN)
    logger.info("Init DB connection:")
    await Tortoise().init(db_url=_DB_URL, modules={"models": ["sp.db"]})
    await Tortoise.generate_schemas()

    # Загружаем обработчики.
    for r in routers:
        logger.info("Include router: {} ...", r.name)
        dp.include_router(r)

    # Запускаем бота.
    logger.info("Start polling ...")
    await dp.start_polling(bot)
