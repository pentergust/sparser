"""Система управления намерениями.

Пользовательские намерения позволяют запечатывать намерения, присваивая
им имя, чтобы после быстро использовать их в обработчиках.
Позволяет создавать, изменять и удалять пользовательские намерения.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from sp.db import User, UserIntent
from sp.enums import SHORT_DAY_NAMES
from sp.intents import Intent
from sp.view.messages import MessagesView
from sp_tg.filters import IsAdmin
from sp_tg.messages import get_intent_status

router = Router(name=__name__)

_MAX_INTENTS = 9
_MIN_INTENT_NAME = 3
_MAX_INTENT_NAME = 15


# Сообщения работы с намерениями -----------------------------------------------

INTENTS_INFO_MESSAGE = (
    "Это ваши намерения."
    "\nИспользуйте их, чтобы получить более точные результаты запроса."
    "\nНапример в счётчиках и при получении списка изменений."
    "\nОни будут бережно хранился здесь для вашего удобства."
)

SET_INTENT_NAME_MESSAGE = (
    "✏️ Теперь дайте имя вашему намерению."
    "\nТак вы сможете отличать его от других намерений в списке."
    "\nТакже это имя будет видно в клавиатуре."
    "\nДавайте напишем что-нибудь осмысленное от 3-х до 15-ти символов."
    "\n\nЕсли вы передумали, воспользуйтесь командой /cancel."
)

PARSE_INTENT_MESSAGE = (
    "✏️ Отлично! Теперь давайте опишем намерения."
    "\nВы помните как составлять запросы?"
    "\nТут такой же принцип. Вы словно замораживаете запрос в намерение."
    "\nМожете воспользоваться классами, уроками, днями, кабинетами."
    "\n\n🔶 Некоторые примеры:"
    "\n-- Вторник матем"
    "\n-- 9в 312"
    "\n\nЕсли вы подзабыли как писать запросы - /tutorial"
    "\n/cancel - Если вы Передумали добавлять намерение."
)

INTENTS_REMOVE_MANY_MESSAGE = (
    "🧹 Режим удаления намерений"
    "\nВам надоели все ваши намерения и вы быстро хотите навести порядок?"
    "\nЭтот инструмент для вас!"
    "\nПросто нажмите на название намерения и оно исчезнет."
    "\nТакже по нажатию на одну кнопку вы можете удалить всё."
)

INTENTS_LIMIT_MESSAGE = (
    "💼 Это предел количества намерений."
    "\n🧹 Пожалуйста удалите не используемые намерения, "
    "прежде чем добавлять новые в коллекцию."
    "\n\n/remove_intents - Для быстрой чистки намерений"
)


# Обработка намерений ----------------------------------------------------------


async def get_intents_keyboard(user: User) -> InlineKeyboardMarkup:
    """Отправляет клавиатуру редактора намерений.

    Используется в главном сообщении редактора.
    Позволяет получить доступ к каждому намерению.
    Добавить новое намерение, если не превышает лимит.
    Или перейти в режим быстрого удаления.

    Buttons:
        intent:show:{name} => Показать информацию о намерении.
        intents:remove_mode => Перейти в режим быстрого удаления.
        intent:add: => Добавить новое намерение.
        home => Вернуться на главный экран.
    """
    inline_keyboard: list[list[InlineKeyboardButton]] = [[]]
    intents = await user.intents.all()

    if len(intents):
        for i, x in enumerate(intents):
            if i % 3 == 0:
                inline_keyboard.append([])

            inline_keyboard[-1].append(
                InlineKeyboardButton(
                    text=x.name, callback_data=f"intent:show:{x.name}"
                )
            )

        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="🧹 удалить", callback_data="intents:remove_mode"
                )
            ]
        )

    if len(intents) < _MAX_INTENTS:
        inline_keyboard[-1].append(
            InlineKeyboardButton(text="➕", callback_data="intent:add:")
        )
    inline_keyboard[-1].append(
        InlineKeyboardButton(text="🏠 Домой", callback_data="home")
    )
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_edit_intent_keyboard(intent_name: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру редактора намерения.

    Используется для управления намерением пользователя.
    Позволяет изменить имя или параметры намерения, а также удалить его.

    Buttons:
        intent:reparse:{name} => Изменить параметры намерения.
        intent:remove:{name} => Удалить намерение.
        intents => Вернуться к списку намерений.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="<", callback_data="intents"),
                InlineKeyboardButton(
                    text="🗑️ Удалить",
                    callback_data=f"intent:remove:{intent_name}",
                ),
                InlineKeyboardButton(
                    text="✏️ Изменить",
                    callback_data=f"intent:reparse:{intent_name}",
                ),
            ]
        ]
    )


async def get_remove_intents_keyboard(user: User) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру быстрого удаления намерений.

    Используется когда необходимо удалить много намерений.
    Позволяет удалять намерения по нажатию на название.
    Также позволяет удалить все намерения пользователя.

    Buttons:
        intent:remove_many:{name} => Удаляет намерение пользователя.
        intents => Вернуться к списку намерений.
        intents:remove_all => Удаляет все намерения пользователя.
    """
    inline_keyboard: list[list[InlineKeyboardButton]] = [[]]
    for i, x in enumerate(await user.intents.all()):
        if i % 3 == 0:
            inline_keyboard.append([])
        inline_keyboard[-1].append(
            InlineKeyboardButton(
                text=x.name, callback_data=f"intent:remove_many:{x.name}"
            )
        )
    inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="🧹 Удалить все", callback_data="intents:remove_all"
            )
        ]
    )

    inline_keyboard[-1].append(
        InlineKeyboardButton(text="✅ Завершить", callback_data="intents")
    )
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


