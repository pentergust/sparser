"""
Командный интерфейc для доступа к генератору сообщений.

Author: Milinuri Nirvalen
Ver: 1.5 (sp 6)
"""

from time import time
import argparse
from typing import Optional

from sp.counters import (cl_counter, days_counter, group_counter_res,
                         index_counter)
from sp.intents import Intent
from sp.messages import SPMessages, send_counter, send_search_res, send_update
from sp.users import FileUserStorage, User, UserData, CountedUsers
from sp.utils import get_str_timedelta

def get_parser() -> argparse.ArgumentParser:
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
    sp.add_argument("target", help="Вторичный ключ для отображения",
                    default=None,
                    choices=["cl", "days", "lessons", "cabinets", "main"])

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
    parser = get_parser()
    args = parser.parse_args()

    user_storage = FileUserStorage(args.ustorage)
    user = User(user_storage, args.uid)
    sp = SPMessages(args.uid)


    # Обработка генератора сообщений
    # ==============================

    # Статус генератора сообщений
    if args.version:
        print(sp.send_status())

    # Получение намерений для расписания
    if args.intents is not None:
        intent = sp.sc.parse_intent(args.intent.split())
    else:
        intent = Intent()

    # Обработка пользователей
    # =======================

    if args.cmd == "user":
        # Получает данные пользователя
        if args.action == "get":
            create_delta = get_str_timedelta(int(time()) - user.data.create_time)
            if user.data.last_parse != 0:
                parse_delta = get_str_timedelta(int(time()) - user.data.last_parse)
            else:
                parse_delta = 0

            print(f"Создан: {user.data.create_time} ({create_delta})")
            print(f"Класс: {user.data.cl} (Установлен: {user.data.set_class})")
            print(f"Последняя проверка {user.data.last_parse} ({parse_delta})")
            print(f"Уведомления: {user.data.notifications}")
            print(f"Уведомлять: {','.join([str(x) for x in user.data.hours])}")

        # Счаитет пользователей в базе данных
        elif args.action == "count":
            counted_users = user_storage.count_users(sp.sc)
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
            status = user.set_class(args.value, sp.sc)
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
        elif args.action == "hourremove":
            user.reset_notify()
            print(f"Reset notify hours for {user.uid}")

        else: # artion == "users"
            for k, v in user_storage.get_users().items():
                print(f"-- {k} / {v.cl} - {v.set_class}")

    # # Получить расписание уроков
    elif args.cmd == "sc":
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
        print(sp.send_today_lessons(intent))

# Запуск скрипта
# ==============

if __name__ == '__main__':
    main()
