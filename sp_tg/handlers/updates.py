"""Клавиатура просмотра списка изменений.

Предоставляет раздел для просмотра списка изменений.
Постраничный просмотр списка изменений.
Просмотр списка изменений для всего расписания и для отдельного класса.
Использование системы намерений для уточнения списка изменений.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from sp.db import User
from sp.intents import Intent
from sp.parser import UpdateData
from sp.platform import Platform
from sp_tg.messages import get_intent_status

router = Router(name=__name__)

# Максимальный размер сообщения с изменениями в расписании
_MAX_UPDATE_MESSAGE_LENGTH = 4000


class UpdatesCallback(CallbackData, prefix="updates"):
    """Используется при просмотре списка изменений.

    action (str): back, next, last, switch.

    - back: Переместиться на одну страницу назад.
    - next: Переместиться на одну страницу вперёд.
    - last: Переместиться на последнюю страницу расписания.
    - switch: Переключить режим просмотра с общего на для класса.

    page (int): Текущая страница списка изменений.
    cl (str): Для какого класса отображать список изменений.
    intent (str): Имя намерения пользователя.
    """

    action: str
    page: int
    cl: str
    intent: str


# Вспомогательные функции
# =======================


async def get_updates_keyboard(
    page: int,
    updates: list[UpdateData],
    user: User,
    active_intent: str | None = None,
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для просмотра списка изменений.

    Используется для перемещения по списку изменений в расписании.
    Также может переключать режим просмотре с общего на для класса.
    Использует клавиатуру выбора намерений, для уточнения результатов.

    Buttons:

    - home => Возврат к главному меня бота.
    - updates:back:{page}:{cl} => Перемещается на одну страницу назад.
    - updates:switch:0:{cl} => Переключает режим просмотра расписания.
    - updates:next:{page}:{cl} => Перемещается на страницу вперёд.
    - updates:last:0:{cl} => Переключается на последую страницу.
    """
    # базовая клавиатура
    inline_keyboard = [
        [
            InlineKeyboardButton(text="🏠", callback_data="home"),
            InlineKeyboardButton(
                text="◁",
                callback_data=f"updates:back:{page}:{user.cl}:{active_intent}",
            ),
            InlineKeyboardButton(
                text=f"{page + 1}/{len(updates)}",
                callback_data=f"updates:switch:0:{user.cl}:{active_intent}",
            ),
            InlineKeyboardButton(
                text="▷",
                callback_data=f"updates:next:{page}:{user.cl}:{active_intent}",
            ),
        ]
    ]

    # Дополнительная клавиатура выбора намерения
    for i, x in enumerate(await user.intents.all()):
        if i % 3 == 0:
            inline_keyboard.append([])

        if x.name == active_intent:
            inline_keyboard[-1].append(
                InlineKeyboardButton(
                    text=f"✅ {x.name}",
                    callback_data=f"updates:last:0:{user.cl}:",
                )
            )
        else:
            inline_keyboard[-1].append(
                InlineKeyboardButton(
                    text=f"⚙️ {x.name}",
                    callback_data=f"updates:last:0:{user.cl}:{x.name}",
                )
            )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_updates_message(
    platform: Platform,
    update: UpdateData | None = None,
    cl: str | None = None,
    intent: Intent | None = None,
) -> str:
    """Собирает сообщение со страницей списка изменений расписания.

    Использует функцию update из платформы.
    Проверяет длину сообщения, чтобы не вызывать исключений.
    Добавляет в итоговое сообщение шапку с описанием выбранного
    намерения.
    """
    message = "🔔 Изменения "
    message += " в расписании:\n" if cl is None else f" для {cl}:\n"
    if intent is not None:
        message += f"⚙️ {get_intent_status(intent)}\n"

    if update is not None:
        update_text = platform.updates(update, hide_cl=cl)

        if len(update_text) > _MAX_UPDATE_MESSAGE_LENGTH:
            message += "\n📚 Слишком много изменений."
        else:
            message += update_text
    else:
        message += "✨ Нет новых обновлений."

    return message


# Описание команд
# ===============


@router.message(Command("updates"))
async def updates_handler(
    message: Message, platform: Platform, user: User
) -> None:
    """Отправляет последнюю страницу списка изменений в расписании.

    А также вернёт клавиатуру для управления просмотром
    списка изменений.
    """
    updates = platform.view.sc.updates
    if updates is None:
        raise ValueError("Schedule updates is None")
    await message.answer(
        text=get_updates_message(
            platform, updates[-1] if len(updates) else None
        ),
        reply_markup=await get_updates_keyboard(
            max(len(updates) - 1, 0), updates, user
        ),
    )


# Callback обработчики
# ====================


@router.callback_query(UpdatesCallback.filter())
async def updates_call(
    query: CallbackQuery,
    platform: Platform,
    callback_data: UpdatesCallback,
    user: User,
) -> None:
    """Обрабатывает нажатия на клавиатуру просмотра списка изменений.

    - Переключение просмотра с общего на для класса.
    - Перемещает в конец списка изменений.
    - Позволяет перемешаться по страницам изменений вперёд и назад.
    """
    # Смена режима просмотра: только для класса/всего расписания
    if callback_data.action == "switch":
        cl = user.cl if callback_data.cl == "None" else None
    else:
        cl = None if callback_data.cl == "None" else callback_data.cl

    # Загружаем намерение из базы данных
    db_intent = await user.intents.filter(name=callback_data.intent).get()
    if db_intent is not None:
        intent = Intent.from_str(db_intent.intent)
    else:
        intent = None

    # Если указан класс и выбран класс по умолчанию
    # Заменяем намерения на просмотр для класса по умолчанию
    if cl is not None and user.cl is not None:
        if intent is not None:
            intent = intent.reconstruct(platform.view.sc, cl=cl)
        else:
            intent = platform.view.sc.construct_intent(cl=cl)

    # Если намерение не указано. получаем полный список изменений
    if intent is None:
        updates = platform.view.sc.updates
    # Если намерение указан, фильтруем результаты поиска
    else:
        updates = platform.view.sc.get_updates(intent)
    i = max(min(int(callback_data.page), len(updates) - 1), 0)

    # Если в результате есть записи об изменениях
    if len(updates):
        # Переключаемся на последнюю запись
        if callback_data.action in ("last", "switch"):
            i = len(updates) - 1

        # Перемещаемся на следующая запись
        elif callback_data.action == "next":
            i = (i + 1) % len(updates)

        # Перемещаемся на предыдущая запись
        elif callback_data.action == "back":
            i = (i - 1) % len(updates)

        update = updates[i]
    else:
        update = None

    # Отправляем результат пользователю
    await query.message.edit_text(
        text=get_updates_message(platform, update, cl, intent),
        reply_markup=await get_updates_keyboard(
            i, updates, user, callback_data.intent
        ),
    )
