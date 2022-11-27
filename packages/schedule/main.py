"""
Плагин Чио для отправки школьного расписания.
Обёртка над ScheduleParser

Author: Milinuri Nirvalen
Ver: sp 2.4.1
"""

from core import Plugin, Config
from sparser.sparser import ScheduleParser

from datetime import datetime


p = Plugin('Расписание', desc='Отправляет вам расписание уроков')

days_str = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]
set_class_message = f"""\n\n⚠️ Поажлуйста, укажите класс по умолчанию: /класс [Ваш класс]"""

config_path = "data/sparser_autopost.toml"
user_base = {"autopost_hour":17, "hour":0, "day":0}


@p.eventHandler('after')
async def _(event, ctx):
    p.log('Check sparser_autopost')

    c = Config(filepath=config_path)
    day = int(datetime.today().strftime('%j'))
    hour = datetime.now().hour
    updated = False
    autopost_targets = []

    # Проверка таймеров
    # -----------------

    for k, v in c.file_data.items():
        if day != v["day"] and hour >= v["autopost_hour"]:
            updated = True
            autopost_targets.append(k)
            v["day"] = day
            v["hour"] = hour
            c.file_data[k] = v

    if updated:
        c.save()
        p.log("Save autopost file")


    # Отправка расписания
    # ===================

    for x in autopost_targets:
        sp = ScheduleParser(x)
        await ctx.message(sp.print_today_lessons(), peer_id=x)


# Настройка автопоста
# ===================

@p.command("автопост", usage="настроить автопост")
async def autopost(event, ctx):
    uid = str(event.get("to.id"))
    c = Config(filepath=config_path)

    res = "Автопост: "

    if ctx.sargs.lower().startswith("выкл"):
        if uid in c.file_data:
            del c.file_data[uid]
            c.save()
    
    elif ctx.sargs.isdigit():
        user = c.file_data.get(uid, user_base)
        user["autopost_hour"] = min(max(int(ctx.sargs), 0), 23)
        c.file_data[uid] = user
        c.save()

    autopost_status = ""
    autopost_command = ""

    if uid not in c.file_data:
        res += f'🔕 Выключен'
        autopost_command = "\n🔷 /автопост [час] - включить автопост"
    else:
        res += f"🔔 В {c.file_data[uid]['autopost_hour']}:00"
        autopost_command = "\n🔶 /автопост выкл - выключить автопост"

    res += "\n\nВ указанное вами время вы получите расписание автоматически."
    res += "\n⚠️ Уведомления приходят с запозданием (могут и не придти), не полагайтесь сильно на них."
    res += autopost_command

    await ctx.message(res)


# Основные команды
# ================

@p.command('класс', usage='[class_let] сменить класс по умолчанию')
async def setClass(event, ctx):
    sp = ScheduleParser(str(event.get('to.id')))
    await ctx.message(sp.set_class(ctx.sargs.lower()))


@p.command("уроки", usage="[class_let; day] расписание на день")
async def lessons(event, ctx):
    uid = str(event.get("to.id"))
    sp = ScheduleParser(uid)
    lindex = sp.get_lessons_index()
    
    # Обновление данных автопоста
    # ---------------------------

    c = Config(filepath=config_path)
    if uid in c.file_data:
        c.file_data[uid]["day"] = int(datetime.today().strftime('%j'))
        c.file_data[uid]["hour"] = datetime.now().hour
        c.save()


    # Обработка аргументов
    # --------------------

    class_let = None
    lesson = None
    days = []
    
    for x in ctx.args:
        x = x.lower()

        if x in sp.lessons:
            class_let = x

        if x in lindex:
            lesson = x

        for i, d in enumerate(days_str):
            if x.startswith(d) and i not in days:
                days.append(i) 

        if x == "сегодня":
            days.append(datetime.today().weekday())

        if x == "завтра":
            days.append(datetime.today().weekday()+1)


    # Сборка сообщения
    # ----------------

    if lesson:
        res = sp.search_lesson(lesson, days)
    elif days:
        res = sp.print_lessons(days, class_let)
    else:
        res = sp.print_today_lessons(class_let)

    if not class_let and not sp.user["set_class"]:
        res += set_class_message

    await ctx.message(res)
  
@p.command("расписание", usage= "[class_let] расписание на неделю")
async def schedule(event, ctx):
    uid = str(event.get("to.id"))
    sp = ScheduleParser(uid)

    # Обновление данных автопоста
    # ---------------------------

    c = Config(filepath=config_path)
    if uid in c.file_data:
        c.file_data[uid]["day"] = int(datetime.today().strftime('%j'))
        c.file_data[uid]["hour"] = datetime.now().hour
        c.save()


    if ctx.sargs.lower() in ["changes", "изменения"]:
        res = sp.print_sc_changes()
    else:
        res = sp.print_lessons([0, 1, 2, 3, 4, 5], ctx.sargs.lower())
        res += f'\n\n/расписание изменения - что нового в расписании'

    if not ctx.sargs and not sp.user["set_class"]:
        res += set_class_message

    await ctx.message(res)



# Расширенные команды
# ===================

@p.command('sparser', usage='Статус парсера расписания')
async def sparserStatus(event, ctx):
    sp = ScheduleParser(str(event.get('to.id')))
    await ctx.message(sp.print_status())

@p.command('<lesson(s) c(ount)>', usage='[class_let] самые частые уроки')
async def countLessons(event, ctx):
    sp = ScheduleParser(str(event.get('to.id')))
    await ctx.message(sp.count_lessons(ctx.sargs or None))
