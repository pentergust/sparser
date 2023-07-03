"""
Вк бот для доступа к SPMessages.

Author: Milinuri Nirvalen
Ver: 1.0 (9)
"""

from sp.filters import construct_filters
from sp.filters import parse_filters
from sp.spm import SPMessages
from sp.spm import send_update

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

def process_request(sp: SPMessages, request_text: str) -> Optional[str]:
    """Обрабатывает текстовый запрос к расписанию.

    Args:
        sp (SPMessages): Экземпляр генератора сообщений
        request_text (str): Текст запроса к расписанию

    Returns:
        str: Результат запроса к расписанию
    """

    flt = parse_filters(sp.sc, request_text.split())

    # Чтобы не превращать бота в машину для спама
    # Будет использоваться последний урок/кабинет из фильтра
    if len(flt.cabinets):
        text = sp.search_cabinet(list(flt.cabinets)[-1], flt)
    elif len(flt.lessons):
        text = sp.search_lesson(list(flt.lessons)[-1], flt)
    elif flt.cl or flt.days:
        text = sp.send_lessons(flt) if flt.days else sp.send_today_lessons(flt)
    else:
        text = None

    return text


# Определение обработчиков
# ========================

@bot.on.message(command="home")
@bot.on.message(payload={"cmd": "home"})
@bot.on.message(payload={"command": "start"})
async def home_handler(message: Message, sp: SPMessages):
    if sp.user["set_class"]:
        await message.answer(messages.send_home_message(sp),
            keyboard=keyboards.get_home_keyboard(sp)
        )
    else:
        await message.answer(messages.SET_CLASS,
            keyboard=keyboards.SET_CLASS
        )


# Текстовая информация
# ====================

@bot.on.message(command="restrictions")
@bot.on.message(payload={"cmd": "restrictions"})
async def restrictions_handler(message: Message):
    await message.answer(messages.RESTRICTIONS)

@bot.on.message(command="info")
@bot.on.message(payload={"cmd": "info"})
async def info_command(message: Message, sp: SPMessages):
    """Отправляет статус парсера и бота."""
    await message.answer(sp.send_status()+messages.INFO)


# Смена класса пользователя
# =========================

@bot.on.message(command=("set_class", 1))
async def set_class_hadler(message: Message, sp: SPMessages, args: tuple[str]):
    """Явно устанавливает класс пользователя."""
    cl = args[0].lower().strip()
    if cl in ("-", "pass"):
        sp.user["class_let"] = None
        sp.user["set_class"] = True
        sp.save_user()
        text = messages.send_home_message(sp)
        kb = keyboards.get_home_keyboard(sp)

    elif cl in sp.sc.lessons:
        sp.set_class(cl)
        text = messages.send_home_message(sp)
        kb = keyboards.get_home_keyboard(sp)

    else:
        text = "👀 Такого класса не существует."
        kb = keyboards.SET_CLASS

    await message.answer(text, keyboard=kb)

@bot.on.message(command="set_class")
@bot.on.message(payload={"cmd": "set_class"})
async def reset_user_hadler(message: Message, sp: SPMessages):
    """Неявное изменение класса пользоватлея."""
    if message.reply_message is not None:
        cl = message.reply_message.text
        if cl in sp.sc.lessons:
            sp.set_class(cl)
            text = f"✏️ Класс изменён на {cl}"
            kb = keyboards.get_home_keyboard(sp)
        else:
            text = "👀 Такого класса не существует."
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
        answer = process_request(sp, request)
        if answer is not None:
            text = answer
        else:
            text = "👀 Кажется это пустой запрос..."

    elif sp.user["class_let"]:
        payload = message.get_payload_json()
        if payload is not None:
            cl = payload.get("cl", sp.user["class_let"])
            days = payload.get("days")
            flt = construct_filters(sp.sc, cl=cl, days=days)

            if days is not None:
                text = sp.send_lessons(flt)
            else:
                text = sp.send_today_lessons(flt)

        else:
            text = sp.send_today_lessons(construct_filters(sp.sc))

    else:
        text = "⚠️ Для быстрого получения расписания вам нужно указать класс."

    await message.answer(text)

@bot.on.message(command="week")
@bot.on.message(payload={"cmd": "week"})
async def week_sc_handler(message: Message, sp: SPMessages):
    """Отправляет расписание на неделю."""
    if sp.user["class_let"]:
        flt = construct_filters(sp.sc, days=[0, 1, 2, 3, 4, 5])
        text = sp.send_lessons(flt)
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
        text = messages.send_notifications_info(sp)
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
    await message.answer(messages.send_notifications_info(sp),
        keyboard=keyboards.get_notify_keyboad(sp)
    )

