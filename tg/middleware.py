"""Middleware для бота."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, ErrorEvent, Message, Update
from loguru import logger

from tg.db import User


async def set_user(
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
