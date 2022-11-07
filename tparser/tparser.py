"""
Самостоятельный парсер школьного расписания.
Умеет запоминать пользователей и сообщать об изменениях в расписании.

Author: Milinuri Nirvalen
Ver: 1.6

Modules:
      os: Проверка существования файлов
    json: Управление файлами
     csv: Чтение CSV файла расписания
requests: Получение файла расписания
 hashlib: Работа с хеш-суммами
datetime: Работа с датой
"""

import os
import json
import csv
import hashlib
import requests
from datetime import datetime


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
user_data = {"class_let":"9г", "day_hashes":[None, None, None, None, None, None]}
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
        f.write(json.dumps(data, indent=4))
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
    :param custom_sc_path: Нестандартный путь к файлу расписания
    :param custom_users_path: Неcтандартный путь к файлу пользователей
    """
    
    def __init__(self, uid, custom_sc_path=sc_path,
                 custom_users_path=users_path):
        super(ScheduleParser, self).__init__()
        self.uid = uid
        self.sc_path = custom_sc_path
        self.users_path = custom_users_path

        # Получаем данные пользователя и расписание
        self.user = self.get_user()
        self.schedule = self.get_schedule()["schedule"]


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
        #          sc: Словарь расписания sc[КЛАСС][ДЕНЬ][УРОК]
        #      dlines: Указание строки начала дней
        #     lessons: Максимальное кол-во урокеов в день
        #     lt_line: Строка с расписаним звонков
        #          lt: Расписание звонков [[Начало, Конец], [...], ...]

        class_index = {}
        sc = {}
        dlines = [3, 11, 19, 27, 35, 43, 49]
        d = 0
        lessons = 8
        lt_line = 52
        
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

            if d < len(dlines)-2 and i == dlines[d]+lessons:    
                d += 1 

            if i >= dlines[d] and i < min(dlines[d]+lessons, dlines[-1]):
                    
                # Пробегаемся по всем класаам
                for k, v in class_index.items():
                        
                    # Если класса нет в расписании, то добавляем его
                    if k not in sc:
                        sc[k] = [{"lessons":["" for x in range(lessons)],
                                        "hash": None} for x in range(6)]

                    sc[k][d]["lessons"][i-dlines[d]] = f"{row[v]} | {row[v+1]}"


        # Получаем хеши дней
        # ==================

        log('-> Get day hsshes...')
        for class_let, days in sc.items():
            n_days = []
            
            for day in days:
                h = hashlib.md5(bytearray(f";".join(day["lessons"]),
                                          'utf-8')).hexdigest()
                day["hash"] = h
                n_days.append(day)
            sc[class_let] = n_days

        return sc

    def get_schedule(self, update=False):
        """Получает и обновляет расписание.
        :param update: Принудительное обновление расписания

        :return: Преобразованное расписание уроков"""

        log(f'{"Update" if update else "Get"} {self.uid} schedule')

        hour = datetime.now().hour        
        t = load_file(self.sc_path)
        
        # Обновляем данные расписания
        if not t or t.get('updated', 0) != hour or update:
            csv_file = requests.get(url).content
            h = hashlib.md5(csv_file).hexdigest()

            if t.get("hash", "") != h or update:
                t["schedule"] = self.parse_schedule(csv_file)
                t["hash"] = h
            else:
                log("Schedule is up to date")

            t["updated"] = hour
            save_file(self.sc_path, t)    
               
        return t

    
    # Взаимодействуем с расписанием
    # =============================

    def get_class(self, class_let=None):
        """Возвращает выбранный класс или класс по умолчанию."""

        if class_let is None or class_let not in self.schedule:
            return self.user["class_let"]

        return class_let

    def get_lessons(self, class_let=None):
        """Получает расписание уроков на неделю для класса."""
        class_let = self.get_class(class_let)
        return self.schedule[class_let]

    def get_schedule_changes(self):
        """Возвращает номера дней, для которых изменилось расписание."""
        lessons = self.get_lessons()
        days = []

        for i, x in enumerate(self.user["day_hashes"]):
            if x != lessons[i]["hash"]:
                self.user["day_hashes"][i] = lessons[i]["hash"]

                if x:
                    days.append(i)
                    
        if days:
            self.save_user()

        return days


    # Методы представления
    # ====================

    def set_class(self, class_let=None):
        """Изменяет класс пользователя.
        :param class_let: Новый класс по умолчанию

        :return: Сообщение о смене класса"""
        
        if class_let in self.schedule:
            self.user["class_let"] = class_let
            self.user["day_hashes"] = list(map(lambda x: x["hash"],
                                               self.get_lessons(class_let)))
            self.save_user()
            return f"✏ Класс изменён на \"{class_let}\"!"
        
        else:
            return f"""❗Класс указан неправильно.
🔎 Введиие свой класс в формате "1А"
🏫 Доступные классы: {'; '.join(self.schedule)}"""

    def print_day_lessons(self, today=0, class_let=None):
        """Сообщение с расписанием уроков на день.
        
        :param today: День недеди (0-5)
        :param class_let: Класс, которому требуется расписание
        
        :return: Сообщение с расписанием на день"""
        
        # Ограничение дней
        if today > 5:
            today = 0
    
        lessons = self.get_lessons(class_let)[today]["lessons"]
        res = "\n"

        # Пропускаем пустые уроки с конца
        while True:
            l = lessons[-1].split("|")[0].strip() 
            if not l or l == "---":
                lessons.pop()
                continue

            break
        
        # Собираем сообщение с расписанием
        for i, x in enumerate(lessons):
            tt = ""

            if x.strip() == "|":
                x = "---"

            if i < len(timetable):
                tt = f" {timetable[i][0]}"
            
            res += f'\n{i+1}{tt} {x}'

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

        temp = []
        for d in days:
            if d > 5:
                d = 0
    
            if d not in temp:
                temp.append(d)

        days = sorted(temp)
        
        # Для каких дней получаем расписание
        if days == [0, 1, 2, 3, 4, 5]:
            weekday = "неделю"
        else:
            weekday = ", ".join(map(lambda x: days_str[x], days))
        

        # Собираем сообщение
        # ------------------

        res = f"🏫 {class_let} расписание на {weekday}:"

        for day in days:
            res += self.print_day_lessons(day, class_let)
        
        if class_let == self.user["class_let"]:
            updates = self.get_schedule_changes()

            if updates:
                weekday = ", ".join(map(lambda x: days_str[x], updates))
                res += f"\n\nИзменилось расписание на {weekday}!"

                for day in updates:
                    # Пропускаем, если расписание уже получено
                    if day in days:
                        continue
                        
                    res += self.print_day_lessons(day, class_let)
                
        return res

    def print_today_lessons(self, class_let=None):
        """Получение расписания на сегодня/завтра.
        Есои уроки закончились, выводится расписание на завтра.

        :param class_let: Для какого класса требуется расписание

        :return: Сообщение с расписанием"""

        now = datetime.now()
        today = now.weekday()

        if today < 6:
            lessons = self.get_lessons(class_let)
            hour = int(timetable[len(lessons[today]["lessons"])-1][1].split(':')[0])
            
            if now.hour >= hour:
                today += 1 
        else:
            today = 0

        return self.print_lessons(today, class_let)
