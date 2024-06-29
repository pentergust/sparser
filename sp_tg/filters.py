"""Содерижт набор собственных фильтров бота.

Фильтры используются для отсеивания нежелательных обработчиков.
Для проверки некоторых условий, перед тем как выполнить команду
или прочее действие.
"""

from aiogram.enums import ChatMemberStatus
from aiogram.filters import BaseFilter
from aiogram.types import Message


class IsAdmin(BaseFilter):
    """Проверяет что участник является администратором чата.

    Предполагать что все участникик чата милые и пушистые глупо.
    Кто-нибудт забавы ради может взять и переназначить настройки бота.
    Например чтобы использовать его как спам-машину.
    Или внезапно для всех изменить класс по умолчанию.

    Данный фильтр позволяет ограничить число людей, коотрые могуг
    изменять настройки бота до круга администраторов.
    По крайней мере мы надеемся что администраторы будут более
    ответственными, чем общая масса участников.
    """

    async def __call__(self, message: Message) -> bool:
        """Проверяет что пользователь администратор чата."""
        if message.chat.type == "private":
            return True

        member = await message.chat.get_member(message.from_user.id)
        if member.status not in (
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
        ):
            await message.answer((
                "⚙️ Только администраторы чата могут изменять настройки бота.\n"
            ))
            return False
        return True
