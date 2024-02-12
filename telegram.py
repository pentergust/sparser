"""Telegram-бот для доступа к SPMessages.

Полностью реализует доступ ко всем методам SPMessages.
Не считая некоторых ограничений в настройке "намерений" (Intents).

Команды бота для BotFather
--------------------------

sc - Уроки на сегодня
updates - Изменения в расписании
notify - Настроить уведомления
counter - Счётчики уроков/кабинетов
tutorial - Как писать запросы
set_class - Изменить класс
intents - Настроить намерения
add_intent - Добавить намерение
remove_intents - Удалить намерение
help - Главное меню
info - Информация о боте

Author: Milinuri Nirvalen
Ver: 2.2.2 (sp v5.7)
"""

import asyncio
import sqlite3
from datetime import datetime
from os import getenv
from pathlib import Path
from typing import (
    Any, Awaitable,
    Callable,
    Dict,
    NamedTuple,
    Optional,
    Union
)

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from dotenv import load_dotenv
from loguru import logger

from sp.counters import (
    cl_counter,
    days_counter,
    group_counter_res,
    index_counter,
)
from sp.intents import Intent
from sp.messages import SPMessages, send_counter, send_search_res, send_update
from sp.parser import Schedule
from sp.utils import get_str_timedelta

# Настройкки и константы
# ======================

load_dotenv()
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN", "")
dp = Dispatcher()
days_names = ("пн", "вт", "ср", "чт", "пт", "сб")
_TIMETAG_PATH = Path("sp_data/last_update")
DB_CONN = sqlite3.connect("sp_data/tg.db")

# Некоторые константные настройки бота
#   - Максимальное число намерений на одного пользователя
#   - Через сколько секунд выводит предупреждение в статусе
#     о не руботающем скрипте автообновлений.
#   - Предельная длинна для сообщения списка изменений
#   - Минимальная длинна имена намерения.
#   - Максимальная длинна имена намерения.
_BOT_VERSION = "v2.2.2"
_MAX_INTENTS = 9
_ALERT_AUTOUPDATE_AFTER_SECONDS = 3600
_MAX_UPDATE_MESSAGE_LENGTHT = 4000
_MIN_INTENT_NAME = 3
_MAX_INTENT_NAME = 15

# Статические клавиатуры при выборе класса
# pass => Пропустить смену класс и установить None
# cl_features => Список преимуществ если указать класс
PASS_SET_CL_MARKUP = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Без класса", callback_data="pass"
            ),
            InlineKeyboardButton(
                text="Ограничения", callback_data="cl_features"
            )
        ]
    ]
)
BACK_SET_CL_MARKUP = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="◁", callback_data="set_class"),
            InlineKeyboardButton(text="Без класса", callback_data="pass"),
        ]
    ]
)


# Всопомгательный класс
# =====================

class IntentObject(NamedTuple):
    """Используется для описания намерения пользователя.

    name (str): Ключевое имя намерения.
    intent (Ontent): Намерение пользователя.
    """

    name: str
    intent: Intent

class UserIntents:
    """Хранилище намерений пользователя.

    Является обёрткой над базой данных.
    Позволяет получаеть, добавлять и удалять намерений пользователя.

    Args:
        conn (sqlite3.Connection): Подключение к базе данных намерений.
        uid (int): Идентификатор пользователя бота.
    """

    def __init__(self, conn: sqlite3.Connection, uid: int) -> None:
        self._conn = conn
        self._cur = self._conn.cursor()
        self._uid = uid
        self._check_tables()

    def _check_tables(self) -> None:
        self._cur.execute(("CREATE TABLE IF NOT EXISTS intent("
            "user_id TEXT NOT NULL,"
            "name TEXT NOT NULL,"
            "intent TEXT NOT NULL)"
        ))
        self._conn.commit()

    # Работа со списком намерений ----------------------------------------------

    def get(self) -> list[IntentObject]:
        """Получает список всех намерений пользователя."""
        self._cur.execute(
            "SELECT name,intent FROM intent WHERE user_id=?",
            (self._uid,)
        )
        return [IntentObject(n, Intent.from_str(i))
            for n, i in self._cur.fetchall()
        ]

    def get_intent(self, name: str) -> Optional[Intent]:
        """Возвращает первое намерение пользователя по имени."""
        for x in self.get():
            if x.name == name:
                return x.intent

    def remove_all(self):
        """Удаляет все намерение пользователя из базы данных."""
        self._cur.execute("DELETE FROM intent WHERE user_id=?", (self._uid,))
        self._conn.commit()

    # Работа с одним намерением ------------------------------------------------

    def add(self, name: str, intent: Intent) -> None:
        """Добавляет намерение в базу данных.

        Доабвляет запись в базу данных.
        Еслм такое намерение уже существует - обновляет.

        Args:
            name (str): Имя намерения.
            intent (Intent): Намерение для добавления.
        """
        int_s = intent.to_str()
        if self.get_intent(name) is not None:
            self._cur.execute(
                "UPDATE intent SET intent=? WHERE user_id=? AND name=?",
                (int_s, self._uid, name)
            )
        else:
            self._cur.execute(
                "INSERT INTO intent(user_id,name,intent) VALUES(?,?,?);",
                (self._uid, name, int_s)
            )
        self._conn.commit()

    def rename(self, old_name: str, new_name: str) -> None:
        """Изменяет имя намерения.

        Заменяет имя намерения в базе данных на новое.

        Args:
            old_name (str): Старое имя намерения.
            new_name (str): Новое имя намерения.
        """
        self._cur.execute(
            "UPDATE intent SET name=? WHERE user_id=? AND name=?",
            (new_name, self._uid, old_name)
        )
        self._conn.commit()

    def remove(self, name: str) -> None:
        """Удаляет намерение пользователя из базы данных.

        Args:
            name (str): Имя намерения для удаления.
        """
        self._cur.execute(
            "DELETE FROM intent WHERE user_id=? AND name=?",
            (self._uid, name)
        )
        self._conn.commit()


# Добавление Middleware
# =====================

@dp.message.middleware()
@dp.callback_query.middleware()
@dp.error.middleware()
async def user_middleware(
    handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
    event: Union[Update, CallbackQuery, ErrorEvent],
    data: Dict[str, Any],
) -> Any:
    """Добавляет экземпляр SPMessages и намерения пользователя."""
    if isinstance(event, ErrorEvent):
        if event.update.callback_query is not None:
            uid = event.update.callback_query.message.chat.id
        else:
            uid = event.update.message.chat.id
    elif isinstance(event, CallbackQuery):
        uid = event.message.chat.id
    else:
        uid = event.chat.id

    data["sp"] = SPMessages(str(uid))
    data["intents"] = UserIntents(DB_CONN, uid)
    return await handler(event, data)

