"""Командный интерфейc для доступа к генератору сообщений.

Author: Milinuri Nirvalen
Ver: 1.6.1 (sp v6)
"""

import argparse
from time import time

from sp.counters import CounterTarget
from sp.intents import Intent
from sp.messages import SPMessages, send_search_res
from sp.platform import Platform
from sp.text_counter import TextCounter
from sp.utils import get_str_timedelta


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", help="Информация о парсере",
        action="store_true"
    )
    parser.add_argument("-i", "--intents", type=str,
        help="Набор намерений для генератора сообщений"
    )

    # Настройки хранилища пользователя
    parser.add_argument("-u", "--uid", type=str,
        help="User ID пользователя с котороым работаем",
        default="Console"
    )

    parser.add_argument("-s", "--ustorage", type=str,
        help="Путь к файлу с пользователями",
        default="sp_data/users/cli.json"
    )

    # Главные команды парсера
    subparsers = parser.add_subparsers(dest="cmd", metavar="command")
    sp = subparsers.add_parser("sc", help="Расписание уроков")
    sp = subparsers.add_parser("updates", help="Изменения в расписании")

    # Поисковая система по расписнаию
    sp = subparsers.add_parser("search", help="Поиск в расписании")
    sp.add_argument("-c", "--cabinets", help="Поиск по кабинетам",
                    action="store_true")
    sp.add_argument("target", help="Цель для поиска: урок, кабинет")

    # Работа с счётчиками расписания
    sp = subparsers.add_parser("counter", help="Счётчик уроков/кабинетов")
    sp.add_argument("counter", help="Тип Счётчика", default="lessons",
                    choices=["cl", "days", "lessons", "cabinets"])
    sp.add_argument(
        "target", help="Вторичный ключ для отображения",
        type=CounterTarget, default=CounterTarget.NONE, nargs='?'
    )

    # Аргументы хранилища пользователей
    # =================================

    up = subparsers.add_parser("user", help="Взаимодействие с пользователем")
    up.add_argument("action", help="Что нужно сделать с пользователем",
        default="users", nargs='?',
        choices=[
            "get", "count", "users", "create", "remove", "class", "notify",
            "houradd", "hourremove", "hourreset"
        ]
    )
    up.add_argument("value", help="Дополнительный аргумент команды",
        default=None, nargs='?',
    )

    return parser

def main() -> None:
    """Запускает обработку аргументов командной строки."""
    parser = _get_parser()
    args = parser.parse_args()

    platform = Platform(0, "Console", "v1.6", 1)
    platform.view = SPMessages()
    user = platform.get_user(args.uid)


    # Обработка генератора сообщений
    # ==============================

    # Статус генератора сообщений
    if args.version:
        print(platform.view.send_status(user))

    # Получение намерений для расписания
    if args.intents is not None:
        intent = platform.view.sc.parse_intent(args.intent.split())
    else:
        intent = Intent()

    # Обработка пользователей
    # =======================

    if args.cmd == "user":
        # Получает данные пользователя
        if args.action == "get":
            create_delta = get_str_timedelta(
                int(time()) - user.data.create_time
            )
            if user.data.last_parse != 0:
                parse_delta = get_str_timedelta(
                    int(time()) - user.data.last_parse
                )
            else:
                parse_delta = 0

            print(f"Создан: {user.data.create_time} ({create_delta})")
            print(f"Класс: {user.data.cl} (Установлен: {user.data.set_class})")
            print(f"Последняя проверка {user.data.last_parse} ({parse_delta})")
            print(f"Уведомления: {user.data.notifications}")
            print(f"Уведомлять: {','.join([str(x) for x in user.data.hours])}")

        # Счаитет пользователей в базе данных
        elif args.action == "count":
            counted_users = platform.users.count_users(platform.view.sc)
            print(f"Active: {counted_users.active}")
            print(f"Class counter ({len(counted_users.cl)}):")
            for k, v in counted_users.cl.items():
                print(f"-- {k}: {v}")

        # Создать пользователя
        elif args.action == "create":
            user.create()
            print(f"Create user: {user.uid}")

        # Удалить пользователя
        elif args.action == "remove":
            user.remove()
            print(f"Remove user: {user.uid}")

        # Установить класс пользователю
        elif args.action == "class":
            status = user.set_class(args.value, platform.view.sc)
            if status:
                print(f"User {user.uid} set class {args.value}")
            else:
                print(f"User {user.uid} error set {args.value} class")

        # Настройка отправки уведомлений
        elif args.action == "notify":
            if args.value == "on":
                user.set_notify_on()
                print(f"User {user.uid} set notify on!")
            elif args.value == "off":
                user.set_notify_off()
                print(f"User {user.uid} set notify off!")
            else:
                print("Choice value between on and off.")

        # Добавить рассылку в указанный час
        elif args.action == "houradd":
            if args.value.isdigit():
                hour = max(min(int(args.value), 20), 6)
                user.add_notify_hour(hour)
                print(f"{user.uid}: add notify at {hour}:00.")
            else:
                print("Please enter a hour (6-20) in value.")

        # Удаляет рассылку в указанный час
        elif args.action == "hourremove":
            if args.value.isdigit():
                hour = max(min(int(args.value), 20), 6)
                user.remove_notify_hour(hour)
                print(f"{user.uid}: remove notify at {hour}:00.")
            else:
                print("Please enter a hour (6-20) in value.")

        # Сбрасывает рассылку уведомлений
        elif args.action == "hourreset":
            user.reset_notify()
            print(f"Reset notify hours for {user.uid}")

        else: # artion == "users"
            for k, v in platform.users.get_users().items():
                print(f"-- {k} / {v.cl} - {v.set_class}")

    # # Получить расписание уроков
    elif args.cmd == "sc":
        if intent.days:
            print(platform.view.send_lessons(intent, user))
        else:
            print(platform.view.send_today_lessons(intent), user)

    # Просмотреть обновления в расписании
    elif args.cmd == "updates":
        for u in platform.view.sc.get_updates(intent):
            print(platform.view.send_update(u))

    # Поиск в расписании
    elif args.cmd == "search":
        res = platform.view.sc.search(args.target, intent, args.cabinets)
        print(send_search_res(intent, res))

    # Работа с счётчиками расписания
    elif args.cmd == "counter":
        cnt = TextCounter(platform.view.sc)
        header = "✨ Счётчик"

        if args.counter == "cl":
            header += " по классам:"
            res = cnt.cl(intent, args.target)
        elif args.counter == "days":
            header += " по дням:"
            res = cnt.days(intent, args.target)
        elif args.counter == "lessons":
            header += " по урокам:"
            res = cnt.index(intent, target=args.target)

        elif args.counter == "cabinets":
            header += " по кабинетам:"
            res = cnt.index(intent, cabinets_mode=True, target=args.target)

        print(header)
        print(res)

    else:
        print(platform.view.send_today_lessons(intent, user))


# Запуск скрипта
# ==============

if __name__ == '__main__':
    main()
