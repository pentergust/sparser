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
    counters.router,  # Счётчики расписания. Считаются количество элементов.
    intents.router,  # Редактор пользовательских намерений.
    notify.router,  # Рассылка расписания и изменения в нём.
    schedule.router,  # Получение расписания, один из главных обработчиков.
    set_class.router,  # Выбор класса пользователя
    tutorial.router,  # справка как использовать бота
    updates.router,  # Просмотр списка изменений в расписании
    request.router,  # Запросы к расписанию
)

__all__ = ("routers",)
