"""Система управления намерениями.

СОдержит обработчики и функции, необходимые для работы с системой
намерений.
Просматривать, создавать, изенять и удалять пользовательские намерения.

Пользовательстие намерения позволяют сохранять намерения
для пользователей и уже после их использовать в прочих разделах бота.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from sp.intents import Intent
from sp.messages import SPMessages
from sp_tg.messages import get_intent_status
from sp_tg.utils.intents import IntentObject, UserIntents

router = Router(name=__name__)

days_names = ("пн", "вт", "ср", "чт", "пт", "сб")
_MAX_INTENTS = 9
_MIN_INTENT_NAME = 3
_MAX_INTENT_NAME = 15


# Сообщения работы с намерениями -----------------------------------------------

INTENTS_INFO_MESSAGE = ("Это ваши намерения."
    "\nИспользуйте их, чтобы получить более точные результаты запроса."
    "\nНапример в счётчиках и при получении списка изменений."
    "\nОни будут бережно хранися здесь для вашего удобства."
)

SET_INTENT_NAME_MESSAGE = ("✏️ Теперь дайте имя вашему намерению."
    "\nТак вы сможете отличать его от других намерений в списке."
    "\nТакже это имя будет видно в клавиатуре."
    "\nДавайте напишем что-нбиудь осмысленное от 3-х до 15-ти символов."
    "\n\nЕсли вы передумали, воспользуйтесь командой /cancel."
)

PARSE_INTENT_MESSAGE = ("✏️ Отлично! Теперь давайте опишем намерения."
    "\nВы помните как составлять запросы?"
    "\nТут такой же принцип. Вы словно замораживаете запрос в намерение."
    "\nМожете воспользоваться классами, уроками, днями, кабинетами."
    "\n\n🔶 Некоторые примеры:"
    "\n-- Вторник матем"
    "\n-- 9в 312"
    "\n\nЕсли вы подзабыли как писать запросы - /tutorial"
    "\n/cancel - Если вы Передумали добавлять намерение."
)

INTENTS_REMOVE_MANY_MESSAGE = ("🧹 Режим удаления намерений"
    "\nВам надоели все ваши намерения и вы быстро хотите навести порядок?"
    "\nЭтот инструмент для вас!"
    "\nПросто нажмите на название намерения и оно исчезнет."
    "\nТакже по нажатию на одну кнопку вы можете удалить всё."
    "\nБудьте осторожны."
    "\n\nНажмите \"завершить\" как наиграетесь."
)

INTENTS_LIMIT_MESSAGE = ("💼 Это ваш предел количества намерений."
    "\n🧹 Пожалуйста удалите не используемые намерения,"
    "прежде чем добавлять новые в коллекцию."
    "\n\n/remove_intents - Для быстрой чистки намерений"
    "\nИли воспользуйтесь кнопкой ниже."
)


# Обработка намерений ----------------------------------------------------------

def get_intents_keyboard(intents: list[IntentObject]) -> InlineKeyboardMarkup:
    """Отправляет клавиатуру редактора намерений.

    Используется в главном сообщении редактора.
    Позволяет получить доступ к каждому намерению.
    Добавить новое намерение, если не превышем лимит.
    Или перейти в режим быстрого удаления.

    Buttons:
        intent:show:{name} => Покзаать информацию о намерении.
        intents:remove_mode => Перейти в режим быстрого удаления.
        intent:add: => Добавить новое намерение.
        home => Вернуться на главный экран.

    Args:
        intents (list[IntentObject]): Намерения пользователя.

    Returns:
        InlineKeyboardMarkup: Клавиатура редактора намерений.
    
    """
    inlene_keyboard = [[]]

    if len(intents):
        for i, x in enumerate(intents):
            if i % 3 == 0:
                inlene_keyboard.append([])

            inlene_keyboard[-1].append(InlineKeyboardButton(
                    text=x.name, callback_data=f"intent:show:{x.name}"
                )
            )

        inlene_keyboard.append([InlineKeyboardButton(
                text="🧹 удалить", callback_data="intents:remove_mode"
            )
        ])

    if len(intents) < _MAX_INTENTS:
        inlene_keyboard[-1].append(InlineKeyboardButton(
            text="➕ Добавить", callback_data="intent:add:"
            )
        )
    inlene_keyboard[-1].append(
        InlineKeyboardButton(text="🏠 Домой", callback_data="home")
    )
    return InlineKeyboardMarkup(inline_keyboard=inlene_keyboard)

def get_edit_intent_keyboard(intent_name: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру редактора намерения.

    Исползуется для управления намерением пользвоателя.
    Позволяет изменить имя или параметры намерения, а также удалить его.

    Buttons:
        intent:reparse:{name} => Изменить параметры намерения.
        intent:remove:{name} => Удалить намерение.
        intents => Вернуться к списку намерений.

    Args:
        intent_name (str): Имя намерения для редактирования

    Returns:
        InlineKeyboardMarkup: Клавиатура редактирования намерения.
    
    """
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✏️ Изменить", callback_data=f"intent:reparse:{intent_name}"
            )
    ],
    [
        InlineKeyboardButton(text="<", callback_data="intents"),
        InlineKeyboardButton(
            text="🗑️ Удалить", callback_data=f"intent:remove:{intent_name}"
        )
    ]])

