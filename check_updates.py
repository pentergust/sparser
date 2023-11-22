"""
Скрипт для автоматической проверки расписания.
Работает в паре с Teleram ботом.

- Проверяет пользователей.
- Обновляет расписание.
- Отправляет изменения в расписании пользователям.
- Рассылает расписание на сегодня/завтра пользователям.
- Удаляет пользователей.

Author: Milinuri Nirvalen
Ver: 0.8 (sp 5.7+2b, telegram 1.14 +b5)
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
_TIMETAG_PATH = Path("sp_data/last_update")


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

async def migrate_users(migrate_ids: list[tuple[str, str]]) -> None:
    """Перемещает данные пользователей (чатов) на новый ID.

    Например, вследствии перемещания группы в супергруппу.

    Args:
        migrate_ids (list[tuple[str, str]]): ID для миграции.
    """
    logger.info("Start migrate users...")
    users = load_file(Path(users_path), {})
    for old, new in migrate_ids:
        logger.info("Migrate {} -> {}". old, new)
        users[new] = users[old]
        del users[k]
        await bot.send_message(new, CHAT_MIGRATE_MESSAGE)
    save_file(Path(users_path), users)

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
        logger.info("Remove {}". x)
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
    migrate_ids = []

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
            await process_update(bot, now.hour, sp)

        # Если чат сменил свой ID.
        # Например, стал из обычного супергруппой.
        except MigrateToChat as e:
            migrate_ids.append((k, e.migrate_to_chat_id))

        # Если что-то произошло с пользователем:
        # Заблокировал бота, исключил из чата, исчез сам ->
        # Удаляем пользователя (чат) из списка чатов.
        except (BotKicked, BotBlocked, UserDeactivated):
            remove_ids.append(k)

        # Ловим все прочие исключения и отобржаем их на экран
        except Exception as e:
            logger.exception(e)

    # Если данные изменились - записываем изменения в файл
    if remove_ids:
        await remove_users(remove_ids)
    if migrate_ids:
        await migrate_users(migrate_ids)

    # Осталяем временную метку успешного обновления
    set_timetag(_TIMETAG_PATH, int(now.timestamp()))


# Запуск скрипта обновлений
# =========================

if __name__ == '__main__':
    executor.start(dp, main())
