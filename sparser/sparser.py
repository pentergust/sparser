"""
Самостоятельный парсер школьного расписания.
- Преобразование расписания в удобнгый формат.
- Просмотр расписания.
- Сообщение об изменении в расписании.
- Статистика по предметам.
- Поиск по предмету.

Author: Milinuri Nirvalen
Ver: 2.4.1

Modules:
      os: Проверка существования файлов
    json: Управление файлами
     csv: Чтение CSV файла расписания
 hashlib: Работа с хеш-суммами
requests: Получение файла расписания
datetime: Работа с датой
"""

import os
import json
import csv
import hashlib
import requests
from datetime import datetime

# from icecream import ic


"""
Настройки скрипта
------------------
    url       : Ссылка на загрузку CSV файла расписания
    users_path: Путь по умолчанию к файлу данных пользователей
    sc_path   : Путь по умолчанию к файлу расписания
    user_data : Информация о пользователе по умолчанию
    timetable : Расписание звонков [[Начало, Конец], [...]...]
"""

url = "https://docs.google.com/spreadsheets/d/1pP_qEHh4PBk5Rsb7Wk9iVbJtTA11O9nTQbo1JFjnrGU/export?format=csv"
users_path = "users.json"
sc_path = "sc.json"
sc_updates_path = "sc_updates.json"
user_data = {"class_let":"9г", "set_class": False, "last_parse": 0}
timetable = [["08:00", "08:45"],
             ["08:55", "09:40"],
             ["09:55", "10:40"],
             ["10:55", "11:40"],
             ["11:50", "12:35"],
             ["12:45", "13:30"],
             ["13:40", "14:25"],
             ["14:35", "15:20"]]

days_str = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу"]
log_prefix = f'\033[96mS\033[94mP \033[90m| '


# Управоение файлами
# ==================

def save_file(path, data):
    """Записывает данные в файл.

    :param path: Путь к файлу для записи
    :param data: Данные для записи

    :return: data"""

    with open(path, 'w') as f:
        f.write(json.dumps(data, indent=4, ensure_ascii=False))
    return data

def load_file(path, data={}):
    """Читает данные из файла.

    :param path: Путь к файлу для чтения
    :param data: Данные для записи при отцуцтвии файла

    :return: Данные из файла или data"""

    if os.path.isfile(path):
        with open(path) as f:
            return json.loads(f.read())
    
    elif data is not None:
        return save_file(path, data)

    else:
        return {}


# Функции отображения
# ===================

def log(text):
    print(f'{log_prefix}\033[33m{text}\033[0m')

def group_log(text):
    print(f'{log_prefix}\033[96m:\033[94m: \033[0m\033[1m{text}\033[0m')