# Если вы хотите отключить логгирование в боте
# Закомментируйте необходимые вам декораторы
@dp.message.middleware()
@dp.callback_query.middleware()
async def log_middleware(
    handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: Dict[str, Any],
) -> Any:
    """Отслеживает полученные ботом сообщения и callback query."""
    if isinstance(event, CallbackQuery):
        logger.info("[c] {}: {}", event.message.chat.id, event.data)
    else:
        logger.info("[m] {}: {}", event.chat.id, event.text)

    return await handler(event, data)


# Статические тексты сообщений
# ============================

# Главнео сообщение справки бота
HOME_MESSAGE = ("💡 Некоторые интересные примеры запросов:"
    "\n-- 7в 6а на завтра"
    "\n-- уроки 6а на вторник ср"
    "\n-- 312 на вторник пятницу"
    "\n-- химия 228 6а вторник"
    "\n\n🏫 В ваших запросах вы можете использовать:"
    "\n* Урок/Кабинет: Получить все его упоминания."
    "\n* Классы: для которого нужно расписание."
    "\n* Дни недели:"
    "\n-- Если день не указан - на сегодня/завтра."
    "\n-- Понедельник-суббота (пн-сб)."
    "\n-- Сегодня, завтра, неделя."
    "\n\n🌟 Хотите научиться писать запросы? /tutorial"
)

# Сообщение при смене класса
SET_CLASS_MESSAGE = (
    "🌟 Для более удобной работы и получения всех преимуществ,"
    "рекомендуется указать ваш класс."
    "\nЭто позволит быстро просматривать расписание и получать уведомления."
    "\nВы можете ознакомиться с полным списком командой /cl_features."
    "\n\n✨ Просто укажите свой класс следующим сообщением (\"8в\")."
    "\n\nВы также можете пропустить выбор класса, нажав кнопку (/pass)."
    "\n\n💡 Не забывайте, что вы всегда можете сменить класс позже:"
    "\n-- просто отправьте команду /set_class."
    "\n-- или выберите \"Ещё\" -> \"Сменить класс\"."
)

# Какие преимущества получает указавгих класс пользователь
CL_FEATURES_MESSAGE = ("🌟 Если вы укажете класс, то сможете:"
    "\n\n-- Быстро получать расписание для класса, кнопкой в главном меню."
    "\n-- Не укзаывать ваш класс в текстовых запросах (прим. \"пн\")."
    "\n-- Получать уведомления и рассылку расписания для класса."
    "\n-- Просматривать список изменений для вашего класса."
    "\n-- Использовать счётчик cl/lessons."
    "\n\n💎 Список возможностей может пополняться."
)

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


# Сообщения интерактивного обучения по запросам к расписанию
TUTORIAL_MESSAGES = [
    ("💡 Хотите научиться писать запросы?"
        "\nНа самом деле всё намно-о-ого легче."
        "\nПройдите это простое обучение и убедитесь в этом сами."
        "\n\nВы можете пройти обучение с как самого начала,"
        "так и выбрать интересующую вас страницу."
    ),

    ("1. Будьте проще"
        "\n\nВсё стремится к простоте. Запросы не исключение."
        "\nТак ли нужно указывать все эти \"посторонние\" слова?"
        "\nНет, совсем не обязательно! Они никак не влияют на запрос."
        "\n\n🔶 Вот несколько простых примеров, чтобы понять о чём рень:"
        "\n\n❌ уроки на завтра"
        "\n✅ Завтра"
        "\n\n❌ Расписание для 9в на вторник"
        "\n✅ 9в вторник"
        "\n\nПорядок ключевых слов не имеет значение."
        "\n🌲 матем 8в = 8в матем"
        "\nБыла ли матемитака в 8в или 9в в математике для нас не важно."
    ),

    ("2. Классы"
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
        "\n-- По кнопке \"ещё\" в главном меню."
        "\n-- По команде /info"
    ),

    ("3. Дни недели"
        "\n\nВы можете более явно указать дни недели в запросах и поиске."
        "\nЕсли указаать только день, то получите расписание для вашего класса."
        "\nОднако если вы предпочли не указывать класс по умолчанию,"
        "То получите достаточно интересный результат"
        "\n\n✏️ Как вы можете укзаать дни"
        "\n-- Понедельник - суббота."
        "\n-- пн - сб."
        "\n-- Сегодня, завтра, неделя."
        "\n\n-- вт ➜ Расписание для вашего класса по умолчанию на вторник."
        "\n\nНапоминаем что не обязательно указывать \"посторонние\" слова"
        "\n❌ Уроки для 5г на среду"
        "\n✅ 5г среда"
        "\n\n🔎 В поиске если день не указан, то результат выводится на неделю."
        "\n-- матем вт ➜ Все уроки математики на вторник"
        "\n-- пт 312 ➜ Все уроки в 312 кабинете на пятницу"
    ),

    ("4. Поиск по урокам"
        "\n\n🔎 Укажите точное название урока для его поиска в расписании."
        "\nЕсли не указаны прочие параметры, расписание для всех на неделю."
        "\n\n✏️ Вы можете указать класс, день, кабинет в параметрах."
        "\n\n-- матем ➜ Вся математика за неделю для всех классов."
        "\n-- химия вторник 10а ➜ Более точный поиск."
        "\n\n⚠️ Если ввести несколько уроков, будет взят только первый."
        "\nЧтобы результат поиска не было слишком длинным."
        "\n\n💡 Посмотреть все классы можно в счётчиках:"
        "\n-- По кнопке \"Ещё\" ➜ \"Счётчики\""
        "\n-- По команде /counter"
    ),

    ("5. Поиск по кабинетам"
        "\n🔎 Укажите кабинет, чтобы взглянуть на расписание от его лица."
        "\nЕсли прочие параметры не указаны, расписание для всех на неделю."
        "\n\n✏️ Вы можете указать класс, день, урок в параметрах."
        "\n\n-- 328 ➜ Всё что проходит в 328 кабинете за неделю."
        "\n-- 312 литер вторник 7а ➜ Более точный поиск."
        "\n\n⚠️ Если указать несколько кабинетов, будет взят только первый."
        "\nЧтобы результат поиска не был слишком длинным."
        "\nОднако можно указать несколько предметов в поиске по кабинету."
        "\n\n💡 Посмотреть все кабинеты можно в счётчиках:"
        "\n-- По кнопке \"Ещё\" ➜ \"Счётчики\" ➜ \"По урокам\""
        "\n-- По команде /counter ➜ \"По урокам\""
    ),

    ("6. Групповые чаты"
        "\n\n🌟 Вы можете добавить бота в ваш чатик."
        "\nДля того чтобы использовать бота вместе."
        "\nКласс уставливается один на весь чат."
        "\n\n🌲 Вот некоторые особенности при использовании в чате:"
        "\n\n/set_class [класс] - чтобы установить класс в чате."
        "\nИли ответьте классом на сообщение бота (9в)."
        "\n\n✏️ Чтобы писать запросы в чате, используйте команду /sc [запрос]"
        "\nИли ответьте запросом на сообщение бота."
        "\n\n⚙️ Имейте ввиду что доступ к боту имеют все участники чата."
        "\nЭто также касается и настроек бота."
    ),

    ("🎉 Поздравляем с прохождением обучения!"
        "\nТеперь вы знаете всё о составлении запросов к расписанию."
        "\nПриятного вам использования бота."
        "\nВы умничка. ❤️"
    )
]