def get_remove_intents_keyboard(intents: list[IntentObject]
) -> InlineKeyboardMarkup:
    """Возаращает клавиатуру быстрого удаления намерений.

    Используется когда необходимо удалить много намерений.
    Позволяет удалять намерения по нажатию на название.
    Также позволяет удалить все намерения пользователя.

    Buttons:
        intent:remove_many:{name} => Удаляет намерение пользователя.
        intents => Вернуться к списку намерений.
        intents:remove_all => Удаляет все намерения пользователя.

    Args:
        intents (list[IntentObject]): Список намерений пользователя.

    Returns:
        InlineKeyboardMarkup: Клавиатура быстрого удаления намерений.
    
    """
    inlene_keyboard = [[]]
    if len(intents):
        for i, x in enumerate(intents):
            if i % 3 == 0:
                inlene_keyboard.append([])
            inlene_keyboard[-1].append(
                InlineKeyboardButton(
                    text=x.name, callback_data=f"intent:remove_many:{x.name}"
                )
            )
        inlene_keyboard.append([
            InlineKeyboardButton(
                text="🧹 Удалить все", callback_data="intents:remove_all"
            )
        ])

    inlene_keyboard[-1].append(
        InlineKeyboardButton(text="✅ Завершить", callback_data="intents")
    )
    return InlineKeyboardMarkup(inline_keyboard=inlene_keyboard)

# Обработка намерений ----------------------------------------------------------

def get_intent_info(name: str, i: Intent) -> str:
    """Возвращает подробное содержимое намерения.

    Args:
        name (str): Имя намерения.
        i (Intent): Экземпляр намерения.

    Returns:
    str: Подробная информация о намерении.
    
    """
    return (f"💼 Намерение \"{name}\":"
        f"\n\n🔸 Классы: {', '.join(i.cl)}"
        f"\n🔸 Дни: {', '.join([days_names[x] for x in i.days])}"
        f"\n🔸 Уроки: {', '.join(i.lessons)}"
        f"\n🔸 Кабинеты: {', '.join(i.cabinets)}"
    )

def get_intents_message(intents: list[IntentObject]) -> str:
    """Отправляет главное сообщение редактора намерений.

    Оно используется чтобы представить список ваших намерений.
    Для чего нужны намерения и что вы можете сделать в редакторе.

    Args:
        intents (list[IntentObject]): Список намерений пользователя.

    Args:
        str: Главное сообщение редактора намерений.
    
    """
    message = f"💼 Ваши намерения.\n\n{INTENTS_INFO_MESSAGE}\n"

    if len(intents) == 0:
        message += "\n\nУ вас пока нет намерений."

    else:
        for x in intents:
            message += f"\n🔸 {x.name}: {get_intent_status(x.intent)}"

    if len(intents) < _MAX_INTENTS:
        message += ("\n\n✏️ /add_intent - Добавить новое намерение."
            "\nИли использовать кнопку ниже."
        )

    return message




@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """Cбрасывает состояние контекста машины состояний."""
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Отменено.")


class EditIntentStates(StatesGroup):
    """Состояния изменения намерения.

    States:
        name => Выбор имение намерения.
        parse => Выбор параментов намерения.
    """

    name = State()
    parse = State()


class IntentCallback(CallbackData, prefix="intent"):
    """Управляет намерением.

    action (str): Что сделать с намерением.
    name (str): Имя намерения.

    Artions:
        add => Добавить новое намерение.
        show => Посмотреть полную информацию о намерении.
        reparse => Именить параметры намерения.
        remove => Удалить намерение.
    """

    action: str
    name: str


# Получение списка намерений ---------------------------------------------------

@router.message(Command("intents"))
async def manage_intents_handler(message: Message,
    intents: UserIntents
) -> None:
    """Команда для просмотра списка намерений пользователя."""
    await message.answer(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )

@router.callback_query(F.data=="intents")
async def intents_callback(query: CallbackQuery, intents: UserIntents) -> None:
    """Кнопка для просмотра списка намерений пользователя."""
    await query.message.edit_text(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )

