"""
Обёртка над ScheduleParser для отправки расписания в консоль.
Author: Milinuri Nirvalen
Ver: 3.1
"""

from sparser import SPMessages, load_file, days_str, timetable

from datetime import datetime
from shutil import get_terminal_size

import argparse
import re


# Вспомогательные функции
# =======================

def parse_days(args):
    """Парсит имена дней из аргументов.
    
    Args:
        args (list): Список строковых аргументов
    
    Returns:
        list: Список номеров дней
    """
    
    days = []

    for x in args:
        if x == "сегодня":
            days.append(datetime.today().weekday())
            continue

        if x == "завтра":
            days.append(datetime.today().weekday()+1)
            continue

        # Если начало слова совпадает пятниц... а, у, ы.
        for i, d in enumerate(days_str):
            if x.startswith(d):
                days.append(i)
                continue

    return days

def register_user(sp):
    """Проводит первоначальную регистрацию класса пользователя.
    
    Args:
        sp (ScheduleParser): Экземпляр парсера
    """

    print("Добро пожаловать!")
    print("Для использования SP, ему нужно знать ваш класс.")
    print("Для того, чтобы не указывать его каждый раз.")
    print("Вы всегда сможете сменить свой класс по умолчанию.")
    print(f"\nДоступные классы: {', '.join(sp.lessons)}")

    while True:
        print()
        class_let = input("\033[33mВаш класс\033[0m: ").lower().strip()

        if class_let in sp.lessons:
            print(sp.set_class(class_let))
            break


# Вспомогательные функции отображения
# ===================================

def group_log(text):
    print(f'\033[96m:\033[94m: \033[0m\033[1m{text}\033[0m')

def rc(text):
    """Очищает текст от цветовых кодов."""
    return re.sub(r'\033\[[0-9]*m', '', text)

def row(text= None, color=35):
    """Вертикальный разделитель в консоли.
    
    Args:
        text (str, optional): Текст разделителя
        color (int, optional): Цвет текста
    """
    
    l = get_terminal_size()[0]

    if text:
        lc = l - (len(text) + 7)
        print(f"\033[90m===== \033[{color}m{text} \033[90m{'-'*lc}\033[0m")
    else:
        print("\033[90m"+"-"*l+"\033[0m")

def enumerate_list(l, pt=False):
    """Отображает пронумерованный список.
    
    Args:
        l (list): Список для отображения
        pt (bool, optional): Отображать ли расписание (звонков)
    """

    for i, x in enumerate(l):
        if pt:
            tt = ""
            if i < len(timetable):
                tt = f" {timetable[i][0]}"
            print(f"\033[94m{i+1}\033[34m{tt}\033[90m| \033[0m{x}\033[0m")
        
        else:
            print(f"\033[34m{i+1}\033[90m|\033[0m {x}\033[0m")


# Генератор сообщений для консоли
# ===============================

