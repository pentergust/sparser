"""Составление запросов к расписнаию.

Предоставялет обработчики для поставлени текстовых запросов.
Это один из основных способов получения данных из бота.
Текстоыве запросы представляют собой намерения в чистом виде.
Они позволяет как получать расписнаие, так и производить поиск
в расписании.
"""

from typing import Optional

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from loguru import logger

from sp.messages import SPMessages, send_search_res
from sp_tg.keyboards import get_main_keyboard, get_week_keyboard
from sp_tg.messages import get_home_message

router = Router(name=__name__)


def process_request(sp: SPMessages, request_text: str) -> Optional[str]:
    """Обрабатывает текстовый запрос к расписанию.

    Преобразует входящий текст в набор намерений или запрос.
    Производит поиск по урокам/кабинетам
    или получает расписание, в зависимости от намерений.

    :param sp: Экземпляр генератора сообщений.
    :type sp: SPMessages
    :param request_text: Текст запроса к расписнаию.
    :type requets_text: str
    :return: Ответ от генератора сообщений.
    :rtype: Optional[str]
    """
    intent = sp.sc.parse_intent(request_text.split())

    # Чтобы не превращать бота в машину для спама
    # Будет использоваться последний урок/кабинет из фильтра
    if len(intent.cabinets):
        res = sp.sc.search(list(intent.cabinets)[-1], intent, True)
        text = send_search_res(intent, res)

    elif len(intent.lessons):
        res = sp.sc.search(list(intent.lessons)[-1], intent, False)
        text = send_search_res(intent, res)

    elif intent.cl or intent.days:
        if intent.days:
            text = sp.send_lessons(intent)
        else:
            text =sp.send_today_lessons(intent)
    else:
        text = None

    return text


# Обработка команд
# ================

@router.message(Command("sc"))
async def sc_handler(
    message: Message, sp: SPMessages, command: CommandObject
):
    """Отправляет расписание уроков пользовтелю.

    Отправляет предупреждение, если у пользователя не укзаан класс.
    """
    if command.args is not None:
        answer = process_request(sp, command.args)
        if answer is not None:
            await message.answer(text=answer)
        else:
            await message.answer(text="👀 Кажется это пустой запрос...")

    elif sp.user["class_let"]:
        await message.answer(
            text=sp.send_today_lessons(sp.sc.construct_intent()),
            reply_markup=get_week_keyboard(sp.user["class_let"]),
        )
    else:
        await message.answer(
            text="⚠️ Для быстрого получения расписания вам нужно указать класс."
        )

@router.message()
async def main_handler(message: Message, sp: SPMessages) -> None:
    """Главный обработчик сообщений бота.

    Перенаправляет входящий текст в запросы к расписанию.
    Устанавливает класс, если он не установлен.
    В личных подсказках отправляет подсказку о доступных классах.
    """
    if message.text is None:
        return

    text = message.text.strip().lower()

    # Если у пользователя установлек класс -> создаём запрос
    if sp.user["set_class"]:
        answer = process_request(sp, text)

        if answer is not None:
            await message.answer(text=answer)
        elif message.chat.type == "private":
            await message.answer(text="👀 Кажется это пустой запрос...")

    # Устанавливаем класс пользователя, если он ввёл класс
    elif text in sp.sc.lessons:
        logger.info("Set class {}", text)
        sp.set_class(text)
        await message.answer(
            text=get_home_message(sp.user["class_let"]),
            reply_markup=get_main_keyboard(sp.user["class_let"])
        )

    # Отправляем список классов, в личные сообщения.
    elif message.chat.type == "private":
        text = "👀 Такого класса не существует."
        text += f"\n💡 Доступныe классы: {', '.join(sp.sc.lessons)}"
        await message.answer(text=text)
