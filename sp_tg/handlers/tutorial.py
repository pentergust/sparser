"""Предоставляет доступ к многостраничной справке по использованию бота.

Это опциональный обработчик.
В страницах справки указано как использовать бота.
О том, как вы можете составлять запросы.
Какие параметры можете указывать в запросах и поиске.
Где можно брать доступные значения параметров.

Содержит:
    TutorialCallback => Фильтр данных.
    /tutorial => Отправить сообщение справки.
    tutorial:{page} => Перемещение по справке.

Author: Milinuri Nirvalen
Version: 2.2
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

router = Router(name=__name__)


# Тексты сообщений
# ================

# Сообщения интерактивного обучения по запросам к расписанию
_TUTORIAL_MESSAGES = [
    (
        "💡 Хотите научиться писать запросы?"
        "\nНа самом деле всё намного легче."
        "\nПройдите это простое обучение и убедитесь в этом сами."
        "\n\nВы можете пройти обучение с как самого начала,"
        "так и выбрать интересующую вас страницу."
    ),
    (
        "1. Будьте проще"
        "\n\nВсё стремится к простоте. Запросы не исключение."
        '\nТак ли нужно указывать все эти "посторонние" слова?'
        "\nНет, совсем не обязательно! Они никак не влияют на запрос."
        "\n\n🔶 Вот несколько простых примеров, чтобы понять о чём речь:"
        "\n\n❌ уроки на завтра"
        "\n✅ Завтра"
        "\n\n❌ Расписание для 9в на вторник"
        "\n✅ 9в вторник"
        "\n\nПорядок ключевых слов не имеет значение."
        "\n🌲 матем 8в = 8в матем"
        "\nБыла ли математика в 8в или 9в в математике для нас не важно."
    ),
    (
        "2. Классы"
        "\n\nНачнём с самого простого - классов."
        "\nХотите расписание - просто напишите нужный класс."
        "\n\n-- 7г 6а ➜ можно сразу для нескольких классов."
        "\nЕсли вы не укажите день, то получите расписание на сегодня/завтра."
        "\n🔸 На сегодня - если уроки ещё идут."
        "\n🔸 На завтра - если сегодня уроки уже кончились."
        "\n\n🔎 Ещё классы используются в поиске по уроку/кабинету:"
        "\n\n- химия 8б ➜ Все уроки химии для 9б."
        "\n- 9в 312 ➜ Все уроки в 312 кабинете для 9в"
        "\n\n💡 Посмотреть список всех классов можно в статусе:"
        '\n-- По кнопке "ещё" в главном меню.'
        "\n-- По команде /info"
    ),
    (
        "3. Дни недели"
        "\n\nВы можете более явно указать дни недели в запросах и поиске."
        "\nЕсли указать только день, то получите расписание для вашего класса."
        "\nОднако если вы предпочли не указывать класс по умолчанию,"
        "То получите достаточно интересный результат"
        "\n\n✏️ Как вы можете указать дни"
        "\n-- Понедельник - суббота."
        "\n-- пн - сб."
        "\n-- Сегодня, завтра, неделя."
        "\n\n-- вт ➜ Расписание для вашего класса по умолчанию на вторник."
        '\n\nНапоминаем что не обязательно указывать "посторонние" слова'
        "\n❌ Уроки для 5г на среду"
        "\n✅ 5г среда"
        "\n\n🔎 В поиске если день не указан, то результат выводится на неделю."
        "\n-- матем вт ➜ Все уроки математики на вторник"
        "\n-- пт 312 ➜ Все уроки в 312 кабинете на пятницу"
    ),
    (
        "4. Поиск по урокам"
        "\n\n🔎 Укажите точное название урока для его поиска в расписании."
        "\nЕсли не указаны прочие параметры, расписание для всех на неделю."
        "\n\n✏️ Вы можете указать класс, день, кабинет в параметрах."
        "\n\n-- матем ➜ Вся математика за неделю для всех классов."
        "\n-- химия вторник 10а ➜ Более точный поиск."
        "\n\n⚠️ Если ввести несколько уроков, будет взят только первый."
        "\nЧтобы результат поиска не было слишком длинным."
        "\n\n💡 Посмотреть все классы можно в счётчиках:"
        '\n-- По кнопке "Ещё" ➜ "Счётчики"'
        "\n-- По команде /counter"
    ),
    (
        "5. Поиск по кабинетам"
        "\n🔎 Укажите кабинет, чтобы взглянуть на расписание от его лица."
        "\nЕсли прочие параметры не указаны, расписание для всех на неделю."
        "\n\n✏️ Вы можете указать класс, день, урок в параметрах."
        "\n\n-- 328 ➜ Всё что проходит в 328 кабинете за неделю."
        "\n-- 312 литер вторник 7а ➜ Более точный поиск."
        "\n\n⚠️ Если указать несколько кабинетов, будет взят только первый."
        "\nЧтобы результат поиска не был слишком длинным."
        "\nОднако можно указать несколько предметов в поиске по кабинету."
        "\n\n💡 Посмотреть все кабинеты можно в счётчиках:"
        '\n-- По кнопке "Ещё" ➜ "Счётчики" ➜ "По урокам"'
        '\n-- По команде /counter ➜ "По урокам"'
    ),
    (
        "6. Групповые чаты"
        "\n\n🌟 Вы можете добавить бота в ваш чат."
        "\nДля того чтобы использовать бота вместе."
        "\nКласс устанавливается один на весь чат."
        "\n\n🌲 Вот некоторые особенности при использовании в чате:"
        "\n\n/set_class [класс] - чтобы установить класс в чате."
        "\nИли ответьте классом на сообщение бота (9в)."
        "\n\n✏️ Чтобы писать запросы в чате, используйте команду /sc [запрос]"
        "\nИли ответьте запросом на сообщение бота."
        "\n\n⚙️ Имейте ввиду что доступ к боту имеют все участники чата."
        "\nЭто также касается и настроек бота."
    ),
    (
        "🎉 Поздравляем с прохождением обучения!"
        "\nТеперь вы знаете всё о составлении запросов к расписанию."
        "\nПриятного вам использования бота."
        "\nВы умничка. ❤️"
    ),
]


# Функции для сборки клавиатур
# ============================


def get_tutorial_keyboard(page: int) -> InlineKeyboardMarkup:
    """Клавиатура многостраничного обучения.

    Используется для перемещения между страницами обучения.
    Содержит кнопку для запуска и закрытия справки.
    Кнопки перемещения на следующую и предыдущую страницы.
    Содержание для быстрого переключения страниц.

    Buttons:
        delete_msg => Удалить сообщение.
        tutorial:{page} => Сменить страницу справки.
    """
    inline_keyboard = []

    # Если это первая страница -> без кнопки назад
    if page == 0:
        inline_keyboard.append(
            [InlineKeyboardButton(text="🚀 Начать", callback_data="tutorial:1")]
        )

    # Кнопки для управления просмотром
    elif page != len(_TUTORIAL_MESSAGES) - 1:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="◁", callback_data=f"tutorial:{page - 1}"
                ),
                InlineKeyboardButton(
                    text="🌟 Дальше", callback_data=f"tutorial:{page + 1}"
                ),
            ]
        )

        # Краткое содержание для быстрого перемещения
        for i, x in enumerate(_TUTORIAL_MESSAGES[1:-1]):
            if i + 1 == page:
                continue
            inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=x.splitlines()[0],
                        callback_data=f"tutorial:{i + 1}",
                    )
                ]
            )

        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="❌ Закрыть", callback_data="delete_msg"
                )
            ]
        )

    # Завершение обучения
    else:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="🎉 Завершить", callback_data="delete_msg"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


# Callback Data
# =============


class TutorialCallback(CallbackData, prefix="tutorial"):
    """Используется при просмотре постраничной справки.

    Позволяет перемещаться между страницами справки.

    page (int): Текущая страница справки.
    """

    page: int


# Обработчики
# ===========


@router.message(Command("tutorial"))
async def tutorial_handler(message: Message) -> None:
    """Отправляет интерактивное обучение по составлению запросов."""
    await message.delete()
    await message.answer(
        text=_TUTORIAL_MESSAGES[0], reply_markup=get_tutorial_keyboard(0)
    )


@router.callback_query(TutorialCallback.filter())
async def tutorial_call(
    query: CallbackQuery, callback_data: TutorialCallback
) -> None:
    """Отправляет страницу интерактивного обучения."""
    await query.message.edit_text(
        text=_TUTORIAL_MESSAGES[callback_data.page],
        reply_markup=get_tutorial_keyboard(callback_data.page),
    )