# Динамические клавиатуры
# =======================

# Основные клавиатуры ----------------------------------------------------------

def get_other_keyboard(
    cl: Optional[str]=None, home_button: Optional[bool] = True
) -> InlineKeyboardMarkup:
    """Собирает дополнительную клавиатуру.

    Дополнительная клавиатура содержит не часто использумые функции.
    Чтобы эти разделы не занимали место на главном экране и не пугали
    пользователей большим количеством разных кнопочек.

    Buttons:
        set_class => Сменить класс.
        count:lessons:main: => Меню счётчиков бота.
        updates:last:0:{cl}: => Последная страница списка изменений.
        tutorial:0 => первая страница общей справки.
        intents => Раздел настройки намерений пользователя.
        home => Вернуться на главную страницу.

    Args:
        cl (str, Optional): Класс пользователя для клавиатуры.
        home_button (bool, optional): Добавлять ли кнопку возврата.

    Returns:
        InlineKeyboardMarkup: Дополнительная клавиатура.
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

def get_main_keyboard(cl: Optional[str]=None) -> InlineKeyboardMarkup:
    """Возращает главную клавиатуру бота.

    Главная клавиатуры предоставляет доступ к самым часто используемым
    разделам бота, таким как получение расписания для класса по
    умолчанию или настройка оповщеений.
    Если пользвоателй не указал класс - возвращается доплнительная
    клавиатура, но без кнопки возврата домой.

    Buttons:
        other => Вызов дополнительной клавиатуры.
        notify => Меню настройки уведомлений пользователя.
        sc:{cl}:today => Получаени расписания на сегодня для класса.

    Args:
        cl (str, Optional): Класс для подставновки в клавиатуру.

    Returns:
        InlineKeyboardMarkup: Главная домашная клавиатура.
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
                    text=f"📚 Уроки {cl}", callback_data=f"sc:{cl}:today"
                ),
            ]
        ]
    )

# Для расписания уроков --------------------------------------------------------

def get_week_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Возращает клавиатуру, для получение расписания на неделю.

    Используется в сообщении с расписанием уроков.
    Когда режии просмотра выставлен "на сегодня".
    Также содержит кнопки для возврата домой и выбора дня недели.

    Buttons:
        home => Возврат на главный экран.
        sc:{cl}:week => Получить расписание на неедлю для класса.
        select_day:{cl} => Выбрать день недели для расписания.

    Args:
        cl (str, Optional): Класс для подставновки в клавиатуру.

    Return:
        InlineKeyboardMarkup: Клавиатуру для сообщения с расписанием.
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
                )
            ]
        ]
    )

def get_sc_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Возаращает клавиатуру, для получения расписания на сегодня.

    Используется в сообщениях с расписанием уроков.
    Когда режии просмотра выставлен "на неделю".
    Также содержит кнопки для возврата домой и выбора дня недели.

    Buttons:
        home => Возврат в домашний раздел.
        sc:{cl}:today => Получить расписание на сегодня для класса.
        select_day:{cl} => Выбрать день недели для расписания.

    Args:
        cl (str): Класс для подставновки в клавиатуру.

    Return:
        InlineKeyboardMarkup: Клавиатуру для просмотра расписания.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠Домой", callback_data="home"),
                InlineKeyboardButton(
                    text="На сегодня", callback_data=f"sc:{cl}:today"
                ),
                InlineKeyboardButton(text="▷", callback_data=f"select_day:{cl}")
            ]
        ]
    )

def get_select_day_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Возаращает клавиатуру выбора дня недели в рассписания.

    Мспользуется в сообщения с расписанием.
    Позволяет выбрать один из дней недели.
    Автоматически подставляя укзааный класс в запрос.

    Buttons:
        sc:{cl}:{0..6} => Получить расписания для укзаанного дня.
        sc:{cl}:today => Получить расписание на сегодня.
        sc:{cl}:week => получить расписание на неделю.

    Args:
        cl (str): Класс для подставноки в клавиатуру.

    Returns:
        InlineKeyboardMarkup: Клаавиатура для выбра дня расписания.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=x, callback_data=f"sc:{cl}:{i}")
                for i, x in enumerate(days_names)
            ],
            [
                InlineKeyboardButton(text="◁", callback_data="home"),
                InlineKeyboardButton(
                    text="Сегодня", callback_data=f"sc:{cl}:today"
                ),
                InlineKeyboardButton(
                    text="Неделя", callback_data=f"sc:{cl}:week"
                ),
            ],
        ]
    )

# Клавиатуры разделов ----------------------------------------------------------

