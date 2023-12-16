"""
Командный интерфейc для доступа к генератору сообщений.

Author: Milinuri Nirvalen
Ver: 1.4 (sp 5.7)
"""

import argparse
from typing import Optional

from sp.counters import (cl_counter, days_counter, group_counter_res,
                         index_counter)
from sp.intents import Intent
from sp.messages import SPMessages, send_counter, send_search_res, send_update


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", help="Информация о парсере",
                        action="store_true")
    parser.add_argument("--set-class", help="Изменить класс пользователя")
    parser.add_argument("-i", "--intents", type=str,
                        help="Набор намерений для генератора сообщений")

    subparsers = parser.add_subparsers(dest="cmd", metavar="command")
    sp = subparsers.add_parser("sc", help="Расписание уроков")
    sp = subparsers.add_parser("updates", help="Изменения в расписании")

    sp = subparsers.add_parser("search", help="Поиск в расписании")
    sp.add_argument("-c", "--cabinets", help="Поиск по кабинетам",
                    action="store_true")
    sp.add_argument("target", help="Цель для поиска: урок, кабинет")

    sp = subparsers.add_parser("counter", help="Счётчик уроков/кабинетов")
    sp.add_argument("counter", help="Тип Счётчика", default="lessons",
                    choices=["cl", "days", "lessons", "cabinets"])
    sp.add_argument("target", help="Вторичный ключ для отображения",
                    default=None,
                    choices=["cl", "days", "lessons", "cabinets", "main"])
    return parser

def main() -> None:
    sp = SPMessages("Console")
    parser = get_parser()
    args = parser.parse_args()

    if not sp.user["set_class"]:
        print("[+] Please select your class!")
        print("[?] Run: --set-class CLASS for set your class let")

    # Статус генератора сообщений
    if args.version:
        print(sp.send_status())

    # Смена класса пользователя
    if args.set_class is not None:
        status = sp.set_class(args.set_class)
        if status:
            print(f"[*] User class let = {args.set_class}")
        else:
            print(f"[*] Class let: {', '.join(sorted(sp.sc.lessons))}")

    # Получение намерений для расписания
    if args.intents is not None:
        intent = Intent.parse(sp.sc, args.intents.split())
        print(intent)
    else:
        intent = Intent.new()

    # Получить расписание уроков
    if args.cmd == "sc":
        if intent.days:
            print(sp.send_lessons(intent))
        else:
            print(sp.send_today_lessons(intent))

    # Просмотреть обновления в расписании
    elif args.cmd == "updates":
        for u in sp.sc.get_updates(intent):
            print(send_update(u))

    # Поиск в расписании
    elif args.cmd == "search":
        res = sp.sc.search(args.target, intent, args.cabinets)
        print(send_search_res(intent, res))

    # Работа с счётчиками расписания
    elif args.cmd == "counter":
        header = "✨ Счётчик"

        if args.counter == "cl":
            header += " по классам:"
            res = cl_counter(sp.sc, intent)
        elif args.counter == "days":
            header += " по дням:"
            res = days_counter(sp.sc, intent)
        elif args.counter == "lessons":
            header += " по урокам:"
            res = index_counter(sp.sc, intent)
        elif args.counter == "cabinets":
            header += " по кабинетам:"
            res = index_counter(sp.sc, intent, cabinets_mode=True)

        groups = group_counter_res(res)
        print(header)
        print(send_counter(groups, target=args.target))

    else:
        print(sp.send_today_lessons(Intent.new()))

# Запуск скрипта
# ==============

if __name__ == '__main__':
    main()
