"""Скрипт для автоматической проверки расписания.

Работает в паре с Teleram ботом.
Данные для авторизации будут взяты из env файла.

- Проверяет пользователей.
- Обновляет расписание.
- Отправляет изменения в расписании пользователям.
- Рассылает расписание на сегодня/завтра пользователям.
- Удаляет пользователей.

Author: Milinuri Nirvalen
Ver: 0.11.4 (sp v6.1.7, telegram v2.5)
"""

import asyncio
from datetime import datetime
from os import getenv
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from loguru import logger

from sp.intents import Intent
from sp.messages import SPMessages
from sp.platform import Platform
from sp.users.storage import User

# Запуск плфтформы и TG бота
# ==========================

load_dotenv()
TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
bot = Bot(TELEGRAM_TOKEN)
logger.add("sp_data/updates.log")
_TIMETAG_PATH = Path("sp_data/last_update")

# Если данные мигрировали вследствии
CHAT_MIGRATE_MESSAGE = (
    "⚠️ У вашего чата сменился ID.\n"
    "Настройки чата были перемещены."
)

# Функкии для сбора клавиатур
# ===========================

def get_week_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Получает клавиатуру для расписание на неделю.

    За подробностями обращайтесь к модулю ``sptg``.
    """
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠Домой", callback_data="home"),
        InlineKeyboardButton(text="На неделю", callback_data=f"sc:{cl}:week"),
        InlineKeyboardButton(text="▷", callback_data=f"select_day:{cl}"),
    ]])

def get_updates_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Клавиатура сообщения с обновлением.

    Данная клавиатура будет отправляться в месте с сообщением об
    изменениях в расписании.
    Она содержет в себе ссылки на все основные разделы, которые нужны
    при просмотре сообщения с изменением:

    - Вернуться домой.
    - Перейти к списку измененйи.
    - Получить расписание на сегодня/завтра.
    """
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◁", callback_data="home"),
        InlineKeyboardButton(
            text="Изменения", callback_data=f"updates:last:0:{cl}:"
        ),
        InlineKeyboardButton(text="Уроки", callback_data=f"sc:{cl}:today")
    ]])


# Функции для обработки списка пользователей
# ==========================================

async def process_update(
    bot: Bot,
    hour: int,
    platform: Platform,
    user: User
) -> None:
    """Проверяет обновления для одного пользователя (или чата).

    Отправляет расписани на сегодня/завтра в указанный час или
    список измнений в расписании, при наличии.

    :param bot: Экземпляр бота для отправки сообщений.
    :type bot: Bot
    :param hour: Какой сейчас час.
    :type hour: int
    :param platform: Экземпляр запущенной платформы.
    :type platform: Platform
    :param user: Какой пользователь запрашивает обновления.
    :type user: User
    """
    # Рассылка расписания в указанные часы
    if hour in user.data.hours:
        logger.info("Send schedule")
        await bot.send_message(user.uid,
            text=platform.today_lessons(user),
            reply_markup=get_week_keyboard(user.data.cl)
        )

    # Отправляем уведомления об обновлениях
    updates = user.get_updates(platform.view.sc, save_users=False)
    if updates is None:
        return

    logger.info("Send comparc updates message")
    updates_message = platform.updates(updates, hide_cl=user.data.cl)
    if len(updates_message) > 4000:
        updates_message = "f\n< слишком много изменений >"

    await bot.send_message(user.uid,
        text=f"🎉 У вас изменилось расписание!\n{updates_message}",
        reply_markup=get_updates_keyboard(user.data.cl)
    )

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
    platform = Platform(
        pid=1, name="Telegram updater",
        version="0.11", api_version=0
    )
    platform.view = SPMessages()
    now = datetime.now()
    remove_ids = []

    logger.info("Start of the update process...")
    for k, v in platform.users.get_users().items():
        # Если у пользователя отключены уведомления или не указан
        # класс по умолчанию -> пропускаем.
        if not v.notifications or not v.cl:
            continue

        # Получаем экземпляр генератора сообщения пользователя
        # TODO: данные пользователя вновь загружаются из файла на
        # каждой итерации
        user = platform.get_user(k)
        try:
            logger.debug("Process {}: {}", k, v)
            await process_update(bot, now.hour, platform, user)

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
        platform.users.remove_users(remove_ids)

    # Осталяем временную метку успешного обновления
    set_timetag(_TIMETAG_PATH, int(now.timestamp()))
    platform.users.save_users()


# Запуск скрипта обновлений
# =========================

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(e)