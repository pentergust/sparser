"""
Командный интерфейc для доступа к генератору сообщений.

Author: Milinuri Nirvalen
Ver: 1.0 (sp 5.0)
"""

from sp.filters import Filters
from sp.spm import SPMessages
from sp.spm import send_update

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
    sp.add_argument("cl", nargs="?", default=None, help="Сортировка по классу")
    sp.add_argument("-c", "--cabinets", help="Сортировака по кабинетам",
                    action="store_true")

    sp = subparsers.add_parser("updates", help="Изменения в расписании")
    sp.add_argument("filters", nargs="*",
                    help="Набор фильтров для уточнения расписания")
    return parser

def main() -> None:
    sp = SPMessages("Console")
    flt = Filters(sp.sc)
    parser = get_parser()
    args = parser.parse_args()

    if args.cmd == "status":
        print(sp.send_status())

    elif args.cmd == "class":
        sp.set_class(args.cl)
        logger.info("User class let = {}", args.cl)

    elif args.cmd == "sc":
        flt.parse_args(args.filters)
        if flt.days:
            print(sp.send_lessons(flt))
        else:
            print(sp.send_today_lessons(flt))

    elif args.cmd == "search":
        flt.parse_args(args.filters)
        if args.cabinets:
            print(sp.search_cabinet(args.target, flt))
        else:
            print(sp.search_lesson(args.target, flt))

    elif args.cmd == "counter":
        print(sp.count_lessons(cabinets=args.cabinets, cl=args.cl))

    elif args.cmd == "updates":
        flt.parse_args(args.filters)
        for u in sp.sc.get_updates(flt):
            print(send_update(u))

    else:
        print(sp.send_today_lessons(flt))


    if not sp.user["set_class"]:
        logger.warning("Please select your class!")
        logger.warning("Run \"class --help\" for more information")


# Запуск скрипта
# ==============

if __name__ == '__main__':
    main()
