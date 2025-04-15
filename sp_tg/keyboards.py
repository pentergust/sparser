"""Содержит функции для генерации динамических клавиатур.

Это общие функции для генерации InlineKeyboardMarkup.
Они могут быть использованы всеми обработчиками бота.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from sp.enums import SHORT_DAY_NAMES

# Статическая клавиатура для выбора класса.
# Она появляется, когда пользователь переходит в состояние выбора класса.
# Позволяет быстро отвязывать пользователя от класса.
# А также ознакомить с преимуществами, которые получит пользователь
# если укажет свой класс по умолчанию.
PASS_SET_CL_MARKUP = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Без класса", callback_data="pass"),
            InlineKeyboardButton(
                text="Преимущества класса", callback_data="cl_features"
            ),
        ]
    ]
)


# Для расписания уроков --------------------------------------------------------


def get_week_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для получение расписания на неделю.

    Используется в сообщении с расписанием уроков.
    Когда режим просмотра выставлен "на сегодня".
    Также содержит кнопки для возврата домой и выбора дня недели.

    Buttons:

    - home => Возврат на главный экран.
    - sc:{cl}:week => Получить расписание на неделю для класса.
    - select_day:{cl} => Выбрать день недели для расписания.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠Домой", callback_data="home"),
                InlineKeyboardButton(
                    text="На неделю", callback_data=f"sc:{cl}:week"
                ),
                InlineKeyboardButton(
                    text="▷", callback_data=f"select_day:{cl}"
                ),
            ]
        ]
    )


def get_sc_keyboard(cl: str, relative_day: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для получения расписания на сегодня.

    Используется в сообщениях с расписанием уроков.
    Когда режим просмотра выставлен "на неделю".
    Также содержит кнопки для возврата домой и выбора дня недели.

    Buttons:

    - home => Возврат в домашний раздел.
    - sc:{cl}:today => Получить расписание на сегодня для класса.
    - select_day:{cl} => Выбрать день недели для расписания.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠Домой", callback_data="home"),
                InlineKeyboardButton(
                    text=relative_day, callback_data=f"sc:{cl}:today"
                ),
                InlineKeyboardButton(
                    text="▷", callback_data=f"select_day:{cl}"
                ),
            ]
        ]
    )


def get_select_day_keyboard(cl: str, relative_day: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора дня недели в расписании.

    Используется в сообщения с расписанием.
    Позволяет выбрать один из дней недели.
    Автоматически подставляя указанный класс в запрос.

    Buttons:

    - sc:{cl}:{0..6} => Получить расписания для указанного дня.
    - sc:{cl}:today => Получить расписание на сегодня.
    - sc:{cl}:week => получить расписание на неделю.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=x, callback_data=f"sc:{cl}:{i}")
                for i, x in enumerate(SHORT_DAY_NAMES)
            ],
            [
                InlineKeyboardButton(text="◁", callback_data="home"),
                InlineKeyboardButton(
                    text=relative_day, callback_data=f"sc:{cl}:today"
                ),
                InlineKeyboardButton(
                    text="Неделя", callback_data=f"sc:{cl}:week"
                ),
            ],
        ]
    )


# Основные клавиатуры ----------------------------------------------------------


def get_other_keyboard(
    cl: str | None = None, home_button: bool | None = True
) -> InlineKeyboardMarkup:
    """Собирает дополнительную клавиатуру.

    Дополнительная клавиатура содержит не часто используемые функции.
    Чтобы эти разделы не занимали место на главном экране и не пугали
    пользователей большим количеством разных кнопочек.

    Buttons:

    - set_class => Сменить класс.
    - count:lessons:main: => Меню счётчиков бота.
    - updates:last:0:{cl}: => Последняя страница списка изменений.
    - tutorial:0 => первая страница общей справки.
    - intents => Раздел настройки намерений пользователя.
    - home => Вернуться на главную страницу.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="⚙️ Сменить класс", callback_data="set_class"
            ),
            InlineKeyboardButton(
                text="📊 Счётчики", callback_data="count:lessons:main:"
            ),
            InlineKeyboardButton(
                text="📜 Изменения", callback_data=f"updates:last:0:{cl}:"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🌟 Обучение", callback_data="tutorial:0"
            ),
            InlineKeyboardButton(text="💼 Намерения", callback_data="intents"),
        ],
    ]

    if home_button:
        buttons[-1].append(
            InlineKeyboardButton(text="🏠 Домой", callback_data="home")
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_keyboard(
    cl: str | None = None, relative_day: str | None = None
) -> InlineKeyboardMarkup:
    """Возвращает главную клавиатуру бота.

    Главная клавиатуры предоставляет доступ к самым часто используемым
    разделам бота, таким как получение расписания для класса по
    умолчанию или настройка оповещений.
    Если пользователь не указал класс - возвращается дополнительная
    клавиатура, но без кнопки возврата домой.

    Buttons:

    - other => Вызов дополнительной клавиатуры.
    - notify => Меню настройки уведомлений пользователя.
    - sc:{cl}:today => Получаем расписания на сегодня/завтра для класса.
    """
    if cl is None:
        return get_other_keyboard(cl, home_button=False)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔧 Ещё", callback_data="other"),
                InlineKeyboardButton(
                    text="🔔 Уведомления", callback_data="notify"
                ),
                InlineKeyboardButton(
                    text=f"📚 На {relative_day}", callback_data=f"sc:{cl}:today"
                ),
            ]
        ]
    )
