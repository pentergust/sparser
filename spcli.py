"""Командный интерфейс для доступа к платформе расписания.

Позволяет напрямую взаимодействовать с генератором сообщений.
А также управлять хранилищем пользователя.

Author: Milinuri Nirvalen
Ver: v2 (sp v6.2)
"""

from datetime import datetime
from time import time
from typing import NamedTuple

import click

from sp.counter import CounterTarget, CurrentCounter
from sp.db import User
from sp.intents import Intent
from sp.platform import Platform
from sp.utils import get_str_timedelta
from sp.version import VersionInfo
from sp.view.messages import MessagesView, send_search_res

# Определение группы
# ==================


class AppContext(NamedTuple):
    """Контекст приложения."""

    platform: Platform
    user: User


pass_app = click.make_pass_decorator(AppContext)


@click.option(
    "--uid",
    "-u",
    type=str,
    default="Console",
    help="ID пользователя хранилища.",
)
@click.option(
    "--pid", "-p", type=int, default=0, help="ID платформы (хранилища)."
)
@click.group()
@click.pass_context
def cli(ctx: click.Context, uid: str, pid: int) -> None:
    """Скрипт для управления платформой расписания.

    Позволяет напрямую взаимодействовать с генератором сообщений
    и хранилищем пользователя.
    """
    platform = Platform(pid, "Console", VersionInfo("v2.1", 22, 6))
    platform.view = MessagesView()
    user = platform.get_user(uid)
    ctx.obj = AppContext(platform, user)


def _get_intent(
    ctx: click.Context, arg: click.Argument, value: str | None
) -> Intent | None:
    if value is None:
        return None
    return ctx.obj.platform.view.sc.parse_intent(value.split())


# Определение команд
# ==================


@cli.command()
@pass_app
def status(app: AppContext) -> None:
    """Состояние платформы и статуса."""
    click.echo(app.platform.status(app.user))


@cli.command()
@click.argument("intent", callback=_get_intent, required=False)
@pass_app
def iparse(app: AppContext, intent: Intent | None) -> None:
    """Проверка парсера намерений для конкретного расписания."""
    click.echo(intent)


@cli.command()
@click.argument("intent", required=False, callback=_get_intent)
@pass_app
def sc(app: AppContext, intent: Intent | None) -> None:
    """Расписание уроков для класса."""
    if intent is not None and intent.days:
        click.echo(app.platform.lessons(app.user, intent))
    else:
        click.echo(app.platform.today_lessons(app.user, intent))


@cli.command()
@pass_app
def users(app: AppContext) -> None:
    """Список всех пользователей платформы."""
    for k, v in app.platform.users.get_users().items():
        print(f"-- {k} / {v.cl} - {v.set_class}")


@cli.command()
@click.option(
    "--offset",
    help="С какого момента начинать отправлять записи об изменениях",
    type=click.DateTime(),
)
@click.argument("intent", callback=_get_intent, required=False)
@pass_app
def updates(
    app: AppContext, intent: Intent | None, offset: datetime | None
) -> None:
    """Записи об изменениях в расписании."""
    if offset is not None:
        offset = int(offset.timestamp())
    if intent is None:
        intent = Intent()
    for u in app.platform.view.sc.get_updates(intent, offset):
        print(app.platform.view.get_update(u))


@cli.command()
@click.argument("target", type=str)
@click.option("--intent", "-i", callback=_get_intent, default=Intent())
@click.option("--cabinets/--lessons", default=False)
@pass_app
def search(
    app: AppContext, target: str, intent: Intent, cabinets: bool
) -> None:
    """Глобальный поиск в расписании."""
    res = app.platform.view.sc.search(target, intent, cabinets)
    print(send_search_res(intent, res))


@cli.command()
@click.option("--intent", "-i", callback=_get_intent, required=False)
@click.argument(
    "counter",
    type=click.Choice(("cl", "days", "lessons", "cabinets")),
    default="lessons",
)
@click.argument(
    "target",
    type=click.Choice(("cl", "days", "lessons", "cabinets", "main", "none")),
    default="main",
)
@pass_app
def counter(
    app: AppContext, intent: Intent | None, counter: str, target: str
) -> None:
    """Подсчитывает элементы расписания."""
    cnt = CurrentCounter(app.platform.view.sc, intent or Intent())
    header = "✨ Счётчик"

    if counter == "cl":
        header += " по классам:"
        res = cnt.cl()
    elif counter == "days":
        header += " по дням:"
        res = cnt.days()
    elif counter == "lessons":
        header += " по урокам:"
        res = cnt.index()

    elif counter == "cabinets":
        header += " по кабинетам:"
        res = cnt.index(cabinets_mode=True)

    print(header)
    print(app.platform.counter(res, CounterTarget(target)))


