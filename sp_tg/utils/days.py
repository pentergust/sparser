# Краткие названия дней недели
days_names = ("пн", "вт", "ср", "чт", "пт", "сб")


def get_relative_day(today: int, tomorrow: int) -> str:
    """Возвращает описание ближайшего дня недели.

    Используется в паре с функцией получение уроков на сегодня.
    Мспользуется для более точного отображения текста кнопки
    получения расписания на сегодня.

    :param today: Текущмй день недели
    :type today: int
    :param tomorrow: Следующий день недели
    :type tomorrow: int
    :return: Описание ближайшего дня недели
    :rtype: str
    """
    if today == tomorrow:
        relatove_day = "Сегодня"
    elif today+1 == tomorrow:
        relatove_day = "Завтра"
    else:
        relatove_day = days_names[tomorrow]
    return relatove_day