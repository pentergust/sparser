"""Главный файл Telegram бота для работы с SPlatform.

Полностью реализует доступ ко всем методам MessagesView.
Не считая некоторых ограничений в настройке "намерений" (Intents).
Также это касается ограничения текстовых сообщений.

Получает обновления в первую очередь.
Является основной платформой для работы расписания.

Это главный файл с самыми необходимыми обработчиками.
С функцией для загрузки всех дополнительных роутеров и последующего
запуска бота.
"""

from collections.abc import Awaitable, Callable
from os import getenv
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery, ErrorEvent, Message, Update
from dotenv import load_dotenv
from loguru import logger
from tortoise import Tortoise

from sp.view.messages import MessagesView
from tg.db import User
from tg.handlers import routers

load_dotenv()
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN", "")
_TIMETAG_PATH = Path("sp_data/last_update")
# Используются для отладки сообщений об исключениях
_DEBUG_MODE = getenv("DEBUG_MODE")
_ADMIN_ID = getenv("ADMIN_ID")
_DB_URL = getenv("DB_URL")

# Некоторые константные настройки бота
_BOT_VERSION = "v2.7"
_ALERT_AUTO_UPDATE_AFTER_SECONDS = 3600


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
@dp.message.middleware
@dp.callback_query.middleware
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


# Запуск бота
# ===========


async def main() -> None:
    """Главная функция запуска бота.

    Подключает роутеры из других файлов к диспетчеру.
    Запускает обработку событий.
    """
    bot = Bot(TELEGRAM_TOKEN)
    logger.info("Init DB connection:")
    await Tortoise().init(db_url=_DB_URL, modules={"models": ["tg.db"]})
    await Tortoise.generate_schemas()

    for r in routers:
        logger.info("Include router: {}", r.name)
        dp.include_router(r)

    logger.info("Start polling ...")
    await dp.start_polling(bot)  # pyright: ignore[reportUnknownMemberType]
