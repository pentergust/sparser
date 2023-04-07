"""
Скрипт для проверки и отправки изменения в рпсписании.
Работает в паре с телеграмм ботом.

Author: Milinuri Nirvalen
Ver: 0.1 (sp 5.3, telegram 1.11)
"""
from sp.spm import SPMessages
from sp.spm import users_path
from sp.spm import send_update
from sp.utils import load_file
from sp.filters import construct_filters
from telegram import bot

import asyncio
from pathlib import Path
from datetime import datetime

from loguru import logger


logger.add("sp_data/updates.log")

async def main() -> None:
    hour = datetime.now().hour
    users = load_file(Path(users_path), {})
    logger.info("Start of the update process")

    for k, v in users.items():
        if not v["notifications"]:
            continue

        logger.info("User: {}", k)
        sp_user = SPMessages(k)
        updates = sp_user.get_lessons_updates()

        if updates:
            message = "🎉 У вас изменилось расписание!"
            for update in updates:
                message += f"\n{send_update(update)}"

            await bot.send_message(k, text=message)

        if str(hour) in v["hours"]:
            message = sp_user.send_today_lessons(construct_filters(sp_user.sc))
            await bot.send_message(k, text=message)


if __name__ == '__main__':
    asyncio.run(main())
