"""Предоставляет доступ к счётчикам расписания.

Счётчики позволяют подсчитать определённео колическо объектов
в расписании.
"""

from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from sp.counters import (cl_counter, days_counter, group_counter_res,
                         index_counter)
from sp.intents import Intent
from sp.messages import SPMessages, send_counter
from sp.parser import Schedule
from sp_tg.messages import get_intent_status
from sp_tg.utils.intents import UserIntents

router = Router(name=__name__)

# Основные типы счётчиков расписнаия
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

    .. table::

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
    target: str
    intent: str


# Вспомогательные функции
# =======================

def get_counter_keyboard(cl: str, counter: str, target: str,
    intents: UserIntents, intent_name: Optional[str]=""
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для просмотра счётчиков расписания.

    Позволяет просматривать счётчики расписания по группам и целям:

    .. table::

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

    Исользуется клавиатуру для выбрра намерений.
    Чтобы уточнить результаты подсчётов.

    Buttons:

    - home => Вернуться к главному сообщению бота.
    - count:{counter}:{target} => Переключиться на нужный счётчик.

    :param cl: Класс для подстановки в коавиатуру.
    :type cl: str
    :param counter: Текущий тип просмотра счётчика.
    :type counter: str
    :param target: Текущий тип просмотра счётчика.
    :type target: str
    :param intents: Экземпляр хранилища намерений пользователя.
    :type intent: UserIntents
    :param intent_name: Текущее выбранное имя намерения пользователя.
    :type intent_name: Optional[str]
    :return: Клавиатура для просмотра счётчиков расписания.
    :rtype: InlineKeyboardMarkup
    """
    inline_keyboard = [[
            InlineKeyboardButton(text="◁", callback_data="home")
        ],
        []
    ]

    # Добавляем типы счётчиков расписания
    for k, v in _COUNTERS:
        # Пропускаем счётчики, которые которые совпадают с подгруппой
        if counter == k:
            continue

        # Добавляем кнопку выбора группы счётчка в первый ряд клавиатуры
        inline_keyboard[0].append(
            InlineKeyboardButton(
                text=v,
                callback_data=f"count:{k}:{target}:{intent_name}"
            )
        )

    # Добавляем подгруппы счётчиков
    for k, v in _TARGETS:
        # Пропускаем повторяющиеся подгруппы с текущим типом счётчка
        # а также с текущей подгруппой
        if k in (target, counter):
            continue

        # Проускаем main подгруппу для НЕ index счётчика
        if k == "main" and counter not in ("lessons", "cabinets"):
            continue

        # Пропускаем подгруппу уроков и кабинетов для index счётчика
        if counter in ("lessons", "cabinets") and k in ("lessons", "cabinets"):
            continue

        # Если у пользователя не указан класс пропускаем счётчика
        # cl/lessons т.к. его вывод слишком большой без фильтрации
        # по классам в расписании
        if counter == "cl" and k == "lessons" and not cl:
            continue

        inline_keyboard[1].append(
            InlineKeyboardButton(
                text=v,
                callback_data=f"count:{counter}:{k}:{intent_name}"
            )
        )

    # Добавляем клавиатуру выбора намерений пользователя
    for i, x in enumerate(intents.get()):
        if i % 3 == 0:
            inline_keyboard.append([])

        if x.name == intent_name:
            inline_keyboard[-1].append(
                InlineKeyboardButton(
                    text=f"✅ {x.name}",
                    callback_data=f"count:{counter}:{target}:"
                )
            )
        else:
            inline_keyboard[-1].append(
                InlineKeyboardButton(
                    text=f"⚙️ {x.name}",
                    callback_data=f"count:{counter}:{target}:{x.name}"
                )
            )


    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_counter_message(
    sc: Schedule,
    counter: str,
    target: str,
    intent: Optional[Intent]=None
) -> str:
    """Собирает сообщение с результатами работы счётчиков.

    В зависимости от выбранного счётчика использует соответствующую
    функцию счётчика.

    .. table::

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

    :param sc: Экземпляр расписания уроков для отображения счётчиков.
    :type sc: Schedule
    :param counter: Выбранный тип счётчка
    :type counter: str
    :param target: Выбранная подгруппа счётчика, для просмотра.
    :typw target: str
    :param intent: Намерение, для уточнения результатов счётчиков.
    :type intent: Optional[Intent]
    :return: Сообщение с результатов работы счётчиков.
    :rtype: str
    """
    # Шапка сообщения
    # Добавляем описание намерения, если оно имеется
    message = f"✨ Счётчик {counter}/{target}:"
    if intent is not None:
        message += f"\n⚙️ {get_intent_status(intent)}"
    else:
        intent = Intent()

    # Счётчик по классам
    if counter == "cl":
        # Дополнительно передаём намерение, если подгруппа по урокамъ
        # Ибо иначе результат работы будет слишком большим для бота
        if target == "lessons":
            intent = intent.reconstruct(sc, cl=sc.cl)
        res = cl_counter(sc, intent)

    # Счётчик по дням
    elif counter == "days":
        res = days_counter(sc, intent)

    # Счётчики по индексам
    elif counter == "lessons":
        res = index_counter(sc, intent)
    else:
        res = index_counter(sc, intent, cabinets_mode=True)

    # Если счётчик не указан
    if target == "none":
        target = None

    message += send_counter(group_counter_res(res), target=target)
    return message


# Обработчики команд
# ==================

@router.message(Command("counter"))
async def counter_handler(message: Message, sp: SPMessages,
    intents: UserIntents
) -> None:
    """Переводит в меню просмора счётчиков расписания."""
    await message.answer(
        text=get_counter_message(sp.sc, "lessons", "main"),
        reply_markup=get_counter_keyboard(
            cl=(sp.user["class_let"]),
            counter="lessons",
            target="main",
            intents=intents
        ),
    )


@router.callback_query(CounterCallback.filter())
async def counter_callback(
    query: CallbackQuery, sp: SPMessages, callback_data: CounterCallback,
    intents: UserIntents
) -> None:
    """Клавитура для переключения счётчиков расписания."""
    counter = callback_data.counter
    target = callback_data.target

    # Если счётчик равен подгруппу, обнуляем подгруппу
    if counter == target:
        target = None

    # Если установлен счётчик по классам, а подгруппа по урокам
    # Сбрасыфваем подгруппу, если класс не указан
    if counter == "cl" and target == "lessons" and not sp.user["class_let"]:
        target = None

    # Загружаем намерения из хранилища пользователей
    intent = intents.get_intent(callback_data.intent)

    # Отправляем сообщение пользователю
    await query.message.edit_text(
        text=get_counter_message(sp.sc, counter, target, intent),
        reply_markup=get_counter_keyboard(
            cl=sp.user["class_let"],
            counter=counter,
            target=target,
            intents=intents,
            intent_name=callback_data.intent
        )
    )
