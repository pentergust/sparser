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

from aiogram import Bot, Dispatcher
from loguru import logger
from tortoise import Tortoise

from sp.view.messages import MessagesView
from tg import middleware
from tg.config import BotConfig
from tg.handlers import routers


async def main() -> None:
    """Главная функция запуска бота.

    Подключает роутеры из других файлов к диспетчеру.
    Запускает обработку событий.
    """
    config = BotConfig()  # pyright: ignore[reportCallIssue]
    dp = Dispatcher(view=MessagesView())

    bot = Bot(config.bot_token)
    logger.info("Init DB connection:")
    await Tortoise().init(db_url=config.db_url, modules={"models": ["tg.db"]})
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
