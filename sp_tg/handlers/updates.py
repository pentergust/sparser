"""Клавиатура просмотра списка изменений.

Предоставляет раздел для просмотра списка изменений.
Постраничный просмотр списка изменений.
Просмотр списка изменений для всего расписания и для отдельного класса.
Использованеи системы намерений для уточнения списка изменений.
"""

from typing import Optional, Union

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from sp.intents import Intent
from sp.messages import SPMessages, send_update
from sp.users.storage import User
from sp_tg.messages import get_intent_status
from sp_tg.utils.intents import UserIntents

router = Router(name=__name__)

# Максимальный размер сообщения с изменениями в расписании
_MAX_UPDATE_MESSAGE_LENGTHT = 4000


class UpdatesCallback(CallbackData, prefix="updates"):
    """Используется при просмотре списка изменений.

    action (str): back, mext, last, switch.

    - back: Переместитсья на одну страницу назад.
    - next: Переместиться на одну страницу вперёд.
    - last: Переместиться на последную страницу расписания.
    - swith: Переключить режим просмотра с общего на для класса.

    page (int): Текущаю страница списка изменений.
    cl (str): Для какого класса отображать список изменений.
    intent (str): Имя намерения пользователя.
    """

    action: str
    page: int
    cl: str
    intent: str


# Вспомогательные функции
# =======================

def get_updates_keyboard(
    page: int,
    updates: list[dict],
    cl: Optional[str],
    intents: UserIntents,
    intent_name: str = ""
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для просмотра списка изменений.

    Используется для перемещения по списку изменений в расписании.
    Также может переключать режим просмотре с общего на для класса.
    Использует клавиатуру выбора намерений, для уточнения результатов.

    Buttons:

    - home => Возврат к главному меня бота.
    - updates:back:{page}:{cl} => Перещается на одну страницу назад.
    - updates:switch:0:{cl} => Переключает режим просмотра расписания.
    - updates:next:{page}:{cl} => Перемещается на страницу вперёд.
    - updates:last:0:{cl} => Перерключиться на последную страницу.

    :param page: Текущая страница списка изменений.
    :type page: int
    :param update: Список всех страниц списка изменений.
    :type update: list[dict]
    :param cl: Какой класс подставлять в клавиатуру.
    :type cl: str
    :param intents: Экземпляр хранилища намерений пользователя.
    :type intents: UserIntents
    :param intent_name: Имя текущего выбранного намерения.
    :type intent_name: Optional[intent]
    :return: Клавиатура просмотра списка изменений в расписании.
    :rtype: InlineKeyboardMarkup
    """
    # базовая клавиатура
    inline_keyboard = [
        [
            InlineKeyboardButton(text="🏠", callback_data="home"),
            InlineKeyboardButton(
                text="◁",
                callback_data=f"updates:back:{page}:{cl}:{intent_name}"
            ),
            InlineKeyboardButton(
                text=f"{page+1}/{len(updates)}",
                callback_data=f"updates:switch:0:{cl}:{intent_name}",
            ),
            InlineKeyboardButton(
                text="▷",
                callback_data=f"updates:next:{page}:{cl}:{intent_name}"
            ),
        ]
    ]

    # Доплнительная клавиатура выбора намерения
    for i, x in enumerate(intents.get()):
        if i % 3 == 0:
            inline_keyboard.append([])

        if x.name == intent_name:
            inline_keyboard[-1].append(InlineKeyboardButton(
                text=f"✅ {x.name}", callback_data=f"updates:last:0:{cl}:")
            )
        else:
            inline_keyboard[-1].append(InlineKeyboardButton(
                text=f"⚙️ {x.name}",
                callback_data=f"updates:last:0:{cl}:{x.name}"
                )
            )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_updates_message(
    update: Optional[dict[str, Union[int, list[dict]]]]=None,
    cl: Optional[str]=None,
    intent: Optional[Intent]=None
) -> str:
    """Собирает сообщение со страницей списка изменений расписания.

    Использует функцию send_update из генератора сообщений.
    Проверяет длинну сообщения, чтобы не вызывать исключений.
    Добавляет в итоговое сообщение шапку с описанием выбранного
    намерения.

    :param update: Странциа списка измененйи в расписании.
    :type update: Optional[dict[str, Union[int, list[dict]]]]
    :param cl: Для какого класса предоставляется список изменений.
    :type cl: Optional[str]
    :param intent: Экземпляр выбранного намерения в расписании.
    :type intent: Optional[Intent]
    :return: Сообщение страницы списка изменений в расписании.
    :rtype: str
    """
    message = "🔔 Изменения "
    message += " в расписании:\n" if cl is None else f" для {cl}:\n"
    if intent is not None:
        message += f"⚙️ {get_intent_status(intent)}\n"

    if update is not None:
        update_text = send_update(update, cl=cl)

        if len(update_text) > _MAX_UPDATE_MESSAGE_LENGTHT:
            message += "\n📚 Слишком много изменений."
        else:
            message += update_text
    else:
        message += "✨ Нет новых обновлений."

    return message


# Описание команд
# ===============

@router.message(Command("updates"))
async def updates_handler(message: Message, sp: SPMessages,
    intents: UserIntents
) -> None:
    """Отправляет последную страницу списка изменений в расписании.

    А также возвращет клавиатуру для управления просмотром
    списка изменений.
    """
    updates = sp.sc.updates
    await message.answer(
        text=get_updates_message(updates[-1] if len(updates) else None),
        reply_markup=get_updates_keyboard(max(len(updates) - 1, 0),
            updates, None, intents
        )
    )


# Callback обработчики
# ====================

@router.callback_query(UpdatesCallback.filter())
async def updates_callback(
    query: CallbackQuery, sp: SPMessages, callback_data: UpdatesCallback,
    intents: UserIntents, user: User
) -> None:
    """Обрабатывает нажатия на клавиатуру просмтра списка изменений.

    - Переключение просмотар с общего на для класса.
    - Пеермещает в конец списка изменений.
    - Позволяет перемешаться по страницам изменений вперёд и назад.
    """
    # Смена режима просмотра: только для класса/всего расписния
    if callback_data.action == "switch":
        cl = user.data.cl if callback_data.cl == "None" else None
    else:
        cl = None if callback_data.cl == "None" else callback_data.cl

    # Загружаем намерение из базы данных
    intent = intents.get_intent(callback_data.intent)

    # Если указан класс и выбран класс по умолчанию
    # Заменяем намерения на просмотр для класса по умолчанию
    if cl is not None and user.data.cl:
        if intent is not None:
            intent = intent.reconstruct(sp.sc, cl=cl)
        else:
            intent = sp.sc.construct_intent(cl=cl)

    # Если намерение не указано. получаем полный список изменений
    if intent is None:
        updates = sp.sc.updates
    # Если намерение указанр, фильтруем результаты поиска
    else:
        updates = sp.sc.get_updates(intent)
    i = max(min(int(callback_data.page), len(updates) - 1), 0)

    # Если в рузельтате есть записи об изменениях
    if len(updates):
        # Переключаемся на последную запись
        if callback_data.action in ("last", "switch"):
            i = len(updates) - 1

        # Перемещаемся на следующая запись
        elif callback_data.action == "next":
            i = (i + 1) % len(updates)

        # Перемещаемся на предыдушую запись
        elif callback_data.action == "back":
            i = (i - 1) % len(updates)

        update = updates[i]
    else:
        update = None

    # Отправляем результат пользователю
    await query.message.edit_text(
        text=get_updates_message(update, cl, intent),
        reply_markup=get_updates_keyboard(
            i, updates, cl, intents, callback_data.intent
        )
    )
