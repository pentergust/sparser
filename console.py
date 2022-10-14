"""
Лёгкая обёртка над ScheduleParser для получения расписания в консоль.
Author: Milinuri Nirvalen
Ver: 1.1
"""

from tparser import ScheduledParser

import sys
from datetime import datetime

helptext = """Использование console.py [Action] [Args]

ACTION:
    help  - Вывести справку по командам
    parse - Проверка работы парсера расписания
    debug - Получить информацию о расписании
    class [class_let] - Изменить класс по умолчанию 
    lessons [today] [class_let] - Получить расписание для класса

ARGS:
    class_let - Буква класса в фомрате "9a"
    today     - Название дня недели (понедельник - суббота)
"""

days = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]


def main(args):
    action = None
    class_let = None
    today = datetime.today().weekday()+1
    sp = ScheduledParser("Console")
            
    # Обработка аргументов
    # ====================

    for x in args:

        if x in sp.schedule["schedule"]:
            class_let = x.lower()
            continue

        if x == "сегодня":
            today = datetime.today().weekday()
            continue

        for i, d in enumerate(days):
            if x.startswith(d):
                today = i 
                continue

        # Вывод справка по использованию
        if x == "help":
            print(helptext)

        # Команды отладки
        if x == "parse":
            sp.get_schedule(True)

        if x == "debug":
            print(sp.schedule)

        if x in ["class", "lessons"]:
            action = x


    # Исполненение команд
    # ===================
        
    if action == "class":
        print(sp.set_class(class_let))
    elif action == "lessons":
        print(sp.get_lessons(today))
    elif action is None:
        print(helptext)



if __name__ == '__main__':
    main(sys.argv[1:])
