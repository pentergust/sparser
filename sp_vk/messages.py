"""
Cообщения, используемые в боте.

Author: Milinuri Nirvalen
"""

from typing import Optional

from sp.messages import send_update
from sp.messages import send_counter
from sp.messages import SPMessages
from sp.parser import Schedule
from sp.intents import Intent

# Счётчики расписания
from sp.counters import cl_counter
from sp.counters import days_counter
from sp.counters import group_counter_res
from sp.counters import index_counter


# Главнео сообщение справки бота
HOME = ("💡 Некоторые примеры запросов:"
    "\n-- 7в 6а на завтра"
    "\n-- уроки 6а на вторник ср"
    "\n-- 312 на вторник пятницу"
    "\n-- химия 228 6а вторник"
    "\n\n🏫 В запросах вы можете использовать:"
    "\n* Урок/Кабинет: Получить все его упоминания."
    "\n* Классы: для которого нужно расписание."
    "\n* Дни недели:"
    "\n-- Если день не указан - на сегодня/завтра."
    "\n-- Понедельник-суббота (пн-сб)."
    "\n-- Сегодня, завтра, неделя."
    # "\n\n🌟 Как писать запросы? /tutorial"
)


INFO = (
    "🌲 Тестер @errorgirl2007"
    "\n🌲 Версия бота: 1.2 (17"
)

# Сообщение при смене класса
SET_CLASS = ("Для полноценной работы желательно указать ваш класс."
    "\nВы сможете быстро просматривать расписание и получать уведомления."
    "\nПочитать о всех преимуществах - /cl_features"
    "\n\n🌟 Просто укажите класс следующим сообщеним (\"8в\")"
    "\nИли после команды /set_class (прим. /set_class 7в)"
    "\n\nВы можете пропустить выбор класса нажав кнопку (/pass)."
    "\n\n💡 Вы можете сменить класс позже:"
    "\n-- через команду /set_class [класс]."
    "\n-- Кпонку Cменить класс."
)

# Какие преимущества получает указавгих класс пользователь
CL_FEATURES = ("🌟 Если вы укажете класс, то сможете:"
    "\n\n-- Быстро получать расписание для класса, кнопкой в главном меню."
    "\n-- Не укзаывать ваш класс в текстовых запросах (прим. \"пн\")."
    "\n-- Получать уведомления и рассылку расписание для класса."
    "\n-- Просматривать список изменений для вашего класса."
    "\n-- Использовать счётчик cl/lessons."
    "\n\n💎 Список возможностей может пополняться."
)


def send_notify_info(enabled: bool, hours: list[int]) -> str:
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


def send_counter_message(sc: Schedule, counter: str, target: str) -> str:
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

    Returns:
        str: Сообщение с результаатми счётчика.
    """
    message = f"✨ Счётчик {counter}/{target}:"
    intent = Intent()

    if counter == "cl":
        if target == "lessons":
            intent = intent.construct(sc, cl=sc.cl)
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

def send_updates(
    update: Optional[list]=None, cl: Optional[str]=None,
) -> str:
    """Собирает сообщение со страницей списка изменений расписания.

    Args:
        update (list, Optional): Странциа списка изменений расписания.
        cl (str, Optional): Для какого класса представлены изменения.

    Returns:
        str: Сообщение со страницей списка изменений.
    """
    message = "🔔 Изменения "
    message += " в расписании:\n" if cl is None else f" для {cl}:\n"

    if update is not None:
        update_text = send_update(update, cl=cl)

        if len(update_text) > 4000:
            message += "\n📚 Слишком много изменений."
        else:
            message += update_text
    else:
        message += "✨ Нет новых обновлений."

    return message
