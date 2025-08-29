"""Скрипт для автоматической проверки расписания.

Работает в паре с Telegram ботом.
Данные для авторизации будут взяты из env файла.

- Проверяет пользователей.
- Обновляет расписание.
- Отправляет изменения в расписании пользователям.
- Рассылает расписание на сегодня/завтра пользователям.
- Удаляет пользователей.

TODO: Перейти на использование pydantic-settings
TODO: Сделать частью Telegram бота
TODO: Хранить метка обновления в redis

Author: Milinuri Nirvalen
Ver: 0.12.1 (sp v6.5, telegram v2.7)
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

_TIMETAG_PATH = Path("sp_data/last_update")
CHAT_MIGRATE_MESSAGE = (
    "⚠️ У вашего чата сменился ID.\nНастройки чата были перемещены."
)


def _week_markup(cl: str) -> InlineKeyboardMarkup:
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


def _updates_markup(cl: str) -> InlineKeyboardMarkup:
    """Клавиатура для сообщения с обновлением расписания.

    За подробностями обращайтесь к модулю ``sptg``.
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


def _update_last_check(path: Path, timestamp: int) -> None:
    """Оставляет временную метку последней проверки обновления."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write(str(timestamp))


async def _wrap_update(
    bot: Bot, hour: int, view: MessagesView, user: User
) -> None:
    try:
        logger.debug("Process {}", user)
        await process_update(bot, hour, view, user)

    except TelegramForbiddenError:
        await user.delete()

    except Exception as e:  # noqa: BLE001 чтобы процесс не останавливался
        logger.exception(e)


async def process_update(
    bot: Bot, hour: int, view: MessagesView, user: User
) -> None:
    """Проверяет обновления для одного пользователя (или чата).

    Отправляет расписание на сегодня/завтра в указанный час или
    список изменений в расписании, при наличии.
    """
    if user.get_hour(hour):
        logger.debug("Send schedule")
        await bot.send_message(
            user.id,
            text=view.today_lessons(await user.get_intent()),
            reply_markup=_week_markup(user.cl),
        )

    updates = await view.check_updates(user)
    if updates is None:
        return

    logger.debug("Send compare updates message")
    await bot.send_message(
        user.id, text=updates, reply_markup=_updates_markup(user.cl)
    )


async def main() -> None:
    """Запускает процесс проверки обновления.

    Проверяет для каждого пользователя наличие обновлений, а также
    отправляет по необходимости расписание на сегодня/завтра.
    """
    load_dotenv()
    bot = Bot(getenv("TELEGRAM_TOKEN"))  # pyright: ignore[reportArgumentType]
    view = MessagesView()

    logger.add("sp_data/updates.log")
    now = datetime.now(UTC)

    logger.info("Start of the update process...")
    tasks: list[asyncio.Future[None]] = []
    for user in await User.all():
        if not user.notify or not user.cl:
            continue

        tasks.append(
            asyncio.create_task(_wrap_update(bot, now.hour, view, user))
        )
    await asyncio.gather(*tasks)
    _update_last_check(_TIMETAG_PATH, int(now.timestamp()))


# Запуск скрипта обновлений
# =========================

if __name__ == "__main__":
    asyncio.run(main())