def get_notify_keyboard(enabled: bool, hours: list[int]
) -> InlineKeyboardMarkup:
    """Возвращет клавиатуру для настройки уведомлений.

    Используется для управления оповещениями.
    Позволяет включить/отключить уведомления.
    Настроить дни для рассылки расписания.
    Сброисить все часы рассылки расписания.

    Buttons:
        notify:on:0 => Включить уведомления бота.
        notify:off:0 => Отключить уведомления бота.
        notify:reset:0 => Сбросить часы для рассылки расписния.
        notify:add:{hour} => Включить рассылку для указанного часа.
        notify:remove:{hour} => Отключить рассылку для указанного часа.

    Args:
        enabled (bool): Включены ли уведомления у пользователя.
        hours (list[int]): В какой час рассылать расписание.

    Returns:
        InlineKeyboardMarkup: Клавиатура для настройки уведомлений.
    """
    inline_keyboard = [[InlineKeyboardButton(text="◁", callback_data="home")]]

    if not enabled:
        inline_keyboard[0].append(InlineKeyboardButton(
                text="🔔 Включить", callback_data="notify:on:0"
            )
        )
    else:
        inline_keyboard[0].append(InlineKeyboardButton(
            text="🔕 Выключить", callback_data="notify:off:0"
            )
        )
        if hours:
            inline_keyboard[0].append(InlineKeyboardButton(
                text="❌ Сброс", callback_data="notify:reset:0"
                )
            )
        hours_line = []
        for i, x in enumerate(range(6, 24)):
            if x % 6 == 0:
                inline_keyboard.append(hours_line)
                hours_line = []

            if x in hours:
                hours_line.append(
                    InlineKeyboardButton(
                        text=f"✔️{x}", callback_data=f"notify:remove:{x}"
                    )
                )
            else:
                hours_line.append(InlineKeyboardButton(
                    text=str(x), callback_data=f"notify:add:{x}"
                    )
                )

        if len(hours_line):
            inline_keyboard.append(hours_line)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_updates_keyboard(
    page: int, updates: list, cl: Optional[str],
    intents: UserIntents, intent_name: str = ""
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для просмотра списка изменений.

    Используется для перемещения по списку изменений в расписании.
    Также может переключать режим просмотре с общего на для класса.
    Использует клавиатуру выбора намерений, для уточнения результатов.

    Buttons:
        home => Возврат к главному меня бота.
        updates:back:{page}:{cl} => Перещается на одну страницу назад.
        updates:switch:0:{cl} => Переключает режим просмотра расписания.
        updates:next:{page}:{cl} => Перемещается на страницу вперёд.
        updates:last:0:{cl} => Перерключиться на последную страницу.

    Args:
        page (int): Номер текущей страницы списка обновлений.
        updates (list): Список всех страниц списка изменений.
        cl (str, optional): Класс для подстановки в клавиатуру.
        intents (UserIntents): Экземпляр намерений пользователя.
        intent_name (str, Optional): Название текущего
            намерения пользователя

    Returns:
        InlineKeyboardMarkup: Клавиатура просмотра списка изменений.
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


_COUNTERS = (
    ("cl", "По классам"),
    ("days", "По дням"),
    ("lessons", "По урокам"),
    ("cabinets", "По кабинетам"),
)

_TARGETS = (
    ("none", "Ничего"),
    ("cl", "Классы"),
    ("days", "Дни"),
    ("lessons", "Уроки"),
    ("cabinets", "Кабинеты"),
    ("main", "Общее"),
)

def get_counter_keyboard(cl: str, counter: str, target: str,
    intents: UserIntents, intent_name: Optional[str]=""
) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру, для просмотра счётчиков расписания.

    Позволяет просматривать счётчики расписания по группам и целям:

    +----------+-------------------------+
    | counter  | targets                 |
    +----------+-------------------------+
    | cl       | days, lessons. cabinets |
    | days     | cl, lessons. cabinets   |
    | lessons  | cl, days, main          |
    | cabinets | cl, days, main          |
    +----------+-------------------------+

    Исользуется клавиатуру для выбрра намерений.
    Чтобы уточнить результаты подсчётов.

    Buttons:
        home => Вернуться к главному сообщению бота.
        count:{counter}:{target} => Переключиться на нужный счётчик.

    Args:
        cl (str): Класс для подстановки в клавиатуру.
        counter (str): Текущая группа счётчиков.
        target (str): Текущий тип просмотра счётчика.
        intents (UserIntents): Экземпляр намерений пользователя.
        intent_name (str, optional): Текущее выбранное намерение.

    Returns:
        InlineKeyboardMarkup: Клавиатура для просмотра счётчиков.
    """
    inline_keyboard = [[
            InlineKeyboardButton(text="◁", callback_data="home")
        ],
        []
    ]

    for k, v in _COUNTERS:
        if counter == k:
            continue

        inline_keyboard[0].append(
            InlineKeyboardButton(
                text=v,
                callback_data=f"count:{k}:{target}:{intent_name}"
            )
        )

    for k, v in _TARGETS:
        if k in (target, counter):
            continue

        if k == "main" and counter not in ("lessons", "cabinets"):
            continue

        if counter in ("lessons", "cabinets") and k in ("lessons", "cabinets"):
            continue

        if counter == "cl" and k == "lessons" and not cl:
            continue

        inline_keyboard[1].append(
            InlineKeyboardButton(
                text=v,
                callback_data=f"count:{counter}:{k}:{intent_name}"
            )
        )

    # Добавляем клавиатуру выбора намерений
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

def get_tutorial_keyboard(page: int) -> InlineKeyboardMarkup:
    """Клавиатура многостраничного обучения.

    Используется для перемещения между страницами обучения.
    Содержит кнопку для запуска и закрытия справки.
    Кнопки перемещения на следующую и предыдущую страницы.
    Содержание для быстрого переключения страниц.

    Buttons:
        delete_msg => Удалить сообщение.
        tutorual:{page} => Сменить страницу справки.

    Args:
        page (int): Текущая страница справки.

    Returns:
        InlineKeyboardMarkup: Клавиатура для перемещения по справке.
    """
    inline_keyboard = []

    # Если это первая страница -> без кнопки назад
    if page == 0:
        inline_keyboard.append([
            InlineKeyboardButton(text="🚀 Начать", callback_data="tutorial:1")
        ])

    # Кнопкеи для управления просмотром
    elif page != len(TUTORIAL_MESSAGES)-1:
        inline_keyboard.append([
            InlineKeyboardButton(text="◁", callback_data=f"tutorial:{page-1}"),
            InlineKeyboardButton(
                text="🌟 Дальше", callback_data=f"tutorial:{page+1}"
            )
        ])

        # Крпткое содержание для быстрого перемещения
        for i, x in enumerate(TUTORIAL_MESSAGES[1:-1]):
            if i+1 == page:
                continue
            inline_keyboard.append([InlineKeyboardButton(
                text=x.splitlines()[0], callback_data=f"tutorial:{i+1}")]
            )

        inline_keyboard.append([InlineKeyboardButton(
            text="❌ Закрыть", callback_data="delete_msg")]
        )

    # Завершение обучения
    else:
        inline_keyboard.append([
            InlineKeyboardButton(
                text="🎉 Завершить", callback_data="delete_msg"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

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


# Динамический сообщения
# ======================

def get_intent_status(i: Intent) -> str:
    """Отображает краткую информацию о содержимом намерения.

    Формат: < {классы} / {дни} / {уроки} / {кабинеты} >

    Args:
        i (Intent): Намерение для отображения статуса

    Returns:
        str: Краткое описание намерения.
    """
    message = "<"

    for group in (i.cl, i.days, i.lessons, i.cabinets):
        for x in group:
            message += f" {x}"
        message += " /"
    message += " >"

    return message

def get_update_timetag(path: Path) -> int:
    """Получает время последней удачной проверки обнолвений.

    Вспомогательная функция.
    Время успешой проверки используется для контроля скрипта обновлений.
    Если время последней проверки будет дольше одного часа,
    то это повод задуматься о правильноти работы скрипта.

    Args:
        path (Path): Путь к файлу временной метки обновлений.

    Returns:
        int: UNIXtime последней удачной проверки обновлений.
    """
    try:
        with open(path) as f:
            return int(f.read())
    except (ValueError, FileNotFoundError):
        return 0

def get_status_message(sp: SPMessages, timetag_path: Path) -> str:
    """Отправляет информационно сособщение о работа бота и парсера.

    Инфомарционно сообщения содержит некоторую вспомогательную
    информацию относительно статуса и работаспособности бота.
    К примеру версия бота, время последнего обновления,
    классов и прочее.
    Также осдержит метку последнего автоматического обновления.
    Если давно не было автообновлений - выводит предупреждение.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.
        timetag_path (Path): Путь к файлу временной метки обновления.

    Returns:
        str: Информацинное сообщение.
    """
    message = sp.send_status()
    message += f"\n⚙️ Версия бота: {_BOT_VERSION}\n🛠️ Тестер @micronuri"

    timetag = get_update_timetag(timetag_path)
    timedelta = int(datetime.now().timestamp()) - timetag
    message += f"\n📀 Проверка была {get_str_timedelta(timedelta)} назад"

    if timedelta > _ALERT_AUTOUPDATE_AFTER_SECONDS:
        message += ("\n⚠️ Автоматическая проверка была более часа назад."
            "\nПожалуйста свяжитесь с администратором бота."
        )

    return message


def get_home_message(cl: str) -> str:
    """Отпраляет главное сообщение бота.

    Главное сообщение будет сопровождать пользователя всегда.
    Оно содержит краткую необходимую информацию.

    В шапке сообщения указывается ваш класс по умолчанию.
    В теле сообщения содержится краткая справка по использованию бота.
    Если вы не привязаны к классу, справка немного отличается.

    Args:
        cl (str): Для какого класса получить сообщение.

    Returns:
        str: Готовое главное сообщение бота.
    """
    if cl:
        message = f"💎 Ваш класс {cl}"
    else:
        message = "🌟 Вы не привязаны к классу."

    message += f"\n\n{HOME_MESSAGE}"
    return message

def get_notify_message(enabled: bool, hours: list[int]) -> str:
    """Отправляет сообщение с информацией о статусе уведомлений.

    Сообщение о статусе уведомлений содержит в себе:
    Включены ли сейчас уведомления.
    Краткая инфомрация об уведомленях.
    В какие часы рассылается расписание уроков.

    Args:
        enabled (bool): Включены ли уведомления пользователя.
        hours (list[int]): В какие часы отправлять уведомления.

    Returns:
        str: Сообщение с информацией об уведомлениях.
    """
    if enabled:
        message = ("🔔 уведомления включены."
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

def get_counter_message(
    sc: Schedule, counter: str, target: str, intent: Optional[Intent]=None
) -> str:
    """Собирает сообщение с результатами работы счётчиков.

    В зависимости от выбранного счётчика использует соответствующую
    функцию счётчика.

    +----------+-------------------------+
    | counter  | targets                 |
    +----------+-------------------------+
    | cl       | days, lessons. cabinets |
    | days     | cl, lessons. cabinets   |
    | lessons  | cl, days. main          |
    | cabinets | cl, days. main          |
    +----------+-------------------------+

    Args:
        sc (Schedule): Экземпляр расписания уроков.
        counter (str): Тип счётчика.
        target (str): Группа просмтора счётчика.
        intent (Intent): Намерение для уточнения результатов счётчика.

    Returns:
        str: Сообщение с результаатми счётчика.
    """
    message = f"✨ Счётчик {counter}/{target}:"
    if intent is not None:
        message += f"\n⚙️ {get_intent_status(intent)}"
    else:
        intent = Intent()

    if counter == "cl":
        if target == "lessons":
            intent = intent.reconstruct(sc, cl=sc.cl)
        res = cl_counter(sc, intent)
    elif counter == "days":
        res = days_counter(sc, intent)
    elif counter == "lessons":
        res = index_counter(sc, intent)
    else:
        res = index_counter(sc, intent, cabinets_mode=True)

    if target == "none":
        target = None

    message += send_counter(group_counter_res(res), target=target)
    return message

def get_updates_message(
    update: Optional[list]=None, cl: Optional[str]=None,
    intent: Optional[Intent]=None
) -> str:
    """Собирает сообщение со страницей списка изменений расписания.

    Args:
        update (list, Optional): Странциа списка изменений расписания.
        cl (str, Optional): Для какого класса представлены изменения.
        intent (Intent, Optional): Намерение для уточнения результата.

    Returns:
        str: Сообщение со страницей списка изменений.
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



# Обработчики команд
# ==================

# Простая отправка сообщений -------------------------------------------

@dp.message(Command("cl_features"))
async def restrictions_handler(message: Message) -> None:
    """Отправляет список примуществ при указанном классе."""
    await message.answer(text=CL_FEATURES_MESSAGE)

@dp.message(Command("tutorial"))
async def tutorial_handler(message: Message) -> None:
    """Отправляет интерактивное обучение по составлению запросов."""
    await message.delete()
    await message.answer(
        text=TUTORIAL_MESSAGES[0],
        reply_markup=get_tutorial_keyboard(0)
    )

@dp.message(Command("info"))
async def info_handler(message: Message, sp: SPMessages) -> None:
    """Сообщение о статусе рабты бота и парсера."""
    await message.answer(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(sp.user["class_let"]),
    )

# Help команда ---------------------------------------------------------

@dp.message(Command("help", "start"))
async def start_handler(message: Message, sp: SPMessages) -> None:
    """Отправляет сообщение справки и главную клавиатуру.

    Если класс не указан, отпраляет сообщение указания класса.
    """
    await message.delete()
    if sp.user["set_class"]:
        await message.answer(
            text=get_home_message(sp.user["class_let"]),
            reply_markup=get_main_keyboard(sp.user["class_let"]),
        )
    else:
        await message.answer(SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP)

# Изменение класса пользователя ----------------------------------------

@dp.message(Command("set_class"))
async def set_class_command(message: Message, sp: SPMessages,
    command: CommandObject
) -> None:
    """Изменяет класс или удаляет данные о пользователе."""
    if command.args is not None:
        if sp.set_class(command.args):
            await message.answer(
                text=get_home_message(command.args),
                reply_markup=get_main_keyboard(command.args)
        )
        else:
            text = "👀 Такого класса не существует."
            text += f"\n💡 Доступныe классы: {', '.join(sp.sc.lessons)}"
            await message.answer(text=text)

    else:
        sp.reset_user()
        await message.answer(
            text=SET_CLASS_MESSAGE,
            reply_markup=PASS_SET_CL_MARKUP
        )

@dp.message(Command("pass"))
async def pass_handler(message: Message, sp: SPMessages) -> None:
    """Отвязывает пользователя от класса по умолчанию."""
    sp.set_class(None)
    await message.answer(
        text=get_home_message(sp.user["class_let"]),
        reply_markup=get_main_keyboard(sp.user["class_let"]),
    )

# Переход к разделам бота ----------------------------------------------

@dp.message(Command("updates"))
async def updates_handler(message: Message, sp: SPMessages,
    intents: UserIntents
) -> None:
    """Оправляет последную страницу списка изменений в расписании."""
    updates = sp.sc.updates
    await message.answer(
        text=get_updates_message(updates[-1] if len(updates) else None),
        reply_markup=get_updates_keyboard(max(len(updates) - 1, 0),
            updates, None, intents
        )
    )

@dp.message(Command("counter"))
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

@dp.message(Command("notify"))
async def notify_handler(message: Message, sp: SPMessages):
    """Переводит в менюя настройки уведомлений."""
    enabled = sp.user["notifications"]
    hours = sp.user["hours"]
    await message.answer(
        text=get_notify_message(enabled, hours),
        reply_markup=get_notify_keyboard(enabled, hours),
    )


# Обработка намерений
# ===================

@dp.message(Command("cancel"))
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

@dp.message(Command("intents"))
async def manage_intents_handler(message: Message,
    intents: UserIntents
) -> None:
    """Команда для просмотра списка намерений пользователя."""
    await message.answer(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )

@dp.callback_query(F.data=="intents")
async def intents_callback(query: CallbackQuery, intents: UserIntents) -> None:
    """Кнопка для просмотра списка намерений пользователя."""
    await query.message.edit_text(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )

# Добавление нового намерения --------------------------------------------------

@dp.callback_query(IntentCallback.filter(F.action=="add"))
async def add_intent_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Начать добавление нового намерения по кнопке."""
    await state.set_state(EditIntentStates.name)
    await query.message.edit_text(SET_INTENT_NAME_MESSAGE)

@dp.message(Command("add_intent"))
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

@dp.message(EditIntentStates.name)
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

@dp.message(EditIntentStates.parse)
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

@dp.callback_query(IntentCallback.filter(F.action=="show"))
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

@dp.callback_query(IntentCallback.filter(F.action=="remove"))
async def remove_intent_callback(
    query: CallbackQuery, intents: UserIntents, callback_data: IntentCallback
) -> None:
    """Удаляет намерение по имени."""
    intents.remove(callback_data.name)
    await query.message.edit_text(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )

@dp.callback_query(IntentCallback.filter(F.action=="reparse"))
async def reparse_intent_callback(
    query: CallbackQuery, intents: UserIntents, callback_data: IntentCallback,
    state: FSMContext
) -> None:
    """Изменение параметров намерения."""
    await state.set_state(EditIntentStates.parse)
    await state.update_data(name=callback_data.name)
    await query.message.edit_text(text=PARSE_INTENT_MESSAGE)


# Режим удаления намерений -----------------------------------------------------

@dp.message(Command("remove_intents"))
async def intents_remove_mode_handler(
    message: Message, intents: UserIntents
) -> None:
    """Переключает в режим удаления намерений."""
    await message.answer(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=get_remove_intents_keyboard(intents.get())
    )

@dp.callback_query(F.data=="intents:remove_mode")
async def intents_remove_mode_callback(
    query: CallbackQuery, intents: UserIntents
) -> None:
    """Переключает в режми удаления намерений."""
    await query.message.edit_text(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=get_remove_intents_keyboard(intents.get())
    )

@dp.callback_query(IntentCallback.filter(F.action=="remove_many"))
async def remove_many_intent_callback(
    query: CallbackQuery, intents: UserIntents, callback_data: IntentCallback
) -> None:
    """Удаляет намерение и возвращает в меню удаления."""
    intents.remove(callback_data.name)
    await query.message.edit_text(
        text=INTENTS_REMOVE_MANY_MESSAGE,
        reply_markup=get_remove_intents_keyboard(intents.get())
    )

@dp.callback_query(F.data=="intents:remove_all")
async def intents_set_remove_mode_callback(
    query: CallbackQuery, intents: UserIntents
) -> None:
    """Удаляет всен амерения пользвоателя."""
    intents.remove_all()
    await query.message.edit_text(
        text=get_intents_message(intents.get()),
        reply_markup=get_intents_keyboard(intents.get())
    )


# Обработчик текстовых запросов
# =============================

def process_request(sp: SPMessages, request_text: str) -> Optional[str]:
    """Обрабатывает текстовый запрос к расписанию.

    Преобразует входящий текст в набор намерений или запрос.
    Производит поиск по урокам/кабинетам
    или получает расписание, в зависимости от намерений.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.
        request_text (str): Текст запроса к расписанию.

    Returns:
        str: Ответ от генератора сообщений.
    """
    intent = Intent.parse(sp.sc, request_text.split())

    # Чтобы не превращать бота в машину для спама
    # Будет использоваться последний урок/кабинет из фильтра
    if len(intent.cabinets):
        res = sp.sc.search(list(intent.cabinets)[-1], intent, True)
        text = send_search_res(intent, res)

    elif len(intent.lessons):
        res = sp.sc.search(list(intent.lessons)[-1], intent, False)
        text = send_search_res(intent, res)

    elif intent.cl or intent.days:
        if intent.days:
            text = sp.send_lessons(intent)
        else:
            text =sp.send_today_lessons(intent)
    else:
        text = None

    return text

# Получить расписание уроков -------------------------------------------

@dp.message(Command("sc"))
async def sc_handler(
    message: Message, sp: SPMessages, command: CommandObject
) -> None:
    """Отправляет расписание уроков пользовтелю.

    Отправляет предупреждение, если у пользователя не укзаан класс.
    """
    if command.args is not None:
        answer = process_request(sp, command.args)
        if answer is not None:
            await message.answer(text=answer)
        else:
            await message.answer(text="👀 Кажется это пустой запрос...")

    elif sp.user["class_let"]:
        await message.answer(
            text=sp.send_today_lessons(Intent()),
            reply_markup=get_week_keyboard(sp.user["class_let"]),
        )
    else:
        await message.answer(
            text="⚠️ Для быстрого получения расписания вам нужно указать класс."
        )

@dp.message()
async def main_handler(message: Message, sp: SPMessages) -> None:
    """Главный обработчик сообщений бота.

    Перенаправляет входящий текст в запросы к расписанию.
    Устанавливает класс, если он не установлен.
    В личных подсказках отправляет подсказку о доступных классах.
    """
    if message.text is None:
        return

    text = message.text.strip().lower()

    # Если у пользователя установлек класс -> создаём запрос
    if sp.user["set_class"]:
        answer = process_request(sp, text)

        if answer is not None:
            await message.answer(text=answer)
        elif message.chat.type == "private":
            await message.answer(text="👀 Кажется это пустой запрос...")

    elif text in sp.sc.lessons:
        logger.info("Set class {}", text)
        sp.set_class(text)
        await message.answer(
            text=get_home_message(sp.user["class_let"]),
            reply_markup=get_main_keyboard(sp.user["class_let"])
        )

    elif message.chat.type == "private":
        text = "👀 Такого класса не существует."
        text += f"\n💡 Доступныe классы: {', '.join(sp.sc.lessons)}"
        await message.answer(text=text)


# Обработчик Callback запросов
# ============================

@dp.callback_query(F.data == "delete_msg")
async def delete_msg_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Удаляет сообщение.

    Если не удалось удалить, отправляет гланый раздел.
    """
    try:
        await query.message.delete()
    except TelegramBadRequest:
        await query.message.edit_text(
            text=get_home_message(sp.user["class_let"]),
            reply_markup=get_main_keyboard(sp.user["class_let"])
    )

@dp.callback_query(F.data == "home")
async def home_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Возаращает в главный раздел."""
    await query.message.edit_text(
        text=get_home_message(sp.user["class_let"]),
        reply_markup=get_main_keyboard(sp.user["class_let"])
    )

@dp.callback_query(F.data == "other")
async def other_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Возвращает сообщение статуса и доплнительную клавиатуру."""
    await query.message.edit_text(
        text=get_status_message(sp, _TIMETAG_PATH),
        reply_markup=get_other_keyboard(sp.user["class_let"]),
    )

@dp.callback_query(F.data == "cl_features")
async def restrictions_callback(query: CallbackQuery) -> None:
    """Возвращает сообщение с преимуществами указанного класса."""
    await query.message.edit_text(
        text=CL_FEATURES_MESSAGE, reply_markup=BACK_SET_CL_MARKUP
    )

@dp.callback_query(F.data == "set_class")
async def set_class_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Сбрасывает класс пользователя."""
    sp.reset_user()
    await query.message.edit_text(
        text=SET_CLASS_MESSAGE, reply_markup=PASS_SET_CL_MARKUP
    )

@dp.callback_query(F.data == "pass")
async def pass_class_callback(query: CallbackData, sp: SPMessages) -> None:
    """Отвязывает пользователя от класса."""
    sp.set_class(None)
    await query.message.edit_text(
        text=get_home_message(sp.user["class_let"]),
        reply_markup=get_main_keyboard(sp.user["class_let"])
    )


class ScCallback(CallbackData, prefix="sc"):
    """Используется при получении расписания.

    cl (str): Класс для которого получить расписание.
    day (str): Для какого дня получить расписание.

    - 0-5: понедельник - суббота.
    - today: Получить расписание на сегодня/завтра.
    - week: Получить расписание на всю неделю.
    """

    cl: str
    day: str

@dp.callback_query(ScCallback.filter())
async def sc_callback(
    query: CallbackQuery, callback_data: ScCallback, sp: SPMessages
) -> None:
    """Отпарвляет расписание уроков для класса в указанный день."""
    # Расписание на неделю
    if callback_data.day == "week":
        text = sp.send_lessons(
            Intent.construct(
                sp.sc, days=[0, 1, 2, 3, 4, 5], cl=callback_data.cl
            )
        )
        reply_markup = get_sc_keyboard(callback_data.cl)

    # Расипсание на сегодня/завтра
    elif callback_data.day == "today":
        text = sp.send_today_lessons(
            Intent.construct(sp.sc,
            cl=callback_data.cl)
        )
        reply_markup = get_week_keyboard(callback_data.cl)

    # Расписание на другой день недели
    else:
        text = sp.send_lessons(
            Intent.construct(
                sp.sc, cl=callback_data.cl, days=int(callback_data.day)
            )
        )
        reply_markup = get_week_keyboard(callback_data.cl)

    await query.message.edit_text(text=text, reply_markup=reply_markup)


class SelectDayCallback(CallbackData, prefix="select_day"):
    """Используется для выбора дня недели при получении расписания.

    cl (str): Для какого класса получить расписание.
    """

    cl: str

@dp.callback_query(SelectDayCallback.filter())
async def select_day_callback(
    query: CallbackQuery, callback_data: ScCallback, sp: SPMessages
) -> None:
    """Отобржает клавиатуру для выбора дня расписания уроков."""
    await query.message.edit_text(
        text=f"📅 на ...\n🔶 Для {callback_data.cl}:",
        reply_markup=get_select_day_keyboard(callback_data.cl),
    )


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

@dp.callback_query(F.data == "notify")
async def notify_callback(query: CallbackQuery, sp: SPMessages) -> None:
    """Отправляет настройки увдеомлений."""
    enabled = sp.user["notifications"]
    hours = sp.user["hours"]
    await query.message.edit_text(
        text=get_notify_message(enabled, hours),
        reply_markup=get_notify_keyboard(enabled, hours),
    )

@dp.callback_query(NotifyCallback.filter())
async def notify_mod_callback(
    query: CallbackQuery, sp: SPMessages, callback_data: NotifyCallback
) -> None:
    """Применяет настройки к уведомлениям."""
    if callback_data.action == "on":
        sp.user["notifications"] = True

    elif callback_data.action == "off":
        sp.user["notifications"] = False

    elif callback_data.action == "add":
        if int(callback_data.hour) not in sp.user["hours"]:
            sp.user["hours"].append(int(callback_data.hour))

    elif callback_data.action == "remove":
        if int(callback_data.hour) in sp.user["hours"]:
            sp.user["hours"].remove(int(callback_data.hour))

    elif callback_data.action == "reset":
        sp.user["hours"] = []

    sp.save_user()
    enabled = sp.user["notifications"]
    hours = sp.user["hours"]

    await query.message.edit_text(
        text=get_notify_message(enabled, hours),
        reply_markup=get_notify_keyboard(enabled, hours),
    )


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

@dp.callback_query(UpdatesCallback.filter())
async def updates_callback(
    query: CallbackQuery, sp: SPMessages, callback_data: UpdatesCallback,
    intents: UserIntents
) -> None:
    """Клавиатура просмотра списка изменений."""
    # Смена режима просмотра: только для класса/всего расписния
    if callback_data.action == "switch":
        cl = sp.user["class_let"] if callback_data.cl == "None" else None
    else:
        cl = None if callback_data.cl == "None" else callback_data.cl

    intent = intents.get_intent(callback_data.intent)

    if cl is not None and sp.user["class_let"]:
        intent = Intent.construct(sp.sc, cl)

    if intent is None:
        updates = sp.sc.updates
    else:
        updates = sp.sc.get_updates(intent)
    i = max(min(int(callback_data.page), len(updates) - 1), 0)

    if len(updates):
        if callback_data.action in ("last", "switch"):
            i = len(updates) - 1

        elif callback_data.action == "next":
            i = (i + 1) % len(updates)

        elif callback_data.action == "back":
            i = (i - 1) % len(updates)

        update = updates[i]
    else:
        update = None

    await query.message.edit_text(
        text=get_updates_message(update, cl, intent),
        reply_markup=get_updates_keyboard(
            i, updates, cl, intents, callback_data.intent
        )
    )


class CounterCallback(CallbackData, prefix="count"):
    """Используется в клавиатуре просмотра счётчиков расписания.

    counter (str): Тип счётчика.
    target (str): Цль для отображения счётчика.
    intent (str): Имя пользовательского намерения.

    +----------+-------------------------+
    | counter  | targets                 |
    +----------+-------------------------+
    | cl       | days, lessons. cabinets |
    | days     | cl, lessons. cabinets   |
    | lessons  | cl, days, main          |
    | cabinets | cl, days, main          |
    +----------+-------------------------+
    """

    counter: str
    target: str
    intent: str

@dp.callback_query(CounterCallback.filter())
async def counter_callback(
    query: CallbackQuery, sp: SPMessages, callback_data: NotifyCallback,
    intents: UserIntents
) -> None:
    """Клавитура для просмотра счётчиков расписания."""
    counter = callback_data.counter
    target = callback_data.target

    if counter == target:
        target = None

    if counter == "cl" and target == "lessons" and not sp.user["class_let"]:
        target = None

    intent = intents.get_intent(callback_data.intent)

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


class TutorlailCallback(CallbackData, prefix="tutorial"):
    """Используется при просмотре постраничной справки.

    page (int): Текущая страница справки.
    """

    page: int

@dp.callback_query(TutorlailCallback.filter())
async def tutorail_callback(query: CallbackQuery,
    callback_data: TutorlailCallback) -> None:
    """Отправляет страницу интерактивного обучения."""
    await query.message.edit_text(
        text=TUTORIAL_MESSAGES[callback_data.page],
        reply_markup=get_tutorial_keyboard(callback_data.page)
    )


@dp.callback_query()
async def callback_handler(query: CallbackQuery) -> None:
    """Перехватывает все прочие callback_data."""
    logger.warning("Unprocessed query - {}", query.data)


def send_error_messsage(exception: ErrorEvent, sp: SPMessages):
    """Отпрвляет отладочное сообщние об ошибке пользователю.

    Data:
        user_name => Кто вызвал ошибку.
        user_id => Какой пользователь вызвал ошибку.
        class_let => К какому класс относился пользователь.
        chat_id => Где была вызвана ошибка.
        exception => Описание текста ошибки.
        action => Callback data или текст сообщение, вызвавший ошибку.

    Args:
        exception (ErrorEvent): Событие ошибки aiogram.
        sp (SPMessage): Экземпляр генератора сообщений пользователя.

    Returns:
        str: Отладочное сообщение с данными об ошибке в боте.
    """
    if exception.update.callback_query is not None:
        action = f"-- Данные: {exception.update.callback_query.data}"
        message = exception.update.callback_query.message
    else:
        action = f"-- Текст: {exception.update.message.text}"
        message = exception.update.message

    user_name = message.from_user.first_name
    chat_id = message.chat.id

    return ("⚠️ Произошла ошибка в работе бота."
        f"\n-- Версия: {_BOT_VERSION}"
        "\n\n👤 Пользователь"
        f"\n-- Имя: {user_name}"
        f"\n-- Класс: {sp.user['class_let']}"
        f"\n-- ID: {chat_id}"
        "\n\n🚫 Описание ошибки:"
        f"\n-- {exception.exception}"
        "\n\n🔍 Доплнительная информаиция"
        f"\n{action}"
        "\n\nПожалуйста, свяжитесь с @milinuri для решения проблемы."
    )

@dp.errors()
async def error_handler(exception: ErrorEvent, sp: SPMessages) -> None:
    """Ловит и обрабатывает все исключения.

    Отправляет сообщение об ошибке пользователям.
    """
    logger.exception(exception.exception)
    if exception.update.callback_query is not None:
        await exception.update.callback_query.message.answer(
            send_error_messsage(exception, sp)
        )
    else:
        await exception.update.message.answer(
            send_error_messsage(exception, sp)
        )


# Запуск бота
# ===========

async def main() -> None:
    """Главная функция запуска бота."""
    bot = Bot(TELEGRAM_TOKEN)
    logger.info("Bot started.")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
