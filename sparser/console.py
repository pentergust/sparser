"""
Обёртка над ScheduleParser для отправки расписания в консоль.
Author: Milinuri Nirvalen
Ver: 3.1
"""

from sparser import SPMessages, load_file, days_str, timetable
from datetime import datetime
import argparse
import re

from icecream import ic


# Вспомогательные компоненты
# ==========================

def parse_days(args):
    days = []

    for x in args:
        if x == "сегодня":
            days.append(datetime.today().weekday())
            continue

        if x == "завтра":
            days.append(datetime.today().weekday()+1)

        for i, d in enumerate(days_str):
            if x.startswith(d):
                days.append(i)
                continue

    return days

def group_log(text):
    print(f'\033[96m:\033[94m: \033[0m\033[1m{text}\033[0m')

def rc(text):
    return re.sub(r'\033\[[0-9]*m', '', text)

def row(text= None, color=35):
    if text:
        lc = 73 - len(text)
        print(f"\033[90m----- \033[{color}m{text} \033[90m{'-'*lc}\033[0m")
    else:
        print("\033[90m"+"-"*80+"\033[0m")


class SPConsole(SPMessages):
    """Переписанный класс генепатора сообщений для консоли.

    :param uid: User ID, кто использует парсер"""
    
    def __init__(self, uid):
        super(SPConsole, self).__init__(uid)
    
    def send_sc_changes(self, days=None, class_let=None):
        """Отправить измененив в расписании.

        :param days: Для каких дней показать изменения
        :param class_let: Для какого класса показать изменения"""

        sc_changes = load_file(self.scu_path)
        group_log("Изменения в расписании:")
        
        if class_let is not None:
            class_let = self.get_class(class_let)


        # Пробегаемся по измененияв в оасписании
        for x in sc_changes["changes"]:
            
            # Добавляем заголовок изменений
            t = datetime.fromtimestamp(x["time"]).strftime("%H:%M:%S")
            print(f"\nПримерно в {t}")

            # Пробегаемся по дням
            for day, changes in enumerate(x["diff"]):
                if days and day not in days:
                    continue

                if changes:
                    row(f"На {days_str[day]}", 36)
                    
                    # Пробегаемся по классам
                    for k, v in changes.items():
                        if class_let and class_let != k:
                            continue

                        row(k, 94)
                        d_str = "" 

                        # Проьегаемся по урокам
                        for i, l in enumerate(v):
                            o = l[0]
                            n = l[1]

                            if n:
                                if n[1] != o[1]:
                                    print(f"\033[34m{i+1} \033[90m| \033[31m{o[0]}\033[90m:{o[1]} \033[0m> \033[32m{n[0]}\033[90m:{n[1]}\033[0m")
                                else:
                                    print(f"\033[34m{i+1} \033[90m| \033[31m{o[0]} \033[0m> \033[32m{n[0]}\033[90m:{n[1]}\033[0m")
                            else:
                                print(f"\033[34m{i+1} \033[90m| \033[0m{o[0]}\033[90m:{o[1]}\033[0m")

    def send_day_lessons(self, today=0, class_let=None):
        """Сообщение с расписанием уроков на день.
        
        :param today: День недеди (0-5)
        :param class_let: Класс, которому требуется расписание
        
        :return: Сообщение с расписанием на день"""
        
        # Ограничение дней
        if today > 5:
            today = 0
    
        class_let = self.get_class(class_let)
        lessons = self.get_lessons(class_let)[today]["l"]
        row(f"На {days_str[today]}", 36)
        
        # Собираем сообщение с расписанием
        for i, x in enumerate(lessons):
            tt = ""
            if i < len(timetable):
                tt = f" {timetable[i][0]}"
            
            print(f"\033[34m{i+1}{tt} \033[90m| \033[0m{x[0]}\033[90m:{x[1]}\033[0m")

        return ""
     
    def send_lessons(self, days=[0], class_let=None):
        """Сообщение с расписанием уроков.

        :param days: Дни недели, для которых нужно расписание
        :param class_let: Класс, для которого нужно расписание

        :return: Сообщение с расписанием"""

        class_let = self.get_class(class_let)

        if isinstance(days, int):
            days = [days]     

        # Убираем повторы и отрезаем несуществующие дни
        # ---------------------------------------------

        days = set(filter(lambda x: x < 6, days))

        # Собираем сообщение
        # ------------------

        print(f"\nРасписание для {class_let}:")

        for day in days:
            print()
            self.send_day_lessons(day, class_let)
        

        # Обновления в расписаниии
        # ------------------------
        
        if class_let == self.user["class_let"]:
            updates = self.get_lessons_updates()
            
            if updates:
                print()
                group_log(f"Изменилось расписание!")

                updates = updates - days
                if len(updates) < 3:
                    for day in updates:
                        self.send_day_lessons(day) 
                else:
                    print(f"На {', '.join(map(lambda x: days_str[x], updates))}.")

    def count_lessons(self, class_let=None):
        """Считает частоту уроков в расписании.
        Для всех или определённого класса.

        :param class_let: Для какого класса произвести подсчёт

        :returns: Сообщение с самыми частыми классами"""

        if class_let is not None:
            class_let = self.get_class(class_let)

        res = ""
        lindex = self.get_sc_lindex()
        groups = {}

        # Считаем частоту предметов
        # -------------------------

        for lesson, v in lindex.items():
            
            cabinets = {}
            for cabinet, vv in v.items():
                if class_let:
                    c = sum(map(len, vv.get(class_let, [])))
                else:
                    c = sum(map(lambda x: sum(map(len, x)), vv.values()))

                if c:
                    cabinets[cabinet] = c

            c = sum(cabinets.values())
            if c:
                if str(c) not in groups:
                    groups[str(c)] = {}

                groups[str(c)][lesson] = cabinets
  
        # Собираем сообщение
        # ------------------

        if class_let:
            group_log(f"Самые частые уроки у {class_let}:")
        else:
            group_log(f"Самые частые уроки:")

        for k, v in sorted(groups.items(), key=lambda x: int(x[0]), reverse=True):
            print()
            row(F"{k} раз(а)", 35)

            for lesson, cabinets in v.items():
                cabinets_str = ""

                for c, n in cabinets.items():
                    if n > 1 and len(cabinets) > 1:
                        cabinets_str += f"\033[33m{c}:\033[90m{n} "
                    else:
                        cabinets_str += f"\033[33m{c} "
                
                print(f" * {lesson} {cabinets_str}\033[0m")
                
    def count_cabinets(self, class_let=None):
        """Считает частоту кабинетов в расписании.
        Для всех или определённого класса.

        :param class_let: Для какого класса произвести подсчёт

        :returns: Сообщение с самыми частыми кабинетами"""

        if class_let is not None:
            class_let = self.get_class(class_let)

        cindex = self.get_sc_cindex()
        groups = {}

        # Считаем частоту предметов
        # -------------------------

        for cabinet, v in cindex.items():      
            lessons = {}
            for l, vv in v.items():
                if class_let:
                    c = sum(map(len, vv.get(class_let, [])))
                else:
                    c = sum(map(lambda x: sum(map(len, x)), vv.values()))

                if c:
                    lessons[l] = c

            c = sum(lessons.values())
            if c:
                if str(c) not in groups:
                    groups[str(c)] = {}

                groups[str(c)][cabinet] = lessons
  
        # Собираем сообщение
        # ------------------

        if class_let:
            group_log(f"Самые частые кабинеты у {class_let}:")
        else:
            group_log(f"Самые частые кабинеты:")

        for k, v in sorted(groups.items(), key=lambda x: int(x[0]), reverse=True):
            row(f"{k} раз(а)", 35)
            
            for cabinet, lessons in v.items():
                lessons_str = ""

                for l, n in lessons.items():
                    if n > 1 and len(lessons) > 1:
                        lessons_str += f"\033[33m{l}:\033[90m{n} "
                    else:
                        lessons_str += f"\033[33m{l} "
                
                print(f" * {cabinet}: {lessons_str}\033[0m")
  
    def search_lesson(self, lesson, days=None, class_let=None):
        """Поиск упоминаний о уроке.
        Когда (день), где (кабинет), для кого (класс), каким уроком.

        :param lesson: Урок, который нужно найти
        :param days: Для каких дней отображать результат поиска
        :param class_let: Для какого класса отображать результаты

        :returns: Сообщение с результатами поиска."""

        lindex = self.get_sc_lindex()
        
        if lesson not in lindex:
            print("Неправильно указан предмет")
            print(f"Доступные предметы: {'; '.join(lindex)}")
            return False

        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))

        if class_let is not None:
            class_let = self.get_class(class_let)

        data = self.search(lesson)

        # Собираем сообщение
        # ------------------

        search_str = f"Поиск упоминаний \"{lesson}\""
        if days == {0, 1, 2, 3, 4, 5}:
            search_str += f" за неделю"
        elif days:
            search_str += f" за {', '.join(map(lambda x: days_str[x], days))}"

        if class_let:
            search_str += f" для {class_let}"

        group_log(search_str)

        # Пробегаемся по результатам поиска
        for cabinet, v in data.items():
            row(cabinet, 35)

            # Пробегаемся по указанным дням
            for day in days:
                ln = v[day]
                day_res = []

                for i, cs in enumerate(ln):
                    if class_let and class_let not in cs:
                        continue

                    if cs:
                        tt = ""

                        if i < len(timetable):
                            tt = f'{timetable[i][0]} '

                        print(f"\033[32m{days_str[day]} \033[34m {i+1}. {tt}\033[0m- {', '.join(cs)}")
        
    def search_cabinet(self, cabinet, lesson=None, days=None, class_let=None):
        """Поиск упоминаний о кабинете.
        Когда (день), что (урок), для кого (класс), каким уроком.

        :param cabinet: Кабинет, который нужно найти
        :param lesson: Для какого урока отображать результат
        :param days: Для каких дней отображать результат поиска
        :param class_let: Для какого класса отображать результаты

        :returns: Сообщение с результатами поиска."""

        cindex = self.get_sc_cindex()
        
        if cabinet not in cindex:
            print("Неправильно указан кабинет")
            print(f"Доступные кабинеты: {'; '.join(cindex)}")
            return False
            
        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))

        if class_let is not None:
            class_let = self.get_class(class_let)

        data = self.search(cabinet)


        # Собираем сообщение
        # ------------------

        search_str = f"Поиск по кабнету {cabinet}"
        if days == {0, 1, 2, 3, 4, 5}:
            search_str += " за неделю"
        elif days:
            search_str += f" за {', '.join(map(lambda x: days_str[x], days))}"

        if class_let:
            search_str += f" для {class_let}"

        if lesson:
            search_str += f" ({lesson})"

        group_log(search_str)

        # Пробегаемся по результатам поиска
        for l, v in data.items():

            if lesson and lesson != l:
                continue

            row(l, 35)

            # Пробегаемся по указанным дням
            for day in days:
                ln = v[day]
                
                for i, cs in enumerate(ln):
                    if class_let and class_let not in cs:
                        continue

                    if cs:
                        tt = ""

                        if i < len(timetable):
                            tt = f'В {timetable[i][0]} '

                        print(f"\033[32m{days_str[day]} \033[34m{i+1}. {tt}\033[0m- {', '.join(cs)}")



