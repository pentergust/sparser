"""
Скрипт для автоматической проверки расписания.
Работает в паре с Teleram ботом.

- Проверяет пользователей.
- Обновляет расписание.
- Отправляет изменения в расписании пользователям.
- Рассылает расписание на сегодня/завтра пользователям.
- Удаляет пользователей.

Author: Milinuri Nirvalen
Ver: 0.6 (sp 5.7+2b, telegram 1.14 +b5)
"""

from datetime import datetime
from pathlib import Path

from aiogram import Dispatcher, executor
from aiogram.utils.exceptions import BotBlocked, BotKicked, MigrateToChat, UserDeactivated
from loguru import logger

from sp.intents import Intent
from sp.messages import SPMessages, send_update, users_path
from sp.utils import load_file, save_file
from telegram import bot, markup_generator, week_markup


# Если данные мигрировали вследствии .
CHAT_MIGRATE_MESSAGE = """⚠️ У вашего чата сменился ID.
Настройки чата были перемещены.."""

dp = Dispatcher(bot)
logger.add("sp_data/updates.log")


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
    # Рассылка расписания в указанные часы.
    if str(hour) in sp.user["hours"]:
        await bot.send_message(sp.uid,
            text=sp.send_today_lessons(Intent.new()),
            reply_markup=markup_generator(sp, week_markup)
        )

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
    edited = False

    logger.info("Start of the update process...")
    for k, v in list(users.items()):
        # Если у пользователя отключены уведомления или не указан
        # класс по умолчанию -> пропускаем.
        if not v.get("notifications") or not v.get("class_let"):
            continue

        # Получаем экземлпря генратора сообщения пользователя
        # TODO: данные пользователя вновь загружаются из файла на
        # каждой итерации
        sp = SPMessages(k, v)
        logger.info("User: {}", k)
        try:
            await process_update(bot, hour, sp)

        # Если чат сменил свой ID.
        # Например, стал из обычного супергруппой.
        except MigrateToChat as e:
            logger.info("Migrate to chat: {}", e)
            new_id = e.migrate_to_chat_id
            users[new_id] = users[k]
            del users[k]
            await bot.send_message(new_id, CHAT_MIGRATE_MESSAGE)
            edited = True

        # Если что-то произошло с пользователем:
        # Заблокировал бота, исключил из чата, исчез сам ->
        # Удаляем пользователя (чат) из списка чатов.
        except (BotKicked, BotBlocked, UserDeactivated):
            logger.info("Remove user {}", k)
            edited = True
            del users[k]

        # Ловим все прочие исключения и отобржаем их на экран
        except Exception as e:
            logger.exception(e)

    # Если данные изменились - записываем изменения в файл
    if edited:
        logger.info("Save changed users file")
        save_file(Path(users_path), users)


# Запуск скрипта обновлений
# =========================

if __name__ == '__main__':
    executor.start(dp, main())