# Добавление нового намерения --------------------------------------------------

@router.callback_query(IntentCallback.filter(F.action=="add"))
async def add_intent_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Начать добавление нового намерения по кнопке."""
    await state.set_state(EditIntentStates.name)
    await query.message.edit_text(SET_INTENT_NAME_MESSAGE)

@router.message(Command("add_intent"))
async def add_intent_handler(
    message: Message, state: FSMContext, intents: UserIntents
) -> None:
    """Команда для добавления нового намерения.

    Выводит сообщение при достижении предела количества намерений.
    """
    # Если превышено количество максимальных намерений
    if len(intents.get()) >= _MAX_INTENTS:
        await message.answer(INTENTS_LIMIT_MESSAGE,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🗑️ удалить", callback_data="intents:remove_mode")
        ]]))
    else:
        await state.set_state(EditIntentStates.name)
        await message.answer(SET_INTENT_NAME_MESSAGE)

@router.message(EditIntentStates.name)
async def intent_name_handler(message: Message, state: FSMContext) -> None:
    """Устанавливает имя намерения."""
    name = message.text.lower().strip()

    # Если длинна имени больше или меньше нужной
    if len(name) < _MIN_INTENT_NAME or len(name) > _MAX_INTENT_NAME:
        await message.answer(
            text="Имя намерения должно быть от 3-х до 15-ти символов."
        )

    else:
        await state.update_data(name=name)
        await state.set_state(EditIntentStates.parse)
        await message.answer(text=PARSE_INTENT_MESSAGE)

@router.message(EditIntentStates.parse)
async def parse_intent_handler(
    message: Message, state: FSMContext, intents: UserIntents, sp: SPMessages
) -> None:
    """Устанавливает парамеры намерения."""
    i = Intent.parse(sp.sc, message.text.lower().strip().split())
    name = (await state.get_data())["name"]
    intents.add(name, i)
    await state.clear()
    await message.answer(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )

# Режим просмотра намерения ----------------------------------------------------

@router.callback_query(IntentCallback.filter(F.action=="show"))
async def show_intent_callback(
    query: CallbackQuery, intents: UserIntents, callback_data: IntentCallback
) -> None:
    """Просматривать информацию о намерении."""
    intent = intents.get_intent(callback_data.name)
    if intent is None:
        await query.message.edit_text(text="⚠️ Непраивльное имя намерения")
    else:
        await query.message.edit_text(
            text=get_intent_info(callback_data.name, intent),
            reply_markup=get_edit_intent_keyboard(callback_data.name)
        )

@router.callback_query(IntentCallback.filter(F.action=="remove"))
async def remove_intent_callback(
    query: CallbackQuery, intents: UserIntents, callback_data: IntentCallback
) -> None:
    """Удаляет намерение по имени."""
    intents.remove(callback_data.name)
    await query.message.edit_text(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )

@router.callback_query(IntentCallback.filter(F.action=="reparse"))
async def reparse_intent_callback(
    query: CallbackQuery, intents: UserIntents, callback_data: IntentCallback,
    state: FSMContext
) -> None:
    """Изменение параметров намерения."""
    await state.set_state(EditIntentStates.parse)
    await state.update_data(name=callback_data.name)
    await query.message.edit_text(text=PARSE_INTENT_MESSAGE)


# Режим удаления намерений -----------------------------------------------------

@router.message(Command("remove_intents"))
async def intents_remove_mode_handler(
    message: Message, intents: UserIntents
) -> None:
    """Переключает в режим удаления намерений."""
    await message.answer(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=get_remove_intents_keyboard(intents.get())
    )

@router.callback_query(F.data=="intents:remove_mode")
async def intents_remove_mode_callback(
    query: CallbackQuery, intents: UserIntents
) -> None:
    """Переключает в режми удаления намерений."""
    await query.message.edit_text(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=get_remove_intents_keyboard(intents.get())
    )

@router.callback_query(IntentCallback.filter(F.action=="remove_many"))
async def remove_many_intent_callback(
    query: CallbackQuery, intents: UserIntents, callback_data: IntentCallback
) -> None:
    """Удаляет намерение и возвращает в меню удаления."""
    intents.remove(callback_data.name)
    await query.message.edit_text(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=get_remove_intents_keyboard(intents.get())
    )

@router.callback_query(F.data=="intents:remove_all")
async def intents_set_remove_mode_callback(
    query: CallbackQuery, intents: UserIntents
) -> None:
    """Удаляет всен амерения пользвоателя."""
    intents.remove_all()
    await query.message.edit_text(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )
