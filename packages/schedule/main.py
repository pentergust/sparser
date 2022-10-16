# ===========================
from core import Plugin

from tparser.tparser import ScheduledParser

from datetime import datetime
# ===========================

p = Plugin('Расписание', desc='Отправляет вам расписание уроков')


days = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]
s_days = ["Понедельник", "Вторник", "Среда", "четверг", "Пятницу", "Субботу"]

@p.command("уроки", usage="[class_let] [day] уроки на день для класса")
async def lessons(event, ctx):
    sp = ScheduledParser(str(event.get('to.id')))

    today = datetime.today().weekday()+1
    class_let = sp.user["class_let"]

    for x in ctx.args:
        x = x.lower()

        if x in sp.schedule["schedule"]:
            class_let = x

        for i, d in enumerate(days):
            if x.startswith(d):
                today = i 
                continue

        if x == 'сегодня':
            today = datetime.today().weekday()

    if today > 5:
        today = 0
        
    res = sp.get_lessons(today, class_let)
    await ctx.message(res)

@p.command('класс', usage='[класс] сменить класс по умолчанию')
async def set_class(event, ctx):
    sp = ScheduledParser(str(event.get('to.id')))
    await ctx.message(sp.set_class(ctx.sargs.lower()))
