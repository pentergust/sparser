"""Настройка системы уведомлений бота.

Позволяет пользователям настроить систему уведомлений бота.

- Включить лии отключить рассылку уведомлений.
- Включить или отключить рассылку расписания в определённый час.
"""

from collections.abc import Iterable

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from sp.db import User
from tg.filters import IsAdmin

router = Router(name=__name__)


class NotifyCallback(CallbackData, prefix="notify"):
    """Используется при настройке уведомлений пользователя.

    action (str): Какое выполнить действие: add, remove, on, off.
    hour (int): Для какого часа применять изменение.

    - on: Включить уведомления.
    - off: Отключить уведомления.
    - add: Включить рассылку расписания в указанный час.
    - remove: Отключить рассылку расписания в указанный час.
    """

    action: str
    hour: int


def get_notify_keyboard(
    enabled: bool, hours: Iterable[tuple[int, bool]]
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для настройки уведомлений.

    Используется для управления оповещениями.
    Позволяет включить/отключить уведомления.
    Настроить дни для рассылки расписания.
    Сбросить все часы рассылки расписания.

    Buttons:

    - notify:on:0 => Включить уведомления бота.
    - notify:off:0 => Отключить уведомления бота.
    - notify:reset:0 => Сбросить часы для рассылки расписания.
    - notify:add:{hour} => Включить рассылку для указанного часа.
    - notify:remove:{hour} => Отключить рассылку для указанного часа.
    """
    inline_keyboard = [[InlineKeyboardButton(text="◁", callback_data="home")]]

    # если уведомлений отключены, нам нужно только кнопка включения
    if not enabled:
        inline_keyboard[0].append(
            InlineKeyboardButton(
                text="🔔 Включить", callback_data="notify:on:0"
            )
        )
    else:
        # Кнопка выключения уведомлений
        inline_keyboard[0].append(
            InlineKeyboardButton(
                text="🔕 Выключить", callback_data="notify:off:0"
            )
        )
        # Если пользователь уже указал какой-то час, добавляем кнопку
        # для быстрого сброса всей рассылки расписания.
        if hours:
            inline_keyboard[0].append(
                InlineKeyboardButton(
                    text="❌ Сброс", callback_data="notify:reset:0"
                )
            )
        # Собираем клавиатуру для настройки времени отправки рассылки
        hours_line: list[InlineKeyboardButton] = []
        for hour, status in hours:
            if hour % 6 == 0:
                inline_keyboard.append(hours_line)
                hours_line = []

            if status:
                hours_line.append(
                    InlineKeyboardButton(
                        text=f"✔️{hour}", callback_data=f"notify:remove:{hour}"
                    )
                )
            else:
                hours_line.append(
                    InlineKeyboardButton(
                        text=str(hour), callback_data=f"notify:add:{hour}"
                    )
                )

        if hours_line:
            inline_keyboard.append(hours_line)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_notify_message(enabled: bool, hours: Iterable[tuple[int, bool]]) -> str:
    """Отправляет сообщение с информацией о статусе уведомлений.

    Сообщение о статусе уведомлений содержит в себе:
    Включены ли сейчас уведомления.
    Краткая информация об уведомлениях.
    В какие часы рассылается расписание уроков.
    """
    if enabled:
        message = (
            "🔔 Уведомления включены."
            "\nВы получите уведомление, если расписание изменится."
            "\n\nТакже вы можете настроить отправку расписания."
            "\nВ указанное время бот отправит расписание вашего класса."
        )
        active_hours = [hour[0] for hour in hours if hour[1]]
        if len(active_hours) > 0:
            message += "\n\nРасписание будет отправлено в: "
            message += ", ".join(map(str, active_hours))
    else:
        message = "🔕 уведомления отключены.\nНикаких лишних сообщений."

    return message


# Обработка команд
# ================


@router.message(Command("notify"))
async def notify_handler(message: Message, user: User) -> None:
    """Переводит в меню настройки системы уведомлений."""
    await message.answer(
        text=get_notify_message(user.notify, user.get_hours()),
        reply_markup=get_notify_keyboard(user.notify, user.get_hours()),
    )


# Обработка Callback запросов
# ===========================


@router.callback_query(F.data == "notify")
async def notify_callback(query: CallbackQuery, user: User) -> None:
    """Переходит к разделу настройки системы уведомлений."""
    await query.message.edit_text(
        text=get_notify_message(user.notify, user.get_hours()),
        reply_markup=get_notify_keyboard(user.notify, user.get_hours()),
    )


@router.callback_query(NotifyCallback.filter(), IsAdmin())
async def notify_mod_callback(
    query: CallbackQuery, callback_data: NotifyCallback, user: User
) -> None:
    """Применяет настройки к системе уведомлениям.

    - Отключить или включить уведомления.
    - Включить или отключить рассылку в определённый час.
    - Сбросить время рассылки расписания.
    """
    # Включает отправку всех уведомлений
    if callback_data.action == "on":
        user.notify = True

    # Отключает отправку всех уведомлений
    elif callback_data.action == "off":
        user.notify = False

    # Включает рассылку расписания в определённый час
    elif callback_data.action == "add":
        user.set_hour(callback_data.hour)

    # Отключает рассылку уведомлений в определённый час
    elif callback_data.action == "remove":
        user.reset_hour(callback_data.hour)

    # Сбрасывает рассылку расписания в определённый часы
    elif callback_data.action == "reset":
        user.reset_hours()

    # Сохраняем данные пользователя
    await user.save()
    await query.message.edit_text(
        text=get_notify_message(user.notify, user.get_hours()),
        reply_markup=get_notify_keyboard(user.notify, user.get_hours()),
    )
