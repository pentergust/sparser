"""Загружает все дополнительные обработчики бота.

Дополнительные обработчики используются для расширения базового
функционала бота, а также для группировки исходного кода бота
по функционалу.
"""

from tg.handlers import (
    counters,
    errors,
    intents,
    menu,
    notify,
    request,
    schedule,
    set_class,
    updates,
)

routers = (
    counters.router,
    errors.router,
    intents.router,
    menu.router,
    notify.router,
    schedule.router,
    set_class.router,
    updates.router,
    request.router,
)

__all__ = ("routers",)
