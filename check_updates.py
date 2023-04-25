"""
Скрипт для автоматической проверки расписания.
Работает в паре с Teleram ботом.

- Обновляет расписание.
- Рассылает изменения в рпсписпнии.
- Рассылает расписание в указанный час.
- Удаляет недействительных пользователей.

Author: Milinuri Nirvalen
Ver: 0.3 (sp 5.3, telegram 1.12)
"""

from sp.filters import construct_filters
from sp.spm import SPMessages
from sp.spm import send_update
from sp.spm import users_path
from sp.utils import load_file
from sp.utils import save_file
from telegram import bot
from telegram import markup_generator
from telegram import week_markup

import asyncio
from datetime import datetime
from pathlib import Path

from aiogram import Dispatcher
from aiogram import executor
from aiogram.utils.exceptions import BotKicked
from aiogram.utils.exceptions import BotBlocked

from loguru import logger


dp = Dispatcher(bot)
logger.add("sp_data/updates.log")


async def process_update(bot, hour: int, uid: str, user: dict) -> None:
    """Проверяет обновления для пользователя (чата).

    Args:
        bot (ТИП): Экземпляр telegram бота
        hour (int): Текущий час
        uid (str): ID чата для проверки
        user (dict): Данные пользователя
    """
    sp = SPMessages(uid)

    # Отправляем расписание в указанные часы
    if str(hour) in user["hours"]:
        message = sp.send_today_lessons(construct_filters(sp.sc))
        markup = markup_generator(sp, week_markup)
        await bot.send_message(uid, text=message, reply_markup=markup)

    # Отправляем уведомления об обновлениях
    updates = sp.get_lessons_updates()
    if updates:
        message = "🎉 У вас изменилось расписание!"
        for update in updates:
            message += f"\n{send_update(update)}"

        await bot.send_message(uid, text=message)


async def main() -> None:
    hour = datetime.now().hour
    users = load_file(Path(users_path), {})
    logger.info("Start of the update process...")
    edited = False

    for k, v in list(users.items()):
        if not v.get("notifications") or not v.get("class_let"):
            continue

        logger.info("User: {}", k)
        try:
           await process_update(bot, hour, k, v)
        except (BotKicked, BotBlocked):
            logger.info("Remove user {}", k)
            edited = True
            del users[k]

        except Exception as e:
            logger.exception(e)

    if edited:
        logger.info("Save changed users file")
        save_file(Path(users_path), users)


# Запуск скрипта
# ==============

if __name__ == '__main__':
    executor.start(dp, main())
