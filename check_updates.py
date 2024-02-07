"""
Скрипт для автоматической проверки расписания.
Работает в паре с Teleram ботом.

- Проверяет пользователей.
- Обновляет расписание.
- Отправляет изменения в расписании пользователям.
- Рассылает расписание на сегодня/завтра пользователям.
- Удаляет пользователей.

Author: Milinuri Nirvalen
Ver: 0.10.1 (sp v5.7+2b, telegram v2.0)
"""

from datetime import datetime
from pathlib import Path
from os import getenv
import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from dotenv import load_dotenv

from sp.intents import Intent
from sp.messages import SPMessages, send_update, users_path
from sp.utils import load_file, save_file


load_dotenv()
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
bot = Bot(TELEGRAM_TOKEN)
logger.add("sp_data/updates.log")
_TIMETAG_PATH = Path("sp_data/last_update")

# Если данные мигрировали вследствии
CHAT_MIGRATE_MESSAGE = """⚠️ У вашего чата сменился ID.
Настройки чата были перемещены."""


# Функкии для сбора клавиатур
# ===========================

def get_week_keyboard(cl: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠Домой", callback_data="home"),
        InlineKeyboardButton(text="На неделю", callback_data=f"sc:{cl}:week"),
        InlineKeyboardButton(text="▷", callback_data=f"select_day:{cl}"),
    ]])

def get_updates_keyboard(cl: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◁", callback_data="home"),
        InlineKeyboardButton(text="Изменения", callback_data=f"updates:last:0:{cl}"),
        InlineKeyboardButton(text="Уроки", callback_data=f"sc:{cl}:today")
    ]])


# Функции для обработки списка пользователей
# ==========================================

async def process_update(bot, hour: int, sp: SPMessages) -> None:
    """Проверяет обновления для одного пользователя (или чата).

    Отправляет расписани на сегодня/завтра в указанный час или
    список измнений в расписании, при наличии.

    Args:
        bot (bot): Экземпляр aiogram бота.
        hour (int): Текущий час.
        uid (str): ID чата для проверки.
        sp (SPMessages): Данные пользователя.
    """
    # Рассылка расписания в указанные часы
    if str(hour) in sp.user["hours"]:
        await bot.send_message(sp.uid,
            text=sp.send_today_lessons(Intent()),
            reply_markup=get_week_keyboard(sp.user["class_let"])
        )

    # Отправляем уведомления об обновлениях
    updates = sp.get_lessons_updates()
    if updates is not None:
        message = "🎉 У вас изменилось расписание!"
        message += f"\n{send_update(updates, cl=sp.user['class_let'])}"

        await bot.send_message(sp.uid, text=message,
            reply_markup=get_updates_keyboard(sp.user["class_let"]
        ))

async def remove_users(remove_ids: list[str]):
    """Удаляет недействительные ID пользователей (чата).

    Если пользователь заблокировал бота.
    Если бота исключили из чата.
    Если пользователь удалил аккаунт.

    Args:
        remove_ids (list[str]) Список ID для удаления.
    """
    logger.info("Start remove users...")
    users = load_file(Path(users_path), {})
    for x in remove_ids:
        logger.info("Remove {}", x)
        del users[x]
    save_file(Path(users_path), users)


def set_timetag(path: Path, timestamp: int) -> None:
    """Оставляет временную метку последней проверки обнолвения.

    После успешной работы скрипта записывает в файл временную метку.
    Метка может использватьна для проверки работаспособности
    скрипта обновлений.

    Args:
        path (Path): Путь к файлу временной метки.
        timestamp (int): Временная UNIXtime метка.
    """

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write(str(timestamp))


# Главная функция скрипта
# =======================

async def main() -> None:
    now = datetime.now()
    users = load_file(Path(users_path), {})
    remove_ids = []

    logger.info("Start of the update process...")
    for k, v in list(users.items()):
        # Если у пользователя отключены уведомления или не указан
        # класс по умолчанию -> пропускаем.
        if not v.get("notifications") or not v.get("class_let"):
            continue

        # Получаем экземпляр генератора сообщения пользователя
        # TODO: данные пользователя вновь загружаются из файла на
        # каждой итерации
        sp = SPMessages(k, v)
        try:
            logger.debug("{} {}", k, v)
            await process_update(bot, now.hour, sp)

        # Если что-то произошло с пользователем:
        # Заблокировал бота, исключил из чата, исчез сам ->
        # Удаляем пользователя (чат) из списка чатов.
        except TelegramForbiddenError:
            remove_ids.append(k)

        # Ловим все прочие исключения и отображаем их на экран
        except Exception as e:
            logger.exception(e)

    # Если данные изменились - записываем изменения в файл
    if remove_ids:
        await remove_users(remove_ids)

    # Осталяем временную метку успешного обновления
    set_timetag(_TIMETAG_PATH, int(now.timestamp()))


# Запуск скрипта обновлений
# =========================

if __name__ == '__main__':
    asyncio.run(main())