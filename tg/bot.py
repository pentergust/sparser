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
from tg import middleware
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

    dp.message.middleware.register(middleware.set_user)
    dp.callback_query.middleware.register(middleware.set_user)
    dp.errors.middleware.register(middleware.set_user)

    dp.message.middleware.register(middleware.log_middleware)
    dp.callback_query.middleware.register(middleware.log_middleware)

    for r in routers:
        logger.info("Include router: {}", r.name)
        dp.include_router(r)

    logger.info("Start polling ...")
    await dp.start_polling(bot)  # pyright: ignore[reportUnknownMemberType]
