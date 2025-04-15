"""Скрипт для автоматической проверки расписания.

Работает в паре с Telegram ботом.
Данные для авторизации будут взяты из env файла.

- Проверяет пользователей.
- Обновляет расписание.
- Отправляет изменения в расписании пользователям.
- Рассылает расписание на сегодня/завтра пользователям.
- Удаляет пользователей.

Author: Milinuri Nirvalen
Ver: 0.12 (sp v6.5, telegram v2.7)
"""

import asyncio
from datetime import UTC, datetime
from os import getenv
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from loguru import logger

from sp.db import User
from sp.view.messages import MessagesView

# Запуск платформы и TG бота
# ==========================

_TIMETAG_PATH = Path("sp_data/last_update")
# Максимальная длинна отправляемого сообщения для Telegram и Вконтакте
_MAX_UPDATE_MESSAGE_LEN = 4000

# Если данные мигрировали в следствии
CHAT_MIGRATE_MESSAGE = (
    "⚠️ У вашего чата сменился ID.\nНастройки чата были перемещены."
)

# Функции для сбора клавиатур
# ===========================


def get_week_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Получает клавиатуру для расписание на неделю.

    За подробностями обращайтесь к модулю ``sptg``.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠Домой", callback_data="home"),
                InlineKeyboardButton(
                    text="На неделю", callback_data=f"sc:{cl}:week"
                ),
                InlineKeyboardButton(
                    text="▷", callback_data=f"select_day:{cl}"
                ),
            ]
        ]
    )


def get_updates_keyboard(cl: str) -> InlineKeyboardMarkup:
    """Клавиатура сообщения с обновлением.

    Данная клавиатура будет отправляться в месте с сообщением об
    изменениях в расписании.
    Она содержит в себе ссылки на все основные разделы, которые нужны
    при просмотре сообщения с изменением:

    - Вернуться домой.
    - Перейти к списку изменений.
    - Получить расписание на сегодня/завтра.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◁", callback_data="home"),
                InlineKeyboardButton(
                    text="Изменения", callback_data=f"updates:last:0:{cl}:"
                ),
                InlineKeyboardButton(
                    text="Уроки", callback_data=f"sc:{cl}:today"
                ),
            ]
        ]
    )


# Функции для обработки списка пользователей
# ==========================================


async def process_update(
    bot: Bot, hour: int, view: MessagesView, user: User
) -> None:
    """Проверяет обновления для одного пользователя (или чата).

    Отправляет расписание на сегодня/завтра в указанный час или
    список изменений в расписании, при наличии.
    """
    # Рассылка расписания в указанные часы
    if user.get_hour(hour):
        logger.info("Send schedule")
        await bot.send_message(
            user.id,
            text=view.today_lessons(await user.get_intent()),
            reply_markup=get_week_keyboard(user.cl),
        )

    # Отправляем уведомления об обновлениях
    updates = await view.check_updates(user)
    if updates is None:
        return

    logger.info("Send compare updates message")

    await bot.send_message(
        user.id, text=updates, reply_markup=get_updates_keyboard(user.cl)
    )


def set_timetag(path: Path, timestamp: int) -> None:
    """Оставляет временную метку последней проверки обновления.

    После успешной работы скрипта записывает в файл временную метку.
    Метка может использоваться для проверки работоспособности
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
    """Запускает процесс проверки обновления.

    Проверяет для каждого пользователя наличие обновлений, а также
    отправляет по необходимости расписание на сегодня/завтра.
    """
    load_dotenv()
    bot = Bot(getenv("TELEGRAM_TOKEN"))
    view = MessagesView()

    logger.add("sp_data/updates.log")
    now = datetime.now(UTC)

    logger.info("Start of the update process...")
    for user in await User.all():
        # Если у пользователя отключены уведомления или не указан
        # класс по умолчанию -> пропускаем.
        if not user.notify or user.cl == "":
            continue

        try:
            logger.debug("Process {}", user)
            await process_update(bot, now.hour, view, user)

        # Если что-то произошло с пользователем:
        # Заблокировал бота, исключил из чата, исчез сам ->
        # Удаляем пользователя (чат) из базы.
        except TelegramForbiddenError:
            await user.delete()

        # Ловим все прочие исключения и отображаем их на экран
        except Exception as e:
            logger.exception(e)

    set_timetag(_TIMETAG_PATH, int(now.timestamp()))


# Запуск скрипта обновлений
# =========================

if __name__ == "__main__":
    asyncio.run(main())
