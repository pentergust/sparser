# ===========================
from core import Plugin
from tparser.tparser import ScheduledParser

from datetime import datetime
# ===========================

p = Plugin('Расписание', desc='Отправляет вам расписание уроков')

days = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]


@p.command("уроки", usage="[class_let, day...] расписание на день")
async def lessons(event, ctx):
    sp = ScheduledParser(str(event.get("to.id")))
    class_let = None
    days = []
    
    for x in ctx.args:
        x = x.lower()

        if x in sp.schedule["schedule"]:
            class_let = x

        for i, d in enumerate(days):
            if x.startswith(d) and i not in days:
                days.append(i) 

        if x == "сегодня":
            days.append(datetime.today().weekday())

    if not days:
        days = datetime.today().weekday()

    await ctx.message(sp.get_lessons(days, class_let))


@p.command("расписание", usage= "[class_let] расписание на неделю")
async def schedule(event, ctx):
    sp = ScheduledParser(str(event.get("to.id")))
    class_let = None

    if ctx.sargs.lower() in sp.schedule["schedule"]:
        class_let = sp.schedule["schedule"][ctx.sargs]

    await ctx.message(sp.get_lessons([0, 1, 2, 3, 4, 5], class_let))


@p.command('класс', usage='[класс] сменить класс по умолчанию')
async def set_class(event, ctx):
    sp = ScheduledParser(str(event.get('to.id')))
    await ctx.message(sp.set_class(ctx.sargs.lower()))

