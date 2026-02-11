"""Предоставляет доступ к счётчикам расписания.

Счётчики позволяют подсчитать определённое количество объектов
в расписании.
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

from sp.counter import CounterTarget, CurrentCounter
from tg.db import User, UserIntent
from sp.intents import Intent
from sp.view.messages import MessagesView
from tg.messages import get_intent_status

router = Router(name=__name__)

# Основные типы счётчиков расписания
_COUNTERS = (
    ("cl", "По классам"),
    ("days", "По дням"),
    ("lessons", "По урокам"),
    ("cabinets", "По кабинетам"),
)

# Типы подгруппы счётчиков
# Другими словарь, что отображать как подгруппу счётчиков
# Если у нас 12 уроков математики, то к примеру подгруппой будет:
# - В каких кабинетах проходят уроки
# - Для каких классов проходил этот урок
# - В какие дни проходят эти уроки математики
_TARGETS = (
    ("none", "Ничего"),
    ("cl", "Классы"),
    ("days", "Дни"),
    ("lessons", "Уроки"),
    ("cabinets", "Кабинеты"),
    ("main", "Общее"),
)


class CounterCallback(CallbackData, prefix="count"):
    """Используется в клавиатуре просмотра счётчиков расписания.

    Описывает какую группу и подгруппу счётчика выбрал пользователь.
    А также какое имя намерения передал для уточнения счётчиков.

    counter (str): Тип счётчика.
    target (str): Цль для отображения счётчика.
    intent (str): Имя пользовательского намерения.

    +----------+-------------------------+
    |counter   | Targets                 |
    +==========+=========================+
    | cl       | days, lessons. cabinets |
    +----------+-------------------------+
    | days     | cl, lessons. cabinets   |
    +----------+-------------------------+
    | lessons  | cl, days, main          |
    +----------+                         |
    | cabinets |                         |
    +----------+-------------------------+
    """

    counter: str
    target: CounterTarget
    intent: str


# Вспомогательные функции
# =======================


async def get_counter_keyboard(
    user: User,
    counter: str,
    target: CounterTarget,
    active_intent: str | None = None,
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для просмотра счётчиков расписания.

    Позволяет просматривать счётчики расписания по группам и целям:
    Более подробно про работу счётчиков можно прочитать в классе
    CurrentCounter.

    Buttons:

    - home => Вернуться к главному сообщению бота.
    - count:{counter}:{target} => Переключиться на нужный счётчик.
    """
    inline_keyboard = [
        [InlineKeyboardButton(text="◁", callback_data="home")],
        [],
    ]

    # Добавляем типы счётчиков расписания
    for k, v in _COUNTERS:
        # Пропускаем счётчики, которые которые совпадают с подгруппой
        if k in (counter, target.value):
            continue

        # Добавляем кнопку выбора группы счётчик в первый ряд клавиатуры
        inline_keyboard[0].append(
            InlineKeyboardButton(
                text=v,
                callback_data=f"count:{k}:{target.value}:{active_intent}",
            )
        )

    # Добавляем подгруппы счётчиков
    for k, v in _TARGETS:
        # Пропускаем повторяющиеся подгруппы с текущим типом счётчика
        # а также с текущей подгруппой
        if k in (target.value, counter):
            continue

        # Пропускаем main подгруппу для НЕ index счётчика
        if k == "main" and counter not in ("lessons", "cabinets"):
            continue

        # Пропускаем подгруппу уроков и кабинетов для index счётчика
        if counter in ("lessons", "cabinets") and k in ("lessons", "cabinets"):
            continue

        # Если у пользователя не указан класс пропускаем счётчика
        # cl/lessons т.к. его вывод слишком большой без фильтрации
        # по классам в расписании
        if counter == "cl" and k == "lessons" and user.cl == "":
            continue

        inline_keyboard[1].append(
            InlineKeyboardButton(
                text=v, callback_data=f"count:{counter}:{k}:{active_intent}"
            )
        )

    # Добавляем клавиатуру выбора намерений пользователя
    for i, x in enumerate(await user.intents.all()):
        if i % 3 == 0:
            inline_keyboard.append([])

        if x.name == active_intent:
            inline_keyboard[-1].append(
                InlineKeyboardButton(
                    text=f"✅ {x.name}",
                    callback_data=f"count:{counter}:{target.value}:",
                )
            )
        else:
            inline_keyboard[-1].append(
                InlineKeyboardButton(
                    text=f"⚙️ {x.name}",
                    callback_data=f"count:{counter}:{target.value}:{x.name}",
                )
            )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_counter_message(
    view: MessagesView,
    user: User,
    counter: str,
    target: CounterTarget | None = None,
    intent: Intent | None = None,
) -> str:
    """Собирает сообщение с результатами работы счётчиков.

    В зависимости от выбранного счётчика использует соответствующую
    функцию счётчика.
    Более подробно о работе счётчиков смотрите в классе CurrentCounter.
    """
    # Шапка сообщения
    # Добавляем описание намерения, если оно имеется
    if target is not None:
        message = f"✨ Счётчик {counter}/{target.value}:"
    else:
        message = f"✨ Счётчик {counter}:"

    if intent is not None:
        message += f"\n⚙️ {get_intent_status(intent)}"
    else:
        intent = Intent()

    cur_counter = CurrentCounter(view.sc, intent)

    # Счётчик по классам
    if counter == "cl":
        # Дополнительно передаём намерение, если подгруппа по урокам
        # Ибо иначе результат работы будет слишком большим для бота
        if target == CounterTarget.LESSONS:
            cur_counter.intent = Intent(
                cl=set(
                    user.cl,
                ),
                days=cur_counter.intent.days,
                lessons=cur_counter.intent.lessons,
                cabinets=cur_counter.intent.cabinets,
            )
        groups = cur_counter.cl()

    # Счётчик по дням
    elif counter == "days":
        groups = cur_counter.days()

    # Счётчики по индексам
    elif counter == "lessons":
        groups = cur_counter.lessons()
    else:
        groups = cur_counter.cabinets()

    message += view.counter(groups=groups, target=target)
    return message


