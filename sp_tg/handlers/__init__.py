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
# Вы можете и самостоятельно отключать не нужным вам обработчики
# Однако помните что пункты меню будут на месте.
# Только они останутся безответными.
routers = (
    # Счётчики расписания. Считаются количество элементов.
    counters.router,

    # Настройка пользовательских намерений
    intents.router,

    # Настройка уведомлений.
    notify.router,

    # Получение расписания, один из главных обработчиков.
    schedule.router,

    # Настрока класса пользователей
    set_class.router,

    # Маленькая справка как использовать бота. Легко отключить.
    tutorial.router,

    # Просмотр списка изменений в расписании
    updates.router,

    # Загружается последним т.к. содержит обработчики всех сообщений
    request.router
)

__all__ = ("routers",)