def main():
    days_str = ["понедельник", "вторник", "сред", "четверг", "пятниц", "суббот"]
    sp = SPConsole("Console")
    days = []
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--parse", action="store_true", 
                        help="Принудительное обновление расписания")
    
    # Определние команд парсера
    # -------------------------

    subparsers = parser.add_subparsers(dest="cmd", metavar="command")
    subparsers.add_parser("status", help="Информация о парсере")
    
    lessons = subparsers.add_parser("lessons", help="Самые частые уроки")
    lessons.add_argument("class_let", nargs="?", default=None,
                         help="Сортировка по классу")
    
    cabinets = subparsers.add_parser("cabinets", help="Самые частые кабинеты")
    cabinets.add_argument("class_let", nargs="?", default=None,
                          help="Сортировка по классу")

    changes = subparsers.add_parser("changes", help="Изменения в расписании")
    changes.add_argument("-d", dest="days", nargs="*", default=[],
                        help="Сортировка по дням (понедельник-суббота)")
    changes.add_argument("-c", dest="class_let", nargs="?",
                        help="Сортировка по классу")

    search = subparsers.add_parser("search", help="Поиск в расписании")
    search.add_argument("args", nargs="+", help="Урок, кабинет или класс")

    week = subparsers.add_parser("week", help="Расписание на неделю")
    week.add_argument("class_let", nargs="?", default=None, 
                      help="Целевой класс")
    
    sc = subparsers.add_parser("sc", help="Расписание уроков")
    sc.add_argument("class_let", nargs="?", default=None, help="Целевой класс")
    
    change_class = subparsers.add_parser("class", 
                                         help="Изменить класс по умолчанию")
    change_class.add_argument("class_let", help="Целевой класс")


    # Обработка аргументов
    # ====================

    args = parser.parse_args()
    
    # Принудитекльно обновляем расписание
    if args.parse:
        sp.get_schedule(True)

    # Задаём дни недели
    if "days" in args:
        days = parse_days(args.days)

    if not args.cmd:
        sp.send_today_lessons()


    
    if args.cmd == "changes":
        sp.send_sc_changes(days, args.class_let)
    
    if args.cmd == "status":
        print(sp.send_status())

    if args.cmd == "lessons":
        sp.count_lessons(args.class_let)
    
    elif args.cmd == "cabinets":
        sp.count_cabinets(args.class_let)

    elif args.cmd == "search":
        days = []
        cabinet = None
        lessons = None
        class_let = None
        cindex = sp.get_sc_cindex()
        lindex = sp.get_sc_lindex()

        for x in args.args:
            if x == "сегодня":
                days.append(datetime.today().weekday())
                continue

            if x == "завтра":
                days.append(datetime.today().weekday()+1)

            for i, d in enumerate(days_str):
                if x.startswith(d):
                    days.append(i)
                    continue
    
            if x in sp.lessons:
                class_let = x

            elif x in lindex:
                lessons = x

            elif x in cindex:
                cabinet = x


        if cabinet:
            sp.search_cabinet(cabinet, lessons, days, class_let)
        else:
            sp.search_lesson(lessons, days, class_let)

    elif args.cmd == "week":
        sp.send_lessons([0, 1, 2, 3, 4, 5], args.class_let)
   
    elif args.cmd == "sc":
        if days:
            sp.send_lessons(days, args.class_let)
        else:
            sp.send_today_lessons(args.class_let)

    if args.cmd == "class":
        print(sp.set_class(args.class_let))

    if not sp.user["set_class"]:
        print("\nНе указан класс по умолчанию для Console.")
        print("Используйте \"--help\" для получения Информации.")



if __name__ == "__main__":
    main()
