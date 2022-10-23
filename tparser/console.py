"""
Обёртка над ScheduleParser для получения расписания в консоль.
Author: Milinuri Nirvalen
Ver: 1.4.2
"""

from tparser import ScheduledParser

from datetime import datetime
import sys

helptext = """Использование console.py [Action] [Args]

ACTION:
    help  - Справкв по командам
    parse - Проверка работы парсера расписания
    debug - Информацию о расписании
    class [class_let] - Изменить класс по умолчанию 
    schedule [class_let]  - Получить расписание уроков на неделю
    lessons [Args] - Получить расписание на день

ARGS:
    class_let - Класс в фомрате "9a"
    today     - Название дня недели (понедельник - суббота)
"""

days_str = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]


def main(args):
    sp = ScheduledParser("Console")

    action = "lessons"
    class_let = None
    days = []
            
    # Обработка аргументов
    # ====================

    for x in args:    
    
        # Смена класса для выполнения действия
        if x in sp.schedule["schedule"]:
            class_let = x.lower()
            continue

        # Устанавливаем день
        if x == "сегодня":
            days.append(datetime.today().weekday())
            continue

        for i, d in enumerate(days_str):
            if x.startswith(d):
                days.append(i)
                continue
              
        # Вывод справка по использованию
        if x == "help":
            print(helptext)

        # Команды отладки
        if x == "parse":
            sp.get_schedule(True)

        if x == "debug":
            print(sp.schedule)

        if x in ["class", "lessons", "schedule"]:
            action = x


    # Исполненение команд
    # ===================
        
    if action == "class":
        print(sp.set_class(class_let))
    
    elif action == "lessons":
        if not days:
            days = [datetime.today().weekday()+1]
        
        print(sp.get_lessons(days, class_let))

    elif action == "schedule":
        print(sp.get_lessons([0, 1, 2, 3, 4, 5], class_let))

    else:
        print(helptext)



if __name__ == '__main__':
    main(sys.argv[1:])
