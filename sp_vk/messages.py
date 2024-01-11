"""
Cообщения, используемые в боте.

Author: Milinuri Nirvalen
"""

from sp.messages import send_counter
from sp.messages import SPMessages
from sp.parser import Schedule
from sp.intents import Intent

# Счётчики расписания
from sp.counters import cl_counter
from sp.counters import days_counter
from sp.counters import group_counter_res
from sp.counters import index_counter



HOME = """💡 Некоторые примеры запросов:
-- 7в 6а на завтра
-- уроки 6а на вторник ср
-- расписание на завтра для 8б
-- 312 на вторник пятницу
-- химия 228 6а вторник

🏫 В запросах вы можете использовать:
Урок/Кабинет: Получить все его упоминания.

Классы: для которых нужно расписание.
-- Если класс не укзаан, подставляется ваш класс.
-- "?": для явной подставновки вашего класса.

Дни недели:
-- Если день не указан - на сегодня/завтра.
-- Понедельник-суббота (пн-сб).
-- Сегодня, завтра, неделя.

🌟 Порядок и форма аргументов не важны, балуйтесь!"""

NO_CLASS_HOME = """💡 Некоторые примеры запросов:
-- 7в 6а на завтра
-- уроки 6а на вторник ср
-- расписание на завтра для 8б
-- 312 на вторник пятницу
-- химия 228 6а вторник

🏫 В запросах вы можете использовать:
Урок/Кабинет: Получить все его упоминания.
Классы: для которых нужно расписание.

Дни недели:
-- Если день не указан - на сегодня/завтра.
-- Понедельник-суббота (пн-сб).
-- Сегодня, завтра, неделя.

🌟 Порядок и форма аргументов не важны, балуйтесь!"""


INFO = """
🌲 Тестер @errorgirl2007
🌲 Версия бота: 1.2 (14)"""


SET_CLASS = """
Для полноценной работы желательно указать ваш класс.
Для быстрого просмотра расписания и списка изменений.

🌟 Вы можете пропустить выбор класса кнопкой "пропустить" (команда /pass).
Но это накладывает некоторые ограничения.
Прочитать об ограничениях можно по кнопек ограничения (команда /restrictions).

Способы указать класс:
-- (В переписке с ботом) Следуюшим сообщением введите ваш класс ("1а").
-- /set_class в ответ на сообщение с классом ("7а").
-- /set_class [класс] - с явным указание класса.

💡 Вы можете сменить класс в дальнейшем:
-- Через команду /set_class.
-- Через кнопку Cменить класс."""


RESTRICTIONS = """Всё перечисленное будет недоступно:

-- Быстрое получение расписания для класса.
-- Подстановка класса в текстовых запросах.
-- Просмотр списка изменений для класса.
-- Счётчик "по классам/уроки".
-- Система уведомлений.

🌟 На этом все отличия заканчиваются."""


def send_home_message(sp: SPMessages) -> str:
    """Отпавляет сообщение со справкой об использовании бота.

    Args:
        sp (SPMessages): Генератор сообщений

    Returns:
        str: Готовое сообщение
    """

    if sp.user["class_let"]:
        return HOME
    else:
        return NO_CLASS_HOME

def send_notifications_info(sp: SPMessages) -> str:
    """Отправляет сообщение с информацией об уведомлениях.

    Args:
        sp (SPMessages): Генератор сообщений

    Returns:
        str: Сообщение с информацией об уведомлениях.
    """

    message = "Вы получите уведомление, если расписание изменится.\n"

    if sp.user["notifications"]:
        message += "\n🔔 уведомления включены."
        message += "\n\nТакже вы можете настроить отправку расписания."
        message += "\nВ указанное время бот отправит расписание вашего класса."
        hours = sp.user["hours"]

        if hours:
            message += "\n\nРасписани будет отправлено в: "
            message += ", ".join(map(str, set(hours)))
    else:
        message += "\n🔕 уведомления отключены."

    return message

def send_counter_message(sc: Schedule, counter: str, target: str) -> str:
    """Собирает сообщение с результатами работы счётчиков.

    Args:
        sc (Schedule): Расписание уроков
        counter (str): Тип счётчика
        target (str): Режим просмотра счётчика

    Returns:
        str: Готовое сообщение
    """

    intent = Intent()

    if counter == "cl":
        if target == "lessons":
            intent = Intent.construct(sc, cl=[sc.cl])
        res = cl_counter(sc, intent)
    elif counter == "days":
        res = days_counter(sc, intent)
    elif counter == "lessons":
        res = index_counter(sc, intent)
    else:
        res = index_counter(sc, intent, cabinets_mode=True)

    groups = group_counter_res(res)
    message = f"✨ Счётчик {counter}/{target}:"
    message += send_counter(groups, target=target)
    return message
