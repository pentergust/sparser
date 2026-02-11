"""Обработчик ошибок бота."""

from datetime import UTC, datetime

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.types import ErrorEvent, Message
from loguru import logger

from tg.config import BotConfig
from tg.db import User
from tg.filters import NotAdminError

router = Router(name=__name__)


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
        f"\n-- Время: {now}"
        "\n\n👤 Пользователь"
        f"\n-- Имя: {user_name}"
        f"\n-- Класс: {user.cl} (установлен: {set_class_flag})"
        f"\n-- ID: {chat_id}"
        f"\n{action}"
        f"\n\n🚫 Возникло исключение  {exception.exception.__class__.__name__}:"
        f"\n-- {exception.exception}"
    )


@router.errors
async def error_handler(
    exception: ErrorEvent, user: User, config: BotConfig, bot: Bot
) -> None:
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

    if isinstance(exception.exception, NotAdminError):
        await message.answer(
            "Только администратор может использовать данную команду."
        )
        return None

    await message.answer(
        "⚠️ Произошла ошибочка.\n"
        "Попробуйте воспользоваться командой чуть позже.\n\n"
        "Если проблема не решилась, свяжитесь с администратором."
    )
    if not config.debug:
        if isinstance(message, Message):
            await message.copy_to(config.bot_admin)
        await bot.send_message(
            config.bot_admin, send_error_message(exception, user)
        )

    return None