@bot.on.message(payload_contains={"notify": "add"})
async def add_notify_hour_handler(message: Message, sp: SPMessages):
    """Добавляет час для отправки оповещений."""
    hour = int(message.get_payload_json()["hour"])
    if hour not in sp.user["hours"]:
        sp.user["hours"].append(hour)
        sp.save_user()

    await message.answer(f"🔔 Включено оповещение в {hour} часов.",
        keyboard=keyboards.get_notify_keyboad(sp)
    )

@bot.on.message(payload_contains={"notify": "remove"})
async def remove_notify_hour_handler(message: Message, sp: SPMessages):
    """Удаляет час для отправки оповещений."""
    hour = int(message.get_payload_json()["hour"])
    if hour in sp.user["hours"]:
        sp.user["hours"].remove(hour)
        sp.save_user()

    await message.answer(f"🔔 Отключено оповещение в {hour} часов.",
        keyboard=keyboards.get_notify_keyboad(sp)
    )

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
@bot.on.message(payload={"updates": "last"})
async def updates_command(message: Message, sp: SPMessages):
    """Оправляет список изменений в расписании."""

    text = "🔔 Изменения в расписании:\n"

    updates = sp.sc.updates
    if len(updates):
        text = send_update(updates[-1])
    else:
        text = "Нет новых обновлений."

    kb = keyboards.get_updates_keyboard(
        max(len(updates)-1, 0), len(updates)
    )
    await message.answer(text, keyboard=kb)

@bot.on.message(payload_contains={"updates": "switch"})
async def switch_updates_handler(message: Message, sp: SPMessages):
    """Переключает просмотр списка обновлений.
    Между общим и для класса.
    """

    text = "🔔 Изменения "
    payload = message.get_payload_json()
    cl = sp.user["class_let"] if payload["cl"] is None else None

    # Доплняем шапку сообщения
    if cl is not None and sp.user["set_class"]:
        text += f"для {cl}:\n"
        flt = construct_filters(sp.sc, cl=cl)
    else:
        text += "в расписании:\n"
        flt = construct_filters(sp.sc)

    updates = sp.sc.get_updates(flt)

    if len(updates):
        text += send_update(updates[-1])
    else:
        text += "Нет новых обновлений."

    kb = keyboards.get_updates_keyboard(
        max(len(updates)-1, 0), len(updates), cl
    )
    await message.answer(text, keyboard=kb)

@bot.on.message(payload_contains={"updates": "next"})
async def next_updates_handler(message: Message, sp: SPMessages):
    """Получает следующую страницу обновлений расписания."""

    text = "🔔 Изменения "
    payload = message.get_payload_json()
    cl = payload["cl"]

    if cl is not None and sp.user["set_class"]:
        text += f"для {cl}:\n"
        flt = construct_filters(sp.sc, cl=cl)
    else:
        text += "в расписании:\n"
        flt = construct_filters(sp.sc)

    updates = sp.sc.get_updates(flt)
    i = (max(min(payload["i"], len(updates)-1), 0) + 1) % len(updates)
    text += send_update(updates[i])

    kb = keyboards.get_updates_keyboard(i, len(updates), cl)
    await message.answer(text, keyboard=kb)

@bot.on.message(payload_contains={"updates": "back"})
async def back_updates_handler(message: Message, sp: SPMessages):
    """Получает предыдущую страницу обновлений расписания."""

    text = "🔔 Изменения "
    payload = message.get_payload_json()
    cl = payload["cl"]

    if cl is not None and sp.user["set_class"]:
        text += f"для {cl}:\n"
        flt = construct_filters(sp.sc, cl=cl)
    else:
        text += "в расписании:\n"
        flt = construct_filters(sp.sc)

    updates = sp.sc.get_updates(flt)
    i = (max(min(payload["i"], len(updates)-1), 0) - 1) % len(updates)
    text += send_update(updates[i])

    kb = keyboards.get_updates_keyboard(i, len(updates), cl)
    await message.answer(text, keyboard=kb)


# Обработка текстовых запросов
# ============================

@bot.on.message()
async def message_handler(message: Message, sp: SPMessages):
    """Обработчик текстовых запросов к боту."""
    uid = str(message.peer_id)
    text = message.text.strip().lower()

    if sp.user["set_class"]:
        answer = process_request(sp, text)

        if answer is not None:
            await message.answer(answer)
        elif message.peer_id == message.from_id:
            await message.answer("👀 Кажется это пустой запрос...")

    elif text in sp.sc.lessons:
        sp.set_class(text)
        await message.answer(messages.send_home_message(sp),
            keyboard=keyboards.get_home_keyboard(sp)
        )
