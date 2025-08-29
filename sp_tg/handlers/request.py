"""Составление запросов к расписанию.

Предоставляет обработчики для составления текстовых запросов.
Это один из основных способов получения данных из бота.
Текстовые запросы представляют собой намерения в чистом виде.
Они позволяет как получать расписание, так и производить поиск
в расписании.
"""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger

from sp.db import User
from sp.view.messages import MessagesView
from sp_tg.keyboards import get_main_keyboard, get_week_keyboard
from sp_tg.messages import get_home_message

router = Router(name=__name__)


async def process_request(
    user: User, view: MessagesView, request_text: str
) -> str | None:
    """Обрабатывает текстовый запрос к расписанию.

    Преобразует входящий текст в набор намерений или запрос.
    Производит поиск по урокам/кабинетам
    или получает расписание, в зависимости от намерений.
    """
    intent = view.sc.parse_intent(request_text.split())

    # Чтобы не превращать бота в машину для спама
    # Будет использоваться последний урок/кабинет из фильтра
    if len(intent.cabinets):
        text = view.search(list(intent.cabinets)[-1], intent, True)

    elif len(intent.lessons):
        text = view.search(list(intent.lessons)[-1], intent, False)

    elif intent.cl or intent.days:
        if intent.days:
            text = view.lessons(await user.intent_or(intent))
        else:
            text = view.today_lessons(await user.intent_or(intent))
    else:
        text = None

    return text


# Обработка команд
# ================


@router.message(Command("sc"))
async def sc_handler(
    message: Message, command: CommandObject, user: User, view: MessagesView
) -> None:
    """Отправляет расписание уроков пользователю.

    Позволяет напрямую писать запросы, после ``/sc [запрос]``.
    Отправляет предупреждение, если у пользователя не указан класс.
    """
    if command.args is not None:
        answer = await process_request(user, view, command.args)
        if answer is not None:
            await message.answer(text=answer)
        else:
            await message.answer(text="👀 Кажется это пустой запрос...")

    elif user.cl != "":
        await message.answer(
            text=view.today_lessons(await user.main_intent()),
            reply_markup=get_week_keyboard(user.cl),
        )
    else:
        await message.answer(
            text="⚠️ Для быстрого получения расписания вам нужно указать класс."
        )


@router.message()
async def main_handler(
    message: Message, user: User, view: MessagesView
) -> None:
    """Главный обработчик сообщений бота.

    Перенаправляет входящий текст в запросы к расписанию.
    Устанавливает класс, если он не установлен.
    В личных подсказках отправляет подсказку о доступных классах.
    """
    if message.text is None:
        return

    text = message.text.strip().lower()

    # Если у пользователя установлен класс -> создаём запрос
    if user.set_class:
        answer = await process_request(user, view, text)

        if answer is not None:
            await message.answer(text=answer)
        elif message.chat.type == "private":
            await message.answer(text="👀 Кажется это пустой запрос...")

    # Устанавливаем класс пользователя, если он ввёл класс
    elif text in view.sc.lessons:
        logger.info("Set class {}", text)
        await user.set_cl(text, view.sc)
        relative_day = view.relative_day(user)
        await message.answer(
            text=get_home_message(user.cl),
            reply_markup=get_main_keyboard(user.cl, relative_day),
        )

    # Отправляем список классов, в личные сообщения.
    elif message.chat.type == "private":
        text = "👀 Такого класса не существует."
        text += f"\n💡 Доступные классы: {', '.join(view.sc.lessons)}"
        await message.answer(text=text)
