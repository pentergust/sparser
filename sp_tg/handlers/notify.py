"""Настройка системы уведомлений бота.

Позволяет пользователям настроить систему уведомлений бота.

- Включить лии отключить расслыку уведомлений.
- Включить или отключить рассылку расписнаия в определённый час.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from sp.users.storage import User
from sp_tg.filters import IsAdmin

router = Router(name=__name__)


class NotifyCallback(CallbackData, prefix="notify"):
    """Испольуется при настройке уведомлений пользователя.

    action (str): Какое выполнить действие: add, remove, on, off.
    hour (int): Для какого часа применять изменение.

    - on: Включить увдомления.
    - off: Откплючить уведомления.
    - add: Включить рассылку расписания в указанный час.
    - remove: Отключить рассылку расписания в указанный час.
    """

    action: str
    hour: int


def get_notify_keyboard(enabled: bool, hours: list[int]
) -> InlineKeyboardMarkup:
    """Возвращет клавиатуру для настройки уведомлений.

    Используется для управления оповещениями.
    Позволяет включить/отключить уведомления.
    Настроить дни для рассылки расписания.
    Сброисить все часы рассылки расписания.

    Buttons:

    - notify:on:0 => Включить уведомления бота.
    - notify:off:0 => Отключить уведомления бота.
    - notify:reset:0 => Сбросить часы для рассылки расписния.
    - notify:add:{hour} => Включить рассылку для указанного часа.
    - notify:remove:{hour} => Отключить рассылку для указанного часа.

    :param enabled: Включены ли уведомления у пользователя.
    :type enabled: bool
    :param hours: В какие часы нужно рассылать расписнаи пользователю.
    :type hours: list[int]
    :return: Клавиатура для настройки системы уведомлений.
    :rtype: InlineKeyboardMarkup
    """
    inline_keyboard = [[InlineKeyboardButton(text="◁", callback_data="home")]]

    # если уведомлений отключены, нам нужно только кнопка включения
    if not enabled:
        inline_keyboard[0].append(InlineKeyboardButton(
                text="🔔 Включить", callback_data="notify:on:0"
        ))
    else:
        # Кнопка выключения уведомлений
        inline_keyboard[0].append(InlineKeyboardButton(
            text="🔕 Выключить", callback_data="notify:off:0"
        ))
        # Если пользователь уже указал какой-то час, добавляем кнопку
        # для быстрого сброса всей расссылки расписнаия.
        if hours:
            inline_keyboard[0].append(InlineKeyboardButton(
                text="❌ Сброс", callback_data="notify:reset:0"
            ))
        # Собираем клавиатуру для настроки времени отправки рассылки
        hours_line = []
        for i, x in enumerate(range(6, 24)):
            if x % 6 == 0:
                inline_keyboard.append(hours_line)
                hours_line = []

            if x in hours:
                hours_line.append(
                    InlineKeyboardButton(
                        text=f"✔️{x}", callback_data=f"notify:remove:{x}"
                ))
            else:
                hours_line.append(InlineKeyboardButton(
                    text=str(x), callback_data=f"notify:add:{x}"
                ))

        if len(hours_line):
            inline_keyboard.append(hours_line)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_notify_message(enabled: bool, hours: list[int]) -> str:
    """Отправляет сообщение с информацией о статусе уведомлений.

    Сообщение о статусе уведомлений содержит в себе:
    Включены ли сейчас уведомления.
    Краткая инфомрация об уведомленях.
    В какие часы рассылается расписание уроков.

    :param enabled: Включены ли уведомления у пользователя.
    :type enabled: bool
    :param hours: В какие часы отправлять расписание пользователю.
    :type hours: list[int]
    :return: Сообщение с инфомрацией об уведомлениях.
    :rtype: str
    """
    if enabled:
        message = ("🔔 Уведомления включены."
            "\nВы получите уведомление, если расписание изменится."
            "\n\nТакже вы можете настроить отправку расписания."
            "\nВ указанное время бот отправит расписание вашего класса."
        )
        if len(hours) > 0:
            message += "\n\nРасписание будет отправлено в: "
            message += ", ".join(map(str, set(hours)))
    else:
        message = "🔕 уведомления отключены.\nНикаких лишних сообщений."

    return message


# Обработка команд
# ================

@router.message(Command("notify"))
async def notify_handler(message: Message, user: User):
    """Переводит в меню настройки системы уведомлений."""
    enabled = user.data.notifications
    hours = user.data.hours
    await message.answer(
        text=get_notify_message(enabled, hours),
        reply_markup=get_notify_keyboard(enabled, hours),
    )


# Обработка Callback запросов
# ===========================

@router.callback_query(F.data == "notify")
async def notify_callback(query: CallbackQuery, user: User) -> None:
    """Переходит к разделу настройки системы уведомлений."""
    enabled = user.data.notifications
    hours = user.data.hours
    await query.message.edit_text(
        text=get_notify_message(enabled, hours),
        reply_markup=get_notify_keyboard(enabled, hours),
    )

@router.callback_query(NotifyCallback.filter(), IsAdmin())
async def notify_mod_callback(
    query: CallbackQuery, callback_data: NotifyCallback, user: User
) -> None:
    """Применяет настройки к системе уведомлениям.

    - Отключить или включить уведлмления.
    - Включить или отключить рассылку в определённый час.
    - Сбросить время рассылки расписания.
    """
    # Включает отправку всех уведомлений
    if callback_data.action == "on":
        user.set_notify_on()

    # Отключает отправку всех уведомлений
    elif callback_data.action == "off":
        user.set_notify_off()

    # Включает расслыку расписнаия в определённый час
    elif callback_data.action == "add":
        user.add_notify_hour(callback_data.hour)

    # Отключает расслыку уведомленяи в определённый час
    elif callback_data.action == "remove":
        user.remove_notify_hour(callback_data.hour)

    # Сбрасывает расслыку расписания в определённый часы
    elif callback_data.action == "reset":
        user.reset_notify()

    # Сохраняем данные пользователя
    user.update()
    enabled = user.data.notifications
    hours = user.data.hours

    # Обновленяем сообщение о статусе и обновлеяет клавиатуру для
    # настройки системы уведомлений
    await query.message.edit_text(
        text=get_notify_message(enabled, hours),
        reply_markup=get_notify_keyboard(enabled, hours),
    )
