"""Составление запросов к расписнаию.

Предоставялет обработчики для составления текстовых запросов.
Это один из основных способов получения данных из бота.
Текстоыве запросы представляют собой намерения в чистом виде.
Они позволяет как получать расписнаие, так и производить поиск
в расписании.
"""

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger

from sp.platform import Platform
from sp.users.storage import User
from sp_tg.keyboards import get_main_keyboard, get_week_keyboard
from sp_tg.messages import get_home_message

router = Router(name=__name__)


def process_request(
    user: User, platform: Platform, request_text: str
) -> str | None:
    """Обрабатывает текстовый запрос к расписанию.

    Преобразует входящий текст в набор намерений или запрос.
    Производит поиск по урокам/кабинетам
    или получает расписание, в зависимости от намерений.

    :param user: Кто захотел получить расписание.
    :type user: User
    :param platform: Экземпляр платформы расписания.
    :type platform: Platform
    :param request_text: Текст запроса к расписнаию.
    :type requets_text: str
    :return: Ответ от генератора сообщений.
    :rtype: str | None
    """
    intent = platform.view.sc.parse_intent(request_text.split())

    # Чтобы не превращать бота в машину для спама
    # Будет использоваться последний урок/кабинет из фильтра
    if len(intent.cabinets):
        text = platform.search(list(intent.cabinets)[-1], intent, True)

    elif len(intent.lessons):
        text = platform.search(list(intent.lessons)[-1], intent, False)

    elif intent.cl or intent.days:
        if intent.days:
            text = platform.lessons(user, intent)
        else:
            text = platform.today_lessons(user, intent)
    else:
        text = None

    return text


# Обработка команд
# ================


@router.message(Command("sc"))
async def sc_handler(
    message: Message, command: CommandObject, user: User, platform: Platform
) -> None:
    """Отправляет расписание уроков пользовтелю.

    Позвоялет напрямую писать запросы, после ``/sc [запрос]``.
    Отправляет предупреждение, если у пользователя не укзаан класс.
    """
    if command.args is not None:
        answer = process_request(user, platform, command.args)
        if answer is not None:
            await message.answer(text=answer)
        else:
            await message.answer(text="👀 Кажется это пустой запрос...")

    elif user.data.cl is not None:
        await message.answer(
            text=platform.today_lessons(user),
            reply_markup=get_week_keyboard(user.data.cl),
        )
    else:
        await message.answer(
            text="⚠️ Для быстрого получения расписания вам нужно указать класс."
        )


@router.message()
async def main_handler(
    message: Message, user: User, platform: Platform
) -> None:
    """Главный обработчик сообщений бота.

    Перенаправляет входящий текст в запросы к расписанию.
    Устанавливает класс, если он не установлен.
    В личных подсказках отправляет подсказку о доступных классах.
    """
    if message.text is None:
        return

    text = message.text.strip().lower()

    # Если у пользователя установлек класс -> создаём запрос
    if user.data.set_class:
        answer = process_request(user, platform, text)

        if answer is not None:
            await message.answer(text=answer)
        elif message.chat.type == "private":
            await message.answer(text="👀 Кажется это пустой запрос...")

    # Устанавливаем класс пользователя, если он ввёл класс
    elif text in platform.view.sc.lessons:
        logger.info("Set class {}", text)
        user.set_class(text, platform.view.sc)
        relative_day = platform.relative_day(user)
        await message.answer(
            text=get_home_message(user.data.cl),
            reply_markup=get_main_keyboard(user.data.cl, relative_day),
        )

    # Отправляем список классов, в личные сообщения.
    elif message.chat.type == "private":
        text = "👀 Такого класса не существует."
        text += f"\n💡 Доступныe классы: {', '.join(platform.view.sc.lessons)}"
        await message.answer(text=text)
