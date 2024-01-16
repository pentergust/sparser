"""
Вк бот для доступа к SPMessages.

Author: Milinuri Nirvalen
Ver: 1.2 (23, sp v5.7)
"""

from sp.intents import Intent
from sp.messages import SPMessages
from sp.messages import send_update
from sp.messages import send_search_res

from typing import Optional

from sp_vk import config
from sp_vk import messages
from sp_vk import keyboards

from vkbottle.bot import Bot
from vkbottle.bot import Message


bot = Bot(token=config.VK_TOKEN)
days_names = ["понедельник", "вторник", "среда", "четверг", "пятница",
              "суббота", "сегодня", "неделя"]


# Вспомогательные функции
# =======================

def process_request(sp: SPMessages, request_text: str) -> str:
    """Обрабатывает текстовый запрос к расписанию.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений
        request_text (str): Текст запроса к расписанию

    Returns:
        str: Результат запроса к расписанию
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
            text = sp.send_today_lessons(intent)

    else:
        text = "👀 Кажется это пустой запрос."

    return text


# Определение обработчиков
# ========================

@bot.on.message(command="home")
@bot.on.message(payload={"cmd": "home"})
@bot.on.message(payload={"command": "start"})
async def home_handler(message: Message, sp: SPMessages):
    """Справка и главная клавиатура."""
    if sp.user["set_class"]:
        await message.answer(messages.HOME,
            keyboard=keyboards.get_home_keyboard(sp)
        )
    else:
        await message.answer(messages.SET_CLASS,
            keyboard=keyboards.SET_CLASS
        )


# Текстовая информация
# ====================

@bot.on.message(command="cl_features")
@bot.on.message(payload={"cmd": "cl_features"})
async def cl_features_handler(message: Message):
    """Список огранчиений при отвязанном классе."""
    await message.answer(messages.CL_FEATURES)

@bot.on.message(command="info")
@bot.on.message(payload={"cmd": "info"})
async def info_handler(message: Message, sp: SPMessages):
    """Cтатус парсера и бота."""
    await message.answer(sp.send_status()+messages.INFO)


# Смена класса пользователя
# =========================

@bot.on.message(command=("set_class", 1))
async def set_class_hadler(message: Message, sp: SPMessages, args: tuple[str]):
    """Явно устанавливает класс пользователя."""
    cl = args[0].lower().strip()
    res = sp.set_class(None if cl in ("-", "pass") else cl)

    if res is True:
        text = messages.HOME
    else:
        text = "👀 Такого класса не существует."
        text += f"\n💡 Доступныe классы: {', '.join(sp.sc.lessons)}"

    await message.answer(text, keyboard=keyboards.get_main_keyboard(sp))

@bot.on.message(command="set_class")
@bot.on.message(payload={"cmd": "set_class"})
async def reset_user_hadler(message: Message, sp: SPMessages, cl: Optional[str]=None):
    """Неявное изменение класса пользоватлея."""
    if message.reply_message is not None:
        cl = message.reply_message.text
        res = sp.set_class(cl)

        if res:
            text = messages.HOME
            kb = keyboards.get_home_keyboard(sp)
        else:
            text = "👀 Такого класса не существует."
            kb = keyboards.get_main_keyboard(sp)
            text += f"\n💡 Доступныe классы: {', '.join(sp.sc.lessons)}"

    else:
        sp.reset_user()
        text = messages.SET_CLASS
        kb = keyboards.SET_CLASS

    await message.answer(text, keyboard=kb)

@bot.on.message(command="pass")
@bot.on.message(payload={"cmd": "pass"})
async def pass_handler(message: Message, sp: SPMessages):
    """Отвязывает пользователя от класса."""
    if not sp.user["set_class"]:
        sp.user["set_class"] = True
        sp.save_user()
        await message.answer(messages.send_home_message(sp),
            keyboard=keyboards.get_home_keyboard(sp)
        )


# Получени расписания
# ===================

@bot.on.message(command="sc")
@bot.on.message(payload_contains={"cmd": "sc"})
async def sc_handler(message: Message, sp: SPMessages):
    """Отправляет расписание уроков."""

    if message.reply_message is not None:
        request = message.reply_message.text.strip().lower()
        text = process_request(sp, request)

    elif sp.user["class_let"]:
        payload = message.get_payload_json()
        if payload is not None:
            cl = payload.get("cl", sp.user["class_let"])
            days = payload.get("days")

            if days is not None:
                intent = Intent.construct(sp.sc, cl=[cl], days=days)
                text = sp.send_lessons(intent)
            else:
                intent = Intent.construct(sp.sc, cl=[cl])
                text = sp.send_today_lessons(intent)

        else:
            text = sp.send_today_lessons(Intent())

    else:
        text = "⚠️ Для быстрого получения расписания вам нужно указать класс."

    await message.answer(text)

@bot.on.message(command="week")
@bot.on.message(payload={"cmd": "week"})
async def week_sc_handler(message: Message, sp: SPMessages):
    """Отправляет расписание на неделю."""
    if sp.user["class_let"]:
        intent = Intent.construct(sp.sc, days=[0, 1, 2, 3, 4, 5])
        text = sp.send_lessons(intent)
    else:
        text = "⚠️ Для быстрого получения расписания вам нужно указать класс."

    await message.answer(text)


# Настройки уведомлений
# =====================

@bot.on.message(command="notify")
@bot.on.message(payload={"notify": "info"})
async def notify_info_handler(message: Message, sp: SPMessages):
    """Отправдяет информацию об уведомлениях."""
    if sp.user["class_let"]:
        text = messages.send_notify_info(sp.user["enable"], sp.user["hours"])
        kb = keyboards.get_notify_keyboad(sp)
    else:
        text = "⚠️ Для работы системы уведомлений вам нужно указать класс."
        kb = keyboards.get_home_keyboard(sp)

    await message.answer(text, keyboard=kb)

@bot.on.message(payload={"notify": "switch"})
async def switch_notify_handler(message: Message, sp: SPMessages):
    """Переключает уведомления."""
    if sp.user["notifications"]:
        sp.user["notifications"] = False
    else:
        sp.user["notifications"] = True

    sp.save_user()
    await message.answer(messages.send_notify_info(
            sp.user["enabled"], sp.user["hours"]
        ),
        keyboard=keyboards.get_notify_keyboad(sp)
    )

@bot.on.message(payload_contains={"notify": "toggle"})
async def toggle_notify_hour_handler(message: Message, sp: SPMessages):
    """Переключает отправку уведомлений в укзаанный час."""
    hour = int(message.get_payload_json()["hour"])

    if hour in sp.user["hours"]:
        sp.user["hours"].remove(hour)
        text = f"🔕 Отключено оповещение в {hour} часов."
    else:
        sp.user["hours"].append(hour)
        text = f"🔔 Включено оповещение в {hour} часов."

    sp.save_user()
    await message.answer(text, keyboard=keyboards.get_notify_keyboad(sp))

@bot.on.message(payload={"notify": "reset"})
async def reset_nofify_handler(message: Message, sp: SPMessages):
    """Сбрасывает часы отправки уведомлений."""
    sp.user["hours"] = []
    sp.save_user()

    await message.answer("🔔 Уведомления сброшены.",
        keyboard=keyboards.get_notify_keyboad(sp)
    )


# Счётчики
# ========

@bot.on.message(command="counter")
@bot.on.message(payload_contains={"cmd": "counter"})
async def counter_handler(message: Message, sp: SPMessages):
    """Отправляет сообщение с счётчиком."""
    payload = message.get_payload_json()

    if payload is not None:
        counter = payload.get("counter", "lessons")
        target = payload.get("target", "main")

        if counter == target:
            target = None

        if counter == "cl" and target == "lessons" and not sp.user["class_let"]:
            target = None

    else:
        counter = "lessons"
        target = "main"

    await message.answer(
        messages.send_counter_message(sp.sc, counter, target),
        keyboard=keyboards.get_counter_keyboard(sp, counter, target)
    )


# Изменения в расписании
# ======================

@bot.on.message(command="updates")
@bot.on.message(payload={"group":"updates", "action": "last"})
async def updates_command(message: Message, sp: SPMessages):
    """Оправляет список изменений в расписании."""
    updates = sp.sc.updates
    update = updates[-1] if len(updates) else None
    await message.answer(messages.send_updates(update),
        keyboard=keyboards.get_updates_keyboard(
           max(len(updates)-1, 0), len(updates)
        )
    )

@bot.on.message(payload_contains={"group":"updates"})
async def updates_handler(message: Message, sp: SPMessages):
    """Обработчик клавиатуры списка обновлений."""
    payload = message.get_payload_json()

    # Смена класса, если требутеся
    if payload["action"] == "switch":
        cl = sp.user["class_let"] if payload["cl"] is None else None
    else:
        cl = payload["cl"]

    if cl is not None and sp.user["set_class"]:
        intent = Intent.construct(sp.sc, cl=[cl])
    else:
        intent = Intent()

    updates = sp.sc.get_updates(intent)

    if len(updates):
        if payload["action"] == "switch":
            update = updates[-1]
            i = max(len(updates)-1, 0)
        elif payload["action"] == "next":
            i = (max(min(payload["i"], len(updates)-1), 0) + 1) % len(updates)
            update = updates[i]
        elif payload["action"] == "back":
            i = (max(min(payload["i"], len(updates)-1), 0) - 1) % len(updates)
            update = updates[i]
    else:
        update = None
        i = 0

    await message.answer(
        messages.send_updates(update, cl),
        keyboard=keyboards.get_updates_keyboard(i, len(updates), cl)
    )


# Многостраничная справка
# =======================

@bot.on.message(command="tutorial")
@bot.on.message(payload_contains={"group":"tutorial"})
async def tutorial_handler(message: Message):
    """Обработчик многостраничной справки."""
    payload = message.get_payload_json()
    page = 0 if payload is None else int(payload.get("page", 0))
    await message.answer(messages.TUTORIAL_MESSAGES[page],
        keyboard=keyboards.get_tutorial_keyboard(page)
    )


# Обработка текстовых запросов
# ============================

@bot.on.private_message()
async def message_handler(message: Message, sp: SPMessages):
    """Обработчик текстовых запросов к расписнаию."""
    uid = str(message.peer_id)
    text = message.text.strip().lower()

    if sp.user["set_class"]:
        await message.answer(process_request(sp, text))

    elif text in sp.sc.lessons:
        sp.set_class(text)
        await message.answer(messages.HOME,
            keyboard=keyboards.get_home_keyboard(sp)
        )
    else:
        text = "👀 Такого класса не существует."
        text += f"\n💡 Доступныe классы: {', '.join(sp.sc.lessons)}"
        await message.answer(text)
