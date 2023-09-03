"""
Командный интерфейc для доступа к генератору сообщений.

Author: Milinuri Nirvalen
Ver: 1.2 (sp 5.4)
"""

from sp.counters import cl_counter
from sp.counters import days_counter
from sp.counters import group_counter_res
from sp.counters import index_counter
from sp.filters import construct_filters
from sp.filters import parse_filters
from sp.messages import SPMessages
from sp.messages import send_update
from sp.messages import send_counter
from sp.messages import send_search_res

import argparse

from typing import Optional

from loguru import logger


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd", metavar="command")
    subparsers.add_parser("status", help="Информация о парсере")

    sp = subparsers.add_parser("class", help="Изменить класс по умолчанию")
    sp.add_argument("cl", help="Целевой класс по умолчанию")

    sp = subparsers.add_parser("sc", help="Расписание уроков")
    sp.add_argument("filters", nargs="*",
                    help="Набор фильтров для уточнения расписания")

    sp = subparsers.add_parser("search", help="Поиск в расписании")
    sp.add_argument("-c", "--cabinets", help="Поиск по кабинетам",
                    action="store_true")
    sp.add_argument("target", help="Цель для поиска: урок, кабинет")
    sp.add_argument("filters", nargs="*",
                    help="Набор фильтров для уточнения результатов поиска")

    sp = subparsers.add_parser("counter", help="Счётчик уроков/кабинетов")
    sp.add_argument("counter", help="Тип Счётчика", default="lessons",
                    choices=["cl", "days", "lessons", "cabinets"])
    sp.add_argument("target", help="Вторичный ключ для отображения",
                    default=None,
                    choices=["cl", "days", "lessons", "cabinets", "main"])
    sp.add_argument("filters", nargs="*",
                    help="Набор фильтров для уточнения расписания")

    sp = subparsers.add_parser("updates", help="Изменения в расписании")
    sp.add_argument("filters", nargs="*",
                    help="Набор фильтров для уточнения расписания")
    return parser

def main() -> None:
    sp = SPMessages("Console")
    parser = get_parser()
    args = parser.parse_args()

    if args.cmd == "status":
        print(sp.send_status())

    elif args.cmd == "class":
        sp.set_class(args.cl)
        logger.info("User class let = {}", args.cl)

    elif args.cmd == "sc":
        flt = parse_filters(sp.sc, args.filters)
        if flt.days:
            print(sp.send_lessons(flt))
        else:
            print(sp.send_today_lessons(flt))

    elif args.cmd == "search":
        flt = parse_filters(sp.sc, args.filters)
        res = sp.sc.search(args.target, flt, args.cabinets)
        print(send_search_res(flt, res))

    elif args.cmd == "counter":
        flt = parse_filters(sp.sc, args.filters)
        header = "✨ Счётчик"

        if args.counter == "cl":
            header += " по классам:"
            res = cl_counter(sp.sc, flt)
        elif args.counter == "days":
            header += " по дням:"
            res = days_counter(sp.sc, flt)
        elif args.counter == "lessons":
            header += " по урокам:"
            res = index_counter(sp.sc, flt)
        elif args.counter == "cabinets":
            header += " по кабинетам:"
            res = index_counter(sp.sc, flt, cabinets_mode=True)

        groups = group_counter_res(res)
        print(header)
        print(send_counter(groups, target=args.target))

    elif args.cmd == "updates":
        flt = parse_filters(sp.sc, args.filters)
        for u in sp.sc.get_updates(flt):
            print(send_update(u))

    else:
        flt = construct_filters(sp.sc)
        print(sp.send_today_lessons(flt))

    if not sp.user["set_class"]:
        logger.warning("Please select your class!")
        logger.warning("Run \"class --help\" for more information")


# Запуск скрипта
# ==============

if __name__ == '__main__':
    main()
