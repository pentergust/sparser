"""
Обёртка над ScheduleParser для отправки расписания в консоль.
Author: Milinuri Nirvalen
Ver: 2.4.1
"""

from tparser import ScheduleParser

from datetime import datetime
import sys

helptext = """Использование console.py [Action] [Args]

ACTION:
    help  - Справкв по командам
    parse - Проверка работы парсера расписания
    lindex - Получить индекс уроков
    debug - Переработанное расписание
    
    class [class_let] - Изменить класс по умолчанию 
    week [class_let]  - Получить расписание уроков на неделю
    lessons [Args] - Получить расписание уроков
    status - Статус ScheduleParser
    count [class_let] - Самые частые уроки
    search [lesson] - Когда и для кого будет урок
    changes - Просмотреть изменения в расписании

ARGS:
    class_let - Класс в фомрате "9a"
    today     - Название дня недели (понедельник - суббота), "сегодня", "завтра")
"""

days_str = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]


def main(args):
    sp = ScheduleParser("Console")
    lindex = sp.get_lessons_index()

    action = "lessons"
    class_let = None
    days = []
    lesson = "aaa"


    # Обработка аргументов
    # ====================

    for x in args:    
        x = x.lower()

        # Смена класса для выполнения действия
        if x in sp.lessons:
            class_let = x.lower()
            continue

        if x in lindex:
            lesson = x
            continue

        # Устанавливаем день
        if x == "сегодня":
            days.append(datetime.today().weekday())
            continue

        if x == "завтра":
            days.append(datetime.today().weekday()+1)

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

        if x == "status":
            print(sp.print_status())

        if x == "lindex":
            print(sp.get_lessons_index())

        if x == "changes":
            print(sp.print_sc_changes())

        if x in ["class", "lessons", "week", "count", "search"]:
            action = x


    # Исполненение команд
    # ===================
        
    if action == "class":
        print(sp.set_class(class_let))
    
    elif action == "lessons":
        if days:
            print(sp.print_lessons(days, class_let))
        else:
            print(sp.print_today_lessons(class_let))


    elif action == "week":
        print(sp.print_lessons([0, 1, 2, 3, 4, 5], class_let))

    elif action == "count":
        print(sp.count_lessons(class_let))

    elif action == "search":
        print(sp.search_lesson(lesson))

    else:
        print(helptext)

    if not sp.user["set_class"]:
        print('\nПРЕДУПРЕЖДЕНИЕ: Укажите ваш класс по умолчанию')

if __name__ == '__main__':
    main(sys.argv[1:])