class SPConsole(SPMessages):
    """Генератор сообщений для консоли."""
    
    def __init__(self, uid):
        super(SPConsole, self).__init__(uid)
    
    def send_sc_changes(self, days=None, cl=None):
        """Отображает изменения в расписании.
        
        Args:
            days (list, optional): Фильтр по дням
            cl (str, optional): Фильтр по классу
        """

        sc_changes = load_file(self._scu_path)
        group_log("Изменения в расписании:")
        
        if cl is not None:
            cl = self.get_class(cl)

        # Пробегаемся по измененияв в расписании
        for x in sc_changes["changes"]:      
            
            # заголовок изменений
            t = datetime.fromtimestamp(x["time"]).strftime("%H:%M:%S")
            print(f"\nПримерно в {t}")

            # Пробегаемся по дням
            for day, changes in enumerate(x["diff"]):
                if days and day not in days:
                    continue

                if changes:
                    print()
                    row(f"На {days_str[day]}", color=36)
                    
                    # Пробегаемся по классам
                    for k, v in changes.items():
                        if cl and cl != k:
                            continue

                        row(k, color=94)
                        res = []

                        # Пробегаемся по урокам
                        for o, n in v:
                            if n:
                                res.append(f"{o[0]} >> \033[32m{n[0]}\033[90m:{n[1]}")
                            else:
                                res.append(f"{o[0]}\033[90m:{o[1]}")
                            
                        enumerate_list(res)

    def send_day_lessons(self, today=0, cl=None):
        """Отображает расписанием уроков на день.
        
        Args:
            today (int, optional): День недели
            cl (str, optional): Для какого класса
        """
        
        # Ограничение дней
        today = today % 6
    
        cl = self.get_class(cl)
        lessons = self.get_lessons(cl)[today]["l"]
        row(f"На {days_str[today]}", color=36)
        
        # Собираем сообщение с расписанием
        res = []
        for x in lessons:
            res.append(f"{x[0]}\033[90m:{x[1]}")
        
        enumerate_list(res, pt=True)
     
    def send_lessons(self, days=[0], cl=None):
        """Отображает расписанием уроков.
        
        Args:
            days (list, optional): Для каких дней недели
            cl (str, optional): Для какого класса
        """

        cl = self.get_class(cl)

        if isinstance(days, int):
            days = [days]     

        # Убираем повторы и несуществующие дни
        days = set(filter(lambda x: x < 6, days))

        # Собираем сообщение
        # ------------------

        print(f"\nРасписание для {cl}:")
        for day in days:
            print()
            self.send_day_lessons(day, cl)
        
        # Обновления в расписании
        # -----------------------
        
        if cl == self.user["class_let"]:
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

    def count_lessons(self, cl=None):
        """Считает частоту уроков в расписании.
        
        Args:
            cl (str, optional): Для какого класса
        """

        if cl is not None:
            cl = self.get_class(cl)

        # Считаем частоту предметов
        res = {}
        for lesson, v in self.l_index.items(): 
            cabinets = {}
            
            for cabinet, vv in v.items():
                if cl:
                    c = sum(map(len, vv.get(cl, [])))
                else:
                    c = sum(map(lambda x: sum(map(len, x)), vv.values()))

                if c:
                    cabinets[cabinet] = c

            c = sum(cabinets.values())
            if c:
                if str(c) not in res:
                    res[str(c)] = {}

                res[str(c)][lesson] = cabinets
  
        # Собираем сообщение
        # ------------------

        if cl:
            group_log(f"Самые частые уроки у {cl}:")
        else:
            group_log(f"Самые частые уроки:")

        for k, v in sorted(res.items(), key=lambda x: int(x[0]), reverse=True):
            print()
            row(f"{k} раз(а)", color=35)

            for lesson, cabinets in v.items():
                cabinets_str = ""

                for c, n in cabinets.items():
                    if n > 1 and len(cabinets) > 1:
                        cabinets_str += f"\033[33m{c}:\033[90m{n} "
                    else:
                        cabinets_str += f"\033[33m{c} "
                
                print(f" * {lesson} {cabinets_str}\033[0m")
                
    def count_cabinets(self, cl=None):
        """Считает частоту кабинетов в расписании.
        
        Args:
            cl (str, optional): Для какого класса
        """

        if cl is not None:
            cl = self.get_class(cl)


        # Считаем частоту кабинетов        
        res = {}
        for cabinet, v in self.c_index.items():      
            lessons = {}
            for l, vv in v.items():
                if cl:
                    c = sum(map(len, vv.get(cl, [])))
                else:
                    c = sum(map(lambda x: sum(map(len, x)), vv.values()))

                if c:
                    lessons[l] = c

            c = sum(lessons.values())
            if c:
                if str(c) not in res:
                    res[str(c)] = {}

                res[str(c)][cabinet] = lessons
  
        # Собираем сообщение
        # ------------------

        if cl:
            group_log(f"Самые частые кабинеты у {cl}:")
        else:
            group_log(f"Самые частые кабинеты:")

        for k, v in sorted(res.items(), key=lambda x: int(x[0]), reverse=True):
            row(f"{k} раз(а)", color=35)
            
            for cabinet, lessons in v.items():
                lessons_str = ""

                for l, n in lessons.items():
                    if n > 1 and len(lessons) > 1:
                        lessons_str += f"\033[33m{l}:\033[90m{n} "
                    else:
                        lessons_str += f"\033[33m{l} "
                
                print(f" * {cabinet}: {lessons_str}\033[0m")
  
    def search_lesson(self, lesson, days=None, cl=None):
        """Поиск упоминаний об уроке.
        
        Args:
            lesson (str): Урок для поиска
            days (list, optional): Для каких дней
            cl (str, optional): Для какого класса
        """
        
        if lesson not in self.l_index:
            print("Неправильно указан предмет")
            print(f"Доступные предметы: {'; '.join(self.l_index)}")
            return False

        if cl is not None:
            cl = self.get_class(cl)

        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))
        data = self.search(lesson)

        # Собираем сообщение
        # ------------------

        search_str = f"Поиск упоминаний \"{lesson}\""
        if days == {0, 1, 2, 3, 4, 5}:
            search_str += f" за неделю"
        elif days:
            search_str += f" за {', '.join(map(lambda x: days_str[x], days))}"

        if cl:
            search_str += f" для {cl}"

        group_log(search_str)

        # Пробегаемся по результатам поиска
        for cabinet, v in data.items():
            print()
            row(cabinet, color=35)

            # Пробегаемся по указанным дням
            for day in days:
                ln = v[day]
                day_res = []

                res = []
                for i, cs in enumerate(ln):
                    if cl and cl not in cs:
                        continue

                    if cs:
                        res.append(", ".join(cs))
                        
                if res:
                    row(days_str[day], color=32)
                    enumerate_list(res, pt=True)

    def search_cabinet(self, cabinet, lesson=None, days=None, cl=None):
        """Поиск упоминаний о кабинете.
        Когда (день), что (урок), для кого (класс), каким уроком.
        
        Args:
            cabinet (str): Кабинет для поиска
            lesson (str, optional): Для какого урока
            days (list, optional): Для каких дней
            cl (str, optional): Для какого класса
        """

        if cabinet not in self.c_index:
            print("Неправильно указан кабинет")
            print(f"Доступные кабинеты: {'; '.join(self.c_index)}")
            return False
            
        if cl is not None:
            cl = self.get_class(cl)

        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))
        data = self.search(cabinet)

        # Собираем сообщение
        # ------------------

        search_str = f"Поиск по кабнету {cabinet}"
        if days == {0, 1, 2, 3, 4, 5}:
            search_str += " за неделю"
        elif days:
            search_str += f" за {', '.join(map(lambda x: days_str[x], days))}"

        if cl:
            search_str += f" для {cl}"

        if lesson:
            search_str += f" ({lesson})"

        group_log(search_str)

        # Пробегаемся по результатам поиска
        res = [[[] for x in range(8)] for x in range(6)]
        for l, v in data.items():
            if lesson and lesson != l:
                continue

            # Пробегаемся по указанным дням
            for day in days:
                ln = v[day]
                
                for i, cs in enumerate(ln):
                    if cl and cl not in cs:
                        continue

                    if cs:
                        res[day][i].append(f"{l}:\033[33m{', '.join(cs)}\033[0m")
            
        for day, lessons in enumerate(res):
            if lessons:
                print()
                row(days_str[day], color=35)
                
                while lessons:
                    if not lessons[-1]:
                        lessons.pop()
                    else:
                        break

                day_lessons = []
                for l in lessons:
                    if not l:
                        day_lessons.append("===")
                    else:
                        day_lessons.append(", ".join(l))
                            
                enumerate_list(day_lessons, pt=True)
 

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
    changes.add_argument("-d", dest="days", nargs="+", default=[],
                        help="Сортировка по дням (понедельник-суббота)")
    changes.add_argument("-c", dest="class_let", help="Сортировка по классу")

    search = subparsers.add_parser("search", help="Поиск в расписании")
    search.add_argument("args", nargs="+", help="Урок, кабинет или класс")

    week = subparsers.add_parser("week", help="Расписание на неделю")
    week.add_argument("class_let", nargs="?", default=None, 
                      help="Целевой класс")
    
    sc = subparsers.add_parser("sc", help="Расписание уроков")
    sc.add_argument("class_let", nargs="?", default=None, help="Целевой класс")
    sc.add_argument("-d", dest="days", nargs="+", default=[],
                    help="Для каких дней (понедельник-суббота)")
    
    change_class = subparsers.add_parser("class", 
                                         help="Изменить класс по умолчанию")
    change_class.add_argument("class_let", help="Целевой класс")


    # Обработка аргументов
    # ====================

    args = parser.parse_args()

    if not sp.user["set_class"]:
        register_user(sp)
    
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

            elif x in sp.l_index:
                lessons = x

            elif x in sp.c_index:
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