# Обработчики команд
# ==================


@router.message(Command("counter"))
async def counter_handler(
    message: Message, user: User, view: MessagesView
) -> None:
    """Переводит в меню просмотра счётчиков расписания."""
    await message.answer(
        text=get_counter_message(view, user, "lessons", CounterTarget.MAIN),
        reply_markup=await get_counter_keyboard(
            user=user, counter="lessons", target=CounterTarget.MAIN
        ),
    )


@router.callback_query(CounterCallback.filter())
async def counter_callback(
    query: CallbackQuery,
    callback_data: CounterCallback,
    user: User,
    view: MessagesView,
) -> None:
    """Клавиатура для переключения счётчиков расписания."""
    counter = callback_data.counter
    if callback_data.target is None or callback_data.target in ("", "none"):
        target = CounterTarget.NONE
    else:
        target = callback_data.target

        # Если счётчик равен подгруппу, обнуляем подгруппу
        if counter == target.value:
            target = CounterTarget.NONE

        # Если установлен счётчик по классам, а подгруппа по урокам
        # Сбрасываем подгруппу, если класс не указан
        if counter == "cl" and target == "lessons" and user.cl == "":
            target = CounterTarget.NONE

    # Загружаем намерения из хранилища пользователей
    db_intent = await UserIntent.get_or_none(
        user=user, name=callback_data.intent
    )
    if db_intent is not None:
        intent = Intent.from_str(db_intent.intent)
    else:
        intent = None

    # Отправляем сообщение пользователю
    await query.message.edit_text(
        text=get_counter_message(view, user, counter, target, intent),
        reply_markup=await get_counter_keyboard(
            user=user,
            counter=counter,
            target=target,
            active_intent=callback_data.intent,
        ),
    )
