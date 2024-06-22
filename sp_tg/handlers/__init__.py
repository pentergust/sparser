"""Загружает все дополнительные обработчики бота.

Дополнительные обработчики используются для расширения базового
функционала бота, а также для группировки исходного кода бота
по функционалу.
"""

# Импортируем все обработчики
from sp_tg.handlers import (
    counters,
    intents,
    notify,
    request,
    schedule,
    set_class,
    tutorial,
    updates,
)

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
