"""Содержит набор собственных фильтров бота.

Фильтры используются для отсеивания нежелательных обработчиков.
Для проверки некоторых условий, перед тем как выполнить команду
или прочее действие.

В отличие от Middleware, фильтры срабатывают только не обработчики,
которые мы сами выберем.
"""

from aiogram.enums import ChatMemberStatus
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from loguru import logger


class IsAdmin(BaseFilter):
    """Проверяет что участник является администратором чата.

    Предполагать что все участники чата милые и пушистые глупо.
    Кто-нибудь забавы ради может взять и переназначить настройки бота.
    Например чтобы использовать его как спам-машину.
    Или внезапно для всех изменить класс по умолчанию.

    Данный фильтр позволяет ограничить число людей, которые могут
    изменять настройки бота до круга администраторов чата.
    По крайней мере мы надеемся что администраторы будут более
    ответственные, чем общая масса участников.
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        """Проверяет что пользователь администратор чата."""
        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery):
            chat = event.message.chat

        # Есть такая вероятность, что чата не будет, тогда это странно..
        if chat is None:
            logger.error("Chat is empty: {}", event)
            raise ValueError("Chat is empty")

        # В личной переписке администраторов нету
        if chat.type == "private":
            return True

        member = await chat.get_member(event.from_user.id)
        if member.status not in (
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
        ):
            await event.answer(
                "⚙️ Только администраторы чата могут изменять настройки бота."
            )
            return False
        return True
