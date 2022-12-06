"""
Обёртка над ScheduleParser для отправки расписания в консоль.
Author: Milinuri Nirvalen
Ver: 3.1
"""

from sparser import SPMessages
from datetime import datetime
import argparse


days_str = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]
sp = SPMessages("Console")
days = []

# Определение аргументов коммандной строки
parser = argparse.ArgumentParser()

# Необязательные аргументы
parser.add_argument("-p", "--parse", action="store_true", 
                    help="Принудительное обновление расписания")
parser.add_argument("-c", "--class", dest="class_let",
                    help="Для какого класса применить действие")
parser.add_argument("-C", "--set-class", help="Изменить класс по умолчанию")
parser.add_argument("-d", "--days", nargs="*", default=[])
parser.add_argument("--cabinet")

# Команды парсеру
parser.add_argument("--changes", action="store_true",
                    help="Изменения в расписании")
parser.add_argument("--status", action="store_true",
                    help="Информация о парсере")
parser.add_argument("--search", help="Поиск по уроку", nargs="?")
parser.add_argument("--lessons", action="store_true", help="Самые частые уроки")
parser.add_argument("--cabinets", action="store_true", help="Самые частые кабинеты")
parser.add_argument("--week", action="store_true", help="Расписание на неделю")
parser.add_argument("--sc", action="store_false", help="Расписание уроков")

# Команда для отладки
parser.add_argument("--debug", help="Строка для отладки")


# Обработка аргументов
# ====================

args = parser.parse_args()

# Настройки поведения парсера
# ---------------------------

# Устанавливаем класс по умолчанию
if args.set_class:
    print(sp.set_class(args.set_class))

# Принудитекльно обновляем расписание
if args.parse:
    sp.get_schedule(True)

# Задаём дни недели
for x in args.days:
    if x == "сегодня":
        days.append(datetime.today().weekday())
        continue

    if x == "завтра":
        days.append(datetime.today().weekday()+1)

    for i, d in enumerate(days_str):
        if x.startswith(d):
            days.append(i)
            continue

# Команды парсера
# ---------------

# Получаем изменения в расписании
if args.changes:
    print(sp.send_sc_changes())

# Получаем информацию о парсере
if args.status:
    print(sp.print_status())

# Самые частые уроки и кабинеты
if args.lessons:
    print(sp.count_lessons(args.class_let))
elif args.cabinets:
    print(sp.count_cabinets(args.class_let))

# Поиск по предмета
elif args.search or args.cabinet:
    if args.cabinet:
        print(sp.search_cabinet(args.cabinet, lesson=args.search, 
                                days=days, class_let=args.class_let))
    else:
        print(sp.search_lesson(args.search, days=days, class_let=args.class_let))

# Расписание на неделю
elif args.week:
    print(sp.send_lessons([0, 1, 2, 3, 4, 5], args.class_let))

elif args.debug:
    if args.debug == "lindex":
        print(sp.get_sc_lindex())
    if args.debug == "cindex":
        print(sp.get_sc_cindex())

# Расписание уроков
elif args.sc:
    if days:
        print(sp.send_lessons(days, args.class_let))
    else:
        print(sp.send_today_lessons(args.class_let))


if not sp.user["set_class"]:
    print('\nПРЕДУПРЕЖДЕНИЕ: Не указан класс по умолчанию для Console')