class ScheduleParser:
    """Парсер школьного расписание
    
    :param uid: User ID или кто работает с расписанием
    :param sc_file: Нестандартный путь к файлу расписания
    :param users_file: Неcтандартный путь к файлу пользователей
    """
    
    def __init__(self, uid, sc_file=sc_path, sc_updates_file=sc_updates_path,
                 users_file=users_path):
        super(ScheduleParser, self).__init__()
        self.uid = uid
        self.sc_path = sc_file
        self.sc_updates_path = sc_updates_file
        self.users_path = users_file

        # Получаем данные пользователя и расписание
        self.user = self.get_user()
        self.schedule = self.get_schedule()
        

        # lessons: Расписание с классами в качестве ключей
        # l_index: Расписание, с предметами в качестве ключей
        # c_index: Расписание, с кабинетами в качестве ключей

        self.lessons = self.schedule["lessons"]
        self.l_index = None
        # self.c_index = None


    # Управление данными пользователя
    # ===============================

    def get_user(self):
        """Возвращает данные пользователя или данные по умолчанию."""
        return load_file(self.users_path).get(self.uid, user_data)

    def save_user(self):
        """Записывает данные пользователя в self.users_path."""
        users = load_file(self.users_path, {})
        users[self.uid] = self.user
        save_file(self.users_path, users)
        log(f'Write: {self.uid}')


    # Получаем расписание
    # ===================

    def parse_schedule(self, csv_file):
        """Преобразует CSV файл в удобный формат.

        :param csv_file: CSV файл расписания для преобразования

        :return: Преобразованное расписание"""
        
        group_log('Parse schedule...')
    
        # class_index: Словарь с классами и их столбцам в расписании
        #     lessons: Словарь расписания [КЛАСС][Номер Дня]
        #      dindex: Указание строк начала дней недели
        #         day: Номер текущего дня недели (0-5)
        #     lessons: Максимальное кол-во урокеов в день
        
        class_index = {}
        lessons = {}
        dindex = [3, 11, 19, 27, 35, 43, 49]
        day = 0
        max_lessons = 8
        
        log('-> Read CSV file...')
        reader = csv.reader(csv_file.decode("utf-8").splitlines())

        for i, row in enumerate(list(reader)):
            
            # Получаем словарь с классами
            if i == 1:
                log('-> Get class_index...')
                for v, k in enumerate(row):
                    if k.replace(' ', ''):
                        class_index[k.lower()] = v


            # Собираем расписание уроков
            # --------------------------

            if day < len(dindex)-2 and i == dindex[day]+max_lessons:    
                day += 1 

            if i >= dindex[day] and i < min(dindex[day]+max_lessons, dindex[-1]):
                    
                # Пробегаемся по всем класаам
                for k, v in class_index.items():
                        
                    # Если класса нет в расписании, то добавляем его
                    if k not in lessons:
                        lessons[k] = [
                            {"l":["" for x in range(max_lessons)],
                             "hash": None} for x in range(6)
                        ]

                    lessons[k][day]["l"][i-dindex[day]] = [row[v], row[v+1]]


        # Получаем хеши дней
        # ==================

        log('-> Get day hsshes and cleanup...')
        for class_let, days in lessons.items():
            n_days = []
            
            for day in days:
                h = hashlib.md5(bytearray(f";".join(day["l"][0]),
                                          'utf-8')).hexdigest()
                
                while True:
                    l = day["l"][-1]
                    
                    if not l or not l[0] or l[0] == "---":
                        day["l"].pop()
                    else:
                        break

                day["hash"] = h
                n_days.append(day)
            lessons[class_let] = n_days

        return lessons

    def get_schedule_diff(self, old_t, new_t):
        """Делает полное сравнение двух расписаний."""

        res = [{} for x in range(6)]

        for k, v in new_t.items():
            if not k in old_t:
                continue

            old_v = old_t[k]

            for day, lessons in enumerate(v):
                if lessons["hash"] == old_v[day]["hash"]:
                    continue

                o_lessons = old_v[day]["l"]
                for lesson_n, lesson in enumerate(lessons["l"]):
                    if lesson_n >= len(o_lessons):
                        o_lesson = ["", ""]
                    else:
                        o_lesson = o_lessons[lesson_n]

                    if k not in res[day]:
                        res[day][k] = []

                    if lesson != o_lesson: 
                        res[day][k].append(f'{lesson_n+1}: {o_lesson[0]} -> {lesson[0]}')
                    else:
                        res[day][k].append(f'{lesson_n+1}: {lesson[0]}')

        return res

    def update_diff_file(self, old_t, new_t):
        log('Update diff file...')

        sc_changes = load_file(self.sc_updates_path)
        day = int(datetime.now().strftime('%j'))        
        
        if sc_changes.get("day", 0) != day:
            sc_changes = {"day":day, "changes":[]}

        diff = self.get_schedule_diff(old_t.get("lessons", {}), 
                                      new_t["lessons"])

        if sum(map(len, diff)):
            sc_changes["changes"].append({"time": new_t["last_parse"],
                                          "diff": diff})

        save_file(self.sc_updates_path, sc_changes)

    def get_schedule(self, update=False):
        """Получает и обновляет расписание.
        :param update: Принудительное обновление расписания

        :return: Преобразованное расписание уроков"""

        log(f'{"Update" if update else "Get"} {self.uid} schedule')

        now = datetime.now()
        hour = now.hour
        t = load_file(self.sc_path)
        
        # Обновляем данные расписания
        if not t or t.get('updated', 0) != hour or update:
            old_t = t.copy()
            csv_file = requests.get(url).content
            h = hashlib.md5(csv_file).hexdigest()

            if t.get("hash", "") != h or update:
                t["lessons"] = self.parse_schedule(csv_file)
                t["last_parse"] = datetime.timestamp(datetime.now())
                t["hash"] = h

                self.update_diff_file(old_t, t)
            else:
                log("Schedule is up to date")

            t["updated"] = hour
            save_file(self.sc_path, t)    
               
        return t


    # Получение индексов
    # ==================

    def get_lessons_index(self):
        """Получает информацию об уроках в расписании.
        Имена уроков, для кого и когда."""

        if self.l_index:
            return self.l_index

        lessons = {}

        for k, v in self.lessons.items():
            for day, day_lessons in enumerate(v):
                for i, lesson in enumerate(day_lessons["l"]):

                    lesson = lesson[0].lower().strip(" .")
                    lesson = lesson.replace('-', '=').replace(' ', '-')

                    if lesson not in lessons:
                        lessons[lesson] = {}

                    if k not in lessons[lesson]:
                        lessons[lesson][k] = [[] for x in range(6)]

                    lessons[lesson][k][day].append(i)

        self.l_index = lessons
        return lessons

 
    # Взаимодействуем с расписанием
    # =============================

    def get_class(self, class_let=None):
        """Возвращает выбранный класс или класс по умолчанию."""

        if class_let is None or class_let not in self.lessons:
            return self.user["class_let"]

        return class_let

    def get_lessons(self, class_let=None):
        """Получает расписание уроков на неделю для класса."""
        return self.lessons[self.get_class(class_let)]

    def get_schedule_changes(self):
        """Возвращает номера дней, для которых изменилось расписание."""
        
        # Если расписание не обновилось, значит и хеши дней тоже
        if self.schedule["last_parse"] == self.user["last_parse"]:
            return []

        sc_changes = load_file(self.sc_updates_path)
        lessons = self.get_lessons()
        days = []

        self.user["last_parse"] = self.schedule["last_parse"]
        self.save_user()
        
        for x in sc_changes["changes"]:
            for day, changes in enumerate(x["diff"]):
                if changes.get(self.user["class_let"]):
                    days.append(day)
 
        return set(days)


    # Методы представления
    # ====================

    def print_sc_changes(self):
        """Отобразить измененив в расписании."""

        sc_changes = load_file(self.sc_updates_path)

        res = "Обновления в расписании:"

        for x in sc_changes["changes"]:
            t = datetime.fromtimestamp(x["time"]).strftime("%H:%M:%S")
            res += f'\n⏰ Примерно в {t}:'

            for day, changes in enumerate(x["diff"]):
                if changes:
                    res += f"\nНа {days_str[day]}:\n"
                    
                    for k, v in changes.items():
                        changes_str = '\n'.join(v)
                        res += f"\n🔶 Для {k}:\n{changes_str}\n"

        return res

    def count_lessons(self, class_let=None):
        """Считает частоту уроков в расписании.
        Для всех или определённого класса.

        :param class_let: Для какого класса произвести подсчёт

        :returns: Сообщение с самыми частыми классами"""

        if class_let is not None:
            class_let = self.get_class(class_let)

        res = ""
        lindex = self.get_lessons_index()
        groups = {}


        # Считаем частоту предметов
        # -------------------------

        for lesson, v in lindex.items():
            if class_let:
                if class_let in v:
                    c = sum(map(len, v[class_let]))
            else:
                c = sum(map(lambda x: sum(map(len, x)), v.values()))

            if str(c) not in groups:
                groups[str(c)] = []

            groups[str(c)].append(lesson)
  

        # Собираем сообщение
        # ------------------

        if class_let:
            res += f"✨ Самые частые уроки у {class_let}:\n"
        else:
            res += f"✨ Самые частые уроки:\n"

        for k, v in sorted(groups.items(), key=lambda x: int(x[0]), reverse=True):
            res += f"\n-- {k} раз(а): {', '.join(v)}; "

        return res

    def search_lesson(self, lesson, days=None):
        """Когда и для кого будет проведён урок.

        :param lesson: Урок, который нужно найти
        :param days: Для каких дней отображать результат поимка

        :returns: Сообщение с результатами поиска."""

        lindex = self.get_lessons_index()
        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))

        if lesson not in lindex:
            return f"❗Неправильно указан предмет.\n🏫 Доступные предметы {len(lindex)}: {'; '.join(lindex)}"


        # Собираем данные
        # ---------------

        data = [[[] for x in range(8)] for x in range(6)]

        for class_let, v in lindex[lesson].items():
            for day, lesson_numbers in enumerate(v):
                for lesson_number in lesson_numbers:

                    data[day][lesson_number].append(class_let)


        # Собираем сообщение
        # ------------------

        res = f"🔎 Поиск {lesson}:"

        for day in days:
            x = data[day]
            day_str = ""

            for i, xx in enumerate(x):
                if xx:
                    tt = ""

                    if i < len(timetable):
                        tt = f'В {timetable[i][0]} '

                    day_str += f"\n{i+1}. {tt}для: {', '.join(xx)}"

            if day_str:
                res += f'\n\n⏰ {days_str[day]}:{day_str}'

        return res 

    def set_class(self, class_let=None):
        """Изменяет класс пользователя.
        :param class_let: Новый класс по умолчанию

        :return: Сообщение о смене класса"""
        
        if class_let in self.lessons:
            self.user["class_let"] = class_let
            self.user["set_class"] = True
            self.user["last_parse"] = self.schedule["last_parse"]
            self.save_user()
            return f'✏ Установлен класс "{class_let}".'
        
        else:
            return f"""🔎 Укажите свой класс в формате "1А".\n🏫 Доступные классы: {'; '.join(self.lessons)}"""

    def print_day_lessons(self, today=0, class_let=None):
        """Сообщение с расписанием уроков на день.
        
        :param today: День недеди (0-5)
        :param class_let: Класс, которому требуется расписание
        
        :return: Сообщение с расписанием на день"""
        
        # Ограничение дней
        if today > 5:
            today = 0
    
        class_let = self.get_class(class_let)
        lessons = self.get_lessons(class_let)[today]["l"]
        res = ""

        # Собираем сообщение с расписанием
        for i, x in enumerate(lessons):
            tt = ""
            if i < len(timetable):
                tt = f" {timetable[i][0]}"
            
            res += f'\n{i+1}{tt} {x[0]} | {x[1]}'

        return res
        
    def print_lessons(self, days=[0], class_let=None):
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

        # Для каких дней получаем расписание
        if days == {0, 1, 2, 3, 4, 5}:
            weekday = "неделю"
        else:
            weekday = ", ".join(map(lambda x: days_str[x], days))
        

        # Собираем сообщение
        # ------------------

        res = f"🏫 Расписание для {class_let} на {weekday}:"

        for day in days:
            res += "\n"
            res += self.print_day_lessons(day, class_let)
        

        # Обновления в расписаниии
        # ------------------------
        
        if class_let == self.user["class_let"]:
            updates = self.get_schedule_changes()
            
            if updates:
                res += f"\n\n🎉 Изменилось расписание!\n"

                updates = updates - days
                if len(updates) < 3:
                    for day in updates:
                        res += f"\n* На {days_str[day]}:{self.print_day_lessons(day)}\n" 
                else:
                    res += f"На {', '.join(map(lambda x: days_str[x], updates))}."

        return res

    def print_today_lessons(self, class_let=None):
        """Получение расписания на сегодня/завтра.
        Есои уроки закончились, выводится расписание на завтра.

        :param class_let: Для какого класса требуется расписание

        :return: Сообщение с расписанием"""

        now = datetime.now()
        today = min(now.weekday(), 5)
        lessons = self.get_lessons(class_let)
        hour = int(timetable[len(lessons[today]["l"])-1][1].split(':')[0])
        
        if now.hour >= hour:
            today += 1 
        
        if today > 5:
            today = 0

        return self.print_lessons(today, class_let)

    def print_status(self):
        last_parse = datetime.fromtimestamp(self.schedule["last_parse"])
        lindex = self.get_lessons_index()

        return f"""SP: ScheduleParser 
Версия: 2.4 (19)
Автор: Milinuri Nirvalen (@milinuri)

* Пользователей: {len(load_file(self.users_path))}
* Проверено в: {self.schedule["updated"]}:00
* Обновлено: {last_parse.strftime("%d %h в %H:%M")}
* Классов: {len(self.lessons)}
* Предметов: ~{len(lindex)}"""
