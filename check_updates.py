"""
Скрипт для автоматической проверки расписания.
Работает в паре с Teleram ботом.

- Обновляет расписание.
- Рассылает изменения в рпсписпнии.
- Рассылает расписание в указанный час.
- Удаляет недействительных пользователей.

Author: Milinuri Nirvalen
Ver: 0.5 (sp 5.7+2b, telegram 1.14-b4)
"""

from datetime import datetime
from pathlib import Path

from aiogram import Dispatcher, executor
from aiogram.utils.exceptions import BotBlocked, BotKicked, MigrateToChat
from loguru import logger

from sp.intents import Intent
from sp.messages import SPMessages, send_update, users_path
from sp.utils import load_file, save_file
from telegram import bot, markup_generator, week_markup


dp = Dispatcher(bot)
logger.add("sp_data/updates.log")

CHAT_MIGRATE_MESSAGE = """⚠️ У вашего чата сменился ID.
Настройки чата были перемещены.."""


async def process_update(bot, hour: int, sp: SPMessages) -> None:
    """Проверяет обновления для пользователя (или чата).

    Args:
        bot (bot): Экземпляр aiogram бота.
        hour (int): Текущий час.
        uid (str): ID чата для проверки.
        sp (SPMessages): Данные пользователя.
    """
    # Отправляем расписание в указанные часы
    if str(hour) in sp.user["hours"]:
        message = sp.send_today_lessons(Intent.new())
        markup = markup_generator(sp, week_markup)
        await bot.send_message(sp.uid, text=message, reply_markup=markup)

    # Отправляем уведомления об обновлениях
    updates = sp.get_lessons_updates()
    if updates:
        message = "🎉 У вас изменилось расписание!"
        for update in updates:
            message += f"\n{send_update(update, cl=sp.user['class_let'])}"

        await bot.send_message(sp.uid, text=message)


# Главная функция скрипта
# =======================

async def main() -> None:
    hour = datetime.now().hour
    users = load_file(Path(users_path), {})
    logger.info("Start of the update process...")
    edited = False

    for k, v in list(users.items()):
        # Если не включены уведомленияя или не укзаан класс
        if not v.get("notifications") or not v.get("class_let"):
            continue

        sp = SPMessages(k, v)
        logger.info("User: {}", k)
        try:
           await process_update(bot, hour, sp)

        # Если чат мигрировал в супергруппу
        except MigrateToChat as e:
            logger.info("Migrate to chat: {}", e)
            new_id = e.migrate_to_chat_id
            users[new_id] = users[k]
            del users[k]
            await bot.send_message(new_id, CHAT_MIGRATE_MESSAGE)
            edited = True

        # Если бота заблокировали или исключили
        except (BotKicked, BotBlocked):
            logger.info("Remove user {}", k)
            edited = True
            del users[k]

        # Все прочие исключения
        except Exception as e:
            logger.exception(e)

    # Если данные изменились - записываем изменения
    if edited:
        logger.info("Save changed users file")
        save_file(Path(users_path), users)


# Запуск скрипта
# ==============

if __name__ == '__main__':
    executor.start(dp, main())