# Обработка намерений ----------------------------------------------------------


def get_intent_info(name: str, i: UserIntent) -> str:
    """Возвращает подробное содержимое намерения."""
    intent = Intent.from_str(i.intent)
    info = (
        f'💼 Намерение "{name}":'
        f"\n\n🔸 Классы: {', '.join(intent.cl)}"
        f"\n🔸 Дни: {', '.join([SHORT_DAY_NAMES[x] for x in intent.days])}"
        f"\n🔸 Уроки: {', '.join(intent.lessons)}"
        f"\n🔸 Кабинеты: {', '.join(intent.cabinets)}"
    )
    if (
        intent.cl == ()
        and intent.cabinets == ()
        and intent.lessons == ()
        and intent.days == ()
    ):
        info += "\n\n⚠️ Вероятно ошибка при чтении намерения, пересоздайте его."
    return info


async def get_intents_message(user: User) -> str:
    """Отправляет главное сообщение редактора намерений.

    Используется чтобы представить список ваших намерений.
    Для чего нужны намерения и что вы можете сделать в редакторе.
    """
    message = f"💼 Ваши намерения.\n\n{INTENTS_INFO_MESSAGE}\n"
    intents = await user.intents.all()

    if len(intents) == 0:
        message += "\n\nУ вас пока нет намерений."
    else:
        for x in intents:
            intent = Intent.from_str(x.intent)
            message += f"\n🔸 {x.name}: {get_intent_status(intent)}"

    if len(intents) < _MAX_INTENTS:
        message += (
            "\n\n✏️ /add_intent - Добавить новое намерение."
            "\nИли использовать кнопку ниже."
        )

    return message


@router.message(Command("cancel"), IsAdmin())
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """Сбрасывает состояние контекста машины состояний."""
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Отменено ...")


class EditIntentStates(StatesGroup):
    """Состояния изменения намерения.

    - name => Выбор имение намерения.
    - parse => Выбор параметров намерения.
    """

    name = State()
    parse = State()


class IntentCall(CallbackData, prefix="intent"):
    """Управляет намерением.

    action (str): Что сделать с намерением.
    name (str): Имя намерения.

    Actions:
        add => Добавить новое намерение.
        show => Посмотреть полную информацию о намерении.
        reparse => Изменить параметры намерения.
        remove => Удалить намерение.
    """

    action: str
    name: str


# Получение списка намерений ---------------------------------------------------


@router.message(Command("intents"))
async def manage_intents_handler(message: Message, user: User) -> None:
    """Команда для просмотра списка намерений пользователя."""
    await message.answer(
        text=await get_intents_message(user),
        reply_markup=await get_intents_keyboard(user),
    )


@router.callback_query(F.data == "intents")
async def intents_callback(query: CallbackQuery, user: User) -> None:
    """Кнопка для просмотра списка намерений пользователя."""
    await query.message.edit_text(
        text=await get_intents_message(user),
        reply_markup=await get_intents_keyboard(user),
    )


# Добавление нового намерения --------------------------------------------------


