"""
Скрипт для проверки и рассылки изменения в расписании.
Работает в паре с Teleram ботом.

Author: Milinuri Nirvalen
Ver: 0.2 (sp 5.3, telegram 1.11)
"""
from sp.filters import construct_filters
from sp.spm import SPMessages
from sp.spm import send_update
from sp.spm import users_path
from sp.utils import load_file
from telegram import bot
from telegram import markup_generator
from telegram import week_markup

import asyncio

from datetime import datetime
from pathlib import Path

from aiogram import Dispatcher
from aiogram import executor
from loguru import logger


dp = Dispatcher(bot)
logger.add("sp_data/updates.log")

async def main() -> None:
    hour = datetime.now().hour
    users = load_file(Path(users_path), {})
    logger.info("Start of the update process...")

    for k, v in users.items():
        if not v.get("notifications") or not v.get("class_let"):
            continue

        logger.info("User: {}", k)
        sp_user = SPMessages(k)

        if str(hour) in v["hours"]:
            message = sp_user.send_today_lessons(construct_filters(sp_user.sc))
            markup = markup_generator(sp_user, week_markup)
            await bot.send_message(k, text=message, reply_markup=markup)
            continue

        updates = sp_user.get_lessons_updates()
        if updates:
            message = "🎉 У вас изменилось расписание!"
            for update in updates:
                message += f"\n{send_update(update)}"

            await bot.send_message(k, text=message)


if __name__ == '__main__':
    executor.start(dp, main())
    # asyncio.run(main())
