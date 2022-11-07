"""
Плагин Чио для отправки школьного расписания.
Обёртка над ScheduleParser
Author: Milinuri Nirvalen
Ver: sp 1.6
"""

from core import Plugin
from tparser.tparser import ScheduleParser

from datetime import datetime


p = Plugin('Расписание', desc='Отправляет вам расписание уроков')

days_str = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]


@p.command("уроки", usage="[class_let; day] расписание на день")
async def lessons(event, ctx):
    sp = ScheduleParser(str(event.get("to.id")))
    class_let = None
    days = []
    
    for x in ctx.args:
        x = x.lower()

        if x in sp.schedule:
            class_let = x

        for i, d in enumerate(days_str):
            if x.startswith(d) and i not in days:
                days.append(i) 

        if x == "сегодня":
            days.append(datetime.today().weekday())

    if days:
        res = sp.print_lessons(days, class_let)
    else:
        res = sp.print_today_lessons(class_let)

    await ctx.message(res)
    

@p.command("расписание", usage= "[class_let] расписание на неделю")
async def schedule(event, ctx):
    sp = ScheduleParser(str(event.get("to.id")))
    await ctx.message(sp.print_lessons([0, 1, 2, 3, 4, 5], ctx.sargs.lower()))


@p.command('класс', usage='[class_let] сменить класс по умолчанию')
async def set_class(event, ctx):
    sp = ScheduleParser(str(event.get('to.id')))
    await ctx.message(sp.set_class(ctx.sargs.lower()))