@router.callback_query(IntentCall.filter(F.action == "add"), IsAdmin())
async def add_intent_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Начать добавление нового намерения по кнопке."""
    await state.set_state(EditIntentStates.name)
    await query.message.edit_text(SET_INTENT_NAME_MESSAGE)


@router.message(Command("add_intent"), IsAdmin())
async def add_intent_handler(
    message: Message, state: FSMContext, user: User
) -> None:
    """Команда для добавления нового намерения.

    Выводит сообщение при достижении предела количества намерений.
    """
    # Если превышено количество максимальных намерений
    if await user.intents.all().count() >= _MAX_INTENTS:
        await message.answer(
            INTENTS_LIMIT_MESSAGE,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🗑️ удалить",
                            callback_data="intents:remove_mode",
                        )
                    ]
                ]
            ),
        )
    else:
        await state.set_state(EditIntentStates.name)
        await message.answer(SET_INTENT_NAME_MESSAGE)


@router.message(EditIntentStates.name, IsAdmin())
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


@router.message(EditIntentStates.parse, IsAdmin())
async def parse_intent_handler(
    message: Message, state: FSMContext, user: User, view: MessagesView
) -> None:
    """Устанавливает парамеры намерения."""
    i = Intent.parse(view.sc, message.text.lower().strip().split())
    if sum(map(len, i)) == 0:
        await message.answer(
            "⚠️ Переданная строка не содержит ни одного ключа, который может "
            "быть использован в намерении.\n"
        )
        return

    name = (await state.get_data())["name"]
    await UserIntent.create(user=user, name=name, intent=i.to_str())
    await state.clear()

    await message.answer(
        text=await get_intents_message(user),
        reply_markup=await get_intents_keyboard(user),
    )


# Режим просмотра намерения ----------------------------------------------------


@router.callback_query(IntentCall.filter(F.action == "show"))
async def show_intent_callback(
    query: CallbackQuery, user: User, callback_data: IntentCall
) -> None:
    """Информацию о намерении."""
    intent = await user.intents.all().get_or_none(name=callback_data.name)
    if intent is None:
        await query.message.edit_text(text="⚠️ Неправильное имя намерения")
    else:
        await query.message.edit_text(
            text=get_intent_info(callback_data.name, intent),
            reply_markup=get_edit_intent_keyboard(callback_data.name),
        )


@router.callback_query(IntentCall.filter(F.action == "remove"), IsAdmin())
async def remove_intent_call(
    query: CallbackQuery, user: User, callback_data: IntentCall
) -> None:
    """Удаляет намерение по его имени."""
    await user.intents.filter(name=callback_data.name).delete()
    await query.message.edit_text(
        text=await get_intents_message(user),
        reply_markup=await get_intents_keyboard(user),
    )


@router.callback_query(IntentCall.filter(F.action == "reparse"), IsAdmin())
async def reparse_intent_call(
    query: CallbackQuery, callback_data: IntentCall, state: FSMContext
) -> None:
    """Изменение параметров намерения."""
    await state.set_state(EditIntentStates.parse)
    await state.update_data(name=callback_data.name)
    await query.message.edit_text(text=PARSE_INTENT_MESSAGE)


# Режим удаления намерений -----------------------------------------------------


@router.message(Command("remove_intents"), IsAdmin())
async def intents_remove_mode_handler(message: Message, user: User) -> None:
    """Переключает в режим удаления намерений."""
    await message.answer(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=await get_remove_intents_keyboard(user),
    )


@router.callback_query(F.data == "intents:remove_mode", IsAdmin())
async def remove_mode_call(query: CallbackQuery, user: User) -> None:
    """Переключает в режим удаления намерений."""
    await query.message.edit_text(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=await get_remove_intents_keyboard(user),
    )


@router.callback_query(IntentCall.filter(F.action == "remove_many"), IsAdmin())
async def remove_many_call(
    query: CallbackQuery, user: User, callback_data: IntentCall
) -> None:
    """Удаляет намерение и возвращает в меню удаления."""
    await user.intents.filter(name=callback_data.name).delete()
    await query.message.edit_text(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=await get_remove_intents_keyboard(user),
    )


@router.callback_query(F.data == "intents:remove_all", IsAdmin())
async def remove_all_call(query: CallbackQuery, user: User) -> None:
    """Удаляет все намерения пользователя."""
    await user.intents.all().delete()
    await user.save()
    await query.message.edit_text(
        await get_intents_message(user),
        reply_markup=await get_intents_keyboard(user),
    )
