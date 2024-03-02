"""Загружает все дополнительные обработчики бота.

Дополнительные обработчики используются для расширения базового
функционала бота, а также для группировки исходного кода бота
по функционалу.
"""

# Импортируем все обработчики
from sp_tg.handlers import (intents, notify, request, schedule, tutorial,
                            updates, set_class, counters)

# Список всех экземпляров роутеров обработчиков
routers = (
    counters.router,
    intents.router,
    notify.router,
    schedule.router,
    set_class.router,
    tutorial.router,
    updates.router,

    # Загружается последним т.к. содержит обработчики всех сообщений
    request.router
)

__all__ = ["routers"]