# Пользователи расписания
# =======================


@cli.group()
def user() -> None:
    """Управление хранилищем пользователя."""


@user.command()
@pass_app
def get(app: AppContext) -> None:
    """Основная информация о пользователе."""
    create_delta = get_str_timedelta(int(time()) - app.user.data.create_time)
    if app.user.data.last_parse != 0:
        parse_delta = get_str_timedelta(int(time()) - app.user.data.last_parse)
    else:
        parse_delta = 0

    print(f"Создан: {app.user.data.create_time} ({create_delta})")
    print(f"Класс: {app.user.data.cl} (Установлен: {app.user.data.set_class})")
    print(f"Последняя проверка {app.user.data.last_parse} ({parse_delta})")
    print(f"Уведомления: {app.user.data.notifications}")
    print(f"Уведомлять: {','.join([str(x) for x in app.user.data.hours])}")


@user.command()
@pass_app
def count(app: AppContext) -> None:
    """Подсчитывает пользователей хранилища."""
    c_users = app.platform.users.count_users(app.platform.view.sc)

    if c_users.total > 0:
        active_pr = round((c_users.active / c_users.total) * 100, 2)
        notify_pr = round((c_users.notify / c_users.total) * 100, 2)
    else:
        active_pr = 0
        notify_pr = 0

    print(f"Всего: {c_users.total}")
    print(f"  | Активных: {c_users.active} ({active_pr}%)")
    print(f"  | С оповещениями: {c_users.notify} ({notify_pr}%)")

    print(f"по классам ({len(c_users.cl)}):")
    for k, v in c_users.cl.items():
        print(f"  | {k}: {v}")

    print(f"по оповещениям ({len(c_users.hour)}):")
    for k, v in c_users.hour.items():
        print(f"  | {k}: {v}")


@user.command()
@pass_app
def create(app: AppContext) -> None:
    """Добавляет нового/сбрасывает данные пользователя."""
    app.user.create()
    print(f"Create user: {user.uid}")


@user.command()
@pass_app
def remove(app: AppContext) -> None:
    """Удаляет пользователя."""
    app.user.remove()
    print(f"Remove user: {user.uid}")


@user.command()
@click.argument("cl", type=str)
@pass_app
def select(app: AppContext, cl: str) -> None:
    """Устанавливает класс по умолчанию для пользователя."""
    status = app.user.set_class(cl, app.platform.view.sc)
    if status:
        print(f"User {app.user.uid} set class {cl}")
    else:
        print(f"User {app.user.uid} {cl} not found?")


@user.command()
@click.argument("select", type=click.Choice(["on", "off"]))
@pass_app
def notify(app: AppContext, select: str) -> None:
    """Переключает режим отправки уведомлений."""
    if select == "on":
        app.user.set_notify_on()
    else:
        app.user.set_notify_off()
    print(f"User {app.user.uid} set notify {select}!")


# Оповещения пользователей
# ========================


@user.group()
def hours() -> None:
    """управляет часами оповещения расписания пользователя."""


@hours.command()
@pass_app
def reset(app: AppContext) -> None:
    """Сбрасывает часы отправки расписания."""
    app.user.reset_notify()


@hours.command()
@click.argument("hour", type=click.IntRange(6, 23))
@pass_app
def add(app: AppContext, hour: int) -> None:
    """Добавляет час отправки расписания."""
    app.user.add_notify_hour(hour)


@hours.command()
@click.argument("hour", type=click.IntRange(6, 23))
@pass_app
def remove(app: AppContext, hour: int) -> None:  # noqa: F811
    """Удаляет час отправки расписания."""
    app.user.remove_notify_hour(hour)


# Запуск скрипта
# ==============

if __name__ == "__main__":
    cli()
