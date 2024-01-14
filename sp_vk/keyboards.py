"""
Определение клавиатур бота.

Author: Milinuri Nirvalen
"""

from sp.messages import SPMessages

from typing import Optional

from vkbottle import Keyboard, KeyboardButtonColor, Text, Callback


# Для возвращение домой
TO_HOME = (
    Keyboard()
    .add(Callback("🏠 Домой", payload={"cmd": "home"}))
    .get_json()
)

# Для меню выбора кдасса
SET_CLASS = (
    Keyboard()
    .add(Text("Ограничения", payload={"cmd": "cl_features"}))
    .add(Text("Пропустить",
        payload={"cmd": "pass"}), color=KeyboardButtonColor.NEGATIVE
    )
    .get_json()
)


# Основная клавиатура
def get_home_keyboard(sp: SPMessages) -> dict:
    """Получает основную клавиатуру бота.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.

    Returns:
        dict: JSON клавиатура.
    """
    cl = sp.user["class_let"]
    kb = Keyboard()
    kb.add(Text("🏠 Справка", payload={"cmd": "home"}))

    if cl is not None:
        kb.add(Text("📚 на неделю", payload={"cmd": "week"}))
        kb.add(Text(f"📚 Уроки {cl}", payload={"cmd": "sc"}),
            color=KeyboardButtonColor.PRIMARY
        )
        kb.row()
        kb.add(Text("🔔 Уведомления", payload={"notify": "info"}))

    kb.add(Text("📊 Счётчики", payload={"cmd": "counter"}))
    kb.add(Text("📜 Изменения", payload={"group":"updates", "action": "last"}))

    kb.row()
    kb.add(Text("⚙️ Сменить класс", payload={"cmd": "set_class"}))
    kb.add(Text("🌲 Инфо", payload={"cmd": "info"}))

    return kb.get_json()

def get_main_keyboard(sp: SPMessages) -> dict:
    """Возрвщает главную клавиатуру бота.
    Если класс не установлен, возвращает клавиатуру смены класса.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений.

    Returns:
        dict: JSON клавиатура.
    """
    return get_home_keyboard(sp) if sp.user["set_class"] else SET_CLASS


def get_notify_keyboad(sp: SPMessages) -> dict:
    """Возвращетс клавиатуру для настройки уведомлений.

    Args:
        sp (SPMessages): Генератор сообщений
        enabled (bool): Включены ли уведомления
        hours (list, optional): В какой час отправлять уведомления

    Returns:
        InlineKeyboardMarkup: Готовая клавитура для настройки
    """
    enabled = sp.user["notifications"]
    kb = Keyboard()
    kb.add(Text("🏠 Домой", payload={"cmd": "home"}))

    if not enabled:
        kb.add(Text("🔔 Включить", payload={"notify": "switch"}),
            color=KeyboardButtonColor.POSITIVE
        )
    else:
        kb.add(Text("🔕 Выключить", payload={"notify": "switch"}),
            color=KeyboardButtonColor.NEGATIVE
        )
        user_hours = set(sp.user["hours"])

        if user_hours:
            kb.add(Text("❌ Cбросить", payload={"notify": "reset"}),
                color=KeyboardButtonColor.PRIMARY
            )

        kb.row()
        for i, x in enumerate(set(range(6, 18))):
            if i > 0 and i % 4 == 0:
                kb.row()

            if x in user_hours:
                kb.add(Text(x, payload={"notify": "toggle", "hour": x}),
                    color=KeyboardButtonColor.POSITIVE
                )
            else:
                kb.add(Text(x, payload={"notify": "toggle", "hour": x}))

    return kb.get_json()


# Клавиатура счётчиков
# ====================

_COUNTERS = {
    "cl": "По классам",
    "days": "По дням",
    "lessons": "По урокам",
    "cabinets": "По кабинетам"
}

_TARGETS = {
    "none": "Ничего",
    "cl": "Классы",
    "days": "Дни",
    "lessons": "Уроки",
    "cabinets": "Кабинеты",
    "main": "Общее"
}

_EXCLUDE_TARGETS = ("lessons", "cabinets")

def get_counter_keyboard(sp: SPMessages, counter: str, target: str) -> dict:
    """Собирает клавиатуру для счётчиков.

    Args:
        sp (SPMessages): Генератор сообщений
        counter (str): Название текущего счётчика
        target (str): Названеи текущего режима просмотра

    Returns:
        dict: Собранная клавиатура
    """
    kb = Keyboard()

    # Группы счётчиков
    for k, name in _COUNTERS.items():
        if counter == k:
            continue

        kb.add(Text(name,
            payload={"cmd": "counter", "counter": k, "target": target}
        ))

    kb.row()

    # Типы счётчиков
    for k, name in _TARGETS.items():
        if target == k or counter == k:
            continue

        # Исключаем пункт main если это не EXCLUDE
        if k == "main" and counter not in _EXCLUDE_TARGETS:
            continue

        # Исключаем EXCLUDE если счётчик EXCLUDE
        if counter in _EXCLUDE_TARGETS and k in _EXCLUDE_TARGETS:
            continue

        # Пропускаем счётчик cl/lessons если класс не установлен
        if counter == "cl" and k == "lessons" and sp.user["class_let"] is None:
            continue

        kb.add(Text(name,
            payload={"cmd": "counter", "counter": counter, "target": k}
        ))

    kb.row()
    kb.add(Text("🏠 Домой", payload={"cmd": "home"}))

    return kb.get_json()


def get_updates_keyboard(
    page: int, total: int, cl: Optional[str]=None) -> dict:
    """Собирает клввиатуру для просмотра списка изменений расписания.

    Args:
        page (int): Номер текущей страницы обновлений
        total (int): Список всех страниц
        cl (str, optional): Для какого класс собрать клавиатуру

    Returns:
        dict: Готовая inline-клавиатура
    """

    return (Keyboard()
        .add(Text("◁",
            payload={"group":"updates", "action": "back", "i": page, "cl": cl}))
        .add(Text(f"{page+1}/{total}",
            payload={"group":"updates", "action": "switch", "i": page, "cl": cl
        }))
        .add(Text("▷",
            payload={"group":"updates", "action": "next", "i": page, "cl": cl}))
        .row()
        .add(Text("🏠 Домой", payload={"cmd": "home"}))
        .get_json()
    )
