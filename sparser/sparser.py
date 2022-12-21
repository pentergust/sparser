"""
Самостоятельный парсер школьного расписания уроков.

- Преобразование расписания в удобный формат
- Просмотр расписания
- Сообщение об изменении в расписании
- Статистика по предметам
- Поиск по предмету

Author: Milinuri Nirvalen
Ver: 3.2

Modules:
      os: Проверка существования файлов
    json: Управление файлами
     csv: Чтение CSV файла расписания
 hashlib: Работа с хеш-суммами
requests: Загрузка файла расписания
datetime: Работа с датой и временем
"""

import os
import json
import csv
import hashlib
import requests
from datetime import datetime


# Параметры парсера по умолчанию
# ==============================

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

    :returns: data"""

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


# Работа с расписанием
# ====================

def get_sc_diff(a, b):
    """Делает полное сравнение двух расписаний.
    
    :param a: Пераое расписание уроков (старое)
    :param b: Второе расписание уроков (новое)
    
    :returns: Разница между двумя расписаниями"""

    res = [{} for x in range(6)]

    # Пробегаемся по новому расписанию
    for k, v in b.items():

        # Если класса нет в старом расписании - пропускаем
        if not k in a:
            continue

        av = a[k]

        # Пробегаемся по дням недели в новом расписании
        for d, lessons in enumerate(v):
            if lessons["hash"] == av[d]["hash"]:
                continue

            a_lessons = av[d]["l"]
            
            # n - номер урока; l - название урока
            for n, l in enumerate(lessons["l"]):
                if n >= len(a_lessons):
                    al = ["", ""]
                else:
                    al = a_lessons[n]

                if k not in res[d]:
                    res[d][k] = []

                if l != al: 
                    res[d][k].append([al, l])
                else:
                    res[d][k].append([l, None])

    return res


class ScheduleParser:
    """Парсер школьного расписания уроков
    
    :param uid: User ID - кто работает с расписанием
    :param sc_file: Другой путь к файлу расписания
    :param scu_file: Жругой путь к файлу обновлений расписания
    :param users_file: Лругой путь к файлу пользователей
    """
    
    def __init__(self, uid, sc_file=sc_path, scu_file=sc_updates_path,
                 users_file=users_path):
        super(ScheduleParser, self).__init__()
        self.uid = uid
        self._sc_path = sc_file
        self._scu_path = scu_file
        self._users_path = users_file

        # Получаем данные пользователя и расписание
        self.user = self.get_user()
        self.schedule = self.get_schedule()
        
        # Словарь расписания по классам
        self.lessons = self.schedule["lessons"]
        
        # l_index: Словарь расписания по урокам
        self._l_index = None
        
        # c_index: Словарь расписания по кабинетам
        self._c_index = None

    @property
    def l_index(self):
        """Получает информацию об уроках в расписании.
        Имена уроков, для кого и когда."""

        if not self._l_index:
            res = {}

            for k, v in self.lessons.items():
                for day, lessons in enumerate(v):
                    for n, l in enumerate(lessons["l"]):

                        c = l[1]
                        l = l[0].lower().strip(" .")
                        l = l.replace('-', '=').replace(' ', '-').replace('.-', '.')

                        
                        if l not in res:
                            res[l] = {}

                        if c not in res[l]:
                            res[l][c] = {}


                        if k not in res[l][c]:
                            res[l][c][k] = [[] for x in range(6)]

                        res[l][c][k][day].append(n)

            self._l_index = res
                
        return self._l_index

    @property
    def c_index(self):
        """Получает информацию о кабинетах в расписании.
        Какие уроки проводятся, для кого и когда."""

        if not self._c_index:
            res = {}

            for k, v in self.lessons.items():
                for day, lessons in enumerate(v):
                    for n, l in enumerate(lessons["l"]):

                        cs = l[1].split('/')
                        l = l[0].lower().strip(" .")
                        l = l.replace('-', '=').replace(' ', '-')

                        for c in cs: 
                            if c not in res:
                                res[c] = {}

                            if l not in res[c]:
                                res[c][l] = {}


                            if k not in res[c][l]:
                                res[c][l][k] = [[] for x in range(6)]

                            res[c][l][k][day].append(n)

                self._c_index = res
        
        return self._c_index


    # Управление данными пользователя
    # ===============================

    def get_user(self):
        """Возвращает данные пользователя или данные по умолчанию."""
        return load_file(self._users_path).get(self.uid, user_data)

    def save_user(self):
        """Записывает данные пользователя в self._users_path."""
        users = load_file(self._users_path, {})
        users[self.uid] = self.user
        save_file(self._users_path, users)
        log(f'Write: {self.uid}')

    def get_lessons_updates(self):
        """Возвращает номера дней, для которых изменилось расписание."""
        
        # Если расписание не обновилось, значит и хеши дней тоже
        if self.schedule["last_parse"] == self.user["last_parse"]:
            return []

        sc_changes = load_file(self._scu_path)
        lessons = self.get_lessons()
        days = []

        self.user["last_parse"] = self.schedule["last_parse"]
        self.save_user()
        
        for x in sc_changes["changes"]:
            for day, changes in enumerate(x["diff"]):
                if changes.get(self.user["class_let"]):
                    days.append(day)
 
        return set(days)


    # Получаем расписание
    # ===================

    def _parse_schedule(self, csv_file):
        """Преобразует CSV файл расписания уроков в удобный формат.

        :param csv_file: CSV файл расписания уроков для переработки

        :returns: Переработанный словарь расписания по классам"""
        
        group_log('Parse schedule...')
    
        # class_index: Словарь с классами и их столбцами в расписании
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
                continue


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

                    l = row[v]
                    c = row[v+1]

                    lessons[k][day]["l"][i-dindex[day]] = [l, c]


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

                for i, l in enumerate(day["l"]):
                    if not l[0]:
                        l[0] = "None"
                    if not l[1]:
                        l[1] = "0"


                day["hash"] = h
                n_days.append(day)
            lessons[class_let] = n_days

        return lessons

    def _update_diff_file(self, a, b):
        """Обновляет файл с изменениями расписания.

        :param a: Старое расписание
        :param b: Новое расписание
        """

        log('Update diff file...')

        # Загружаем файл с изменениями
        sc_changes = load_file(self._scu_path)
        day = int(datetime.now().strftime('%j'))        
        
        # Если сменился день, очищаем расписание
        if sc_changes.get("day", 0) != day:
            sc_changes = {"day":day, "changes":[]}

        # Если есть изменения - добавляем файл
        diff = get_sc_diff(a.get("lessons", {}), b["lessons"])
        if sum(map(len, diff)):
            sc_changes["changes"].append({"time": b["last_parse"],
                                          "diff": diff})
        
        save_file(self._scu_path, sc_changes)

    def get_schedule(self, update=False):
        """Получает и обновляет расписание.
        :param update: Принудительное обновление расписания

        :return: Преобразованное расписание уроков"""

        log(f'{"Update" if update else "Get"} {self.uid} schedule')

        now = datetime.now()
        hour = now.hour
        t = load_file(self._sc_path)
        
        # Обновляем данные расписания
        if not t or t.get('updated', 0) != hour or update:
            old_t = t.copy()
            csv_file = requests.get(url).content
            h = hashlib.md5(csv_file).hexdigest()

            if t.get("hash", "") != h or update:
                t["lessons"] = self._parse_schedule(csv_file)
                t["last_parse"] = datetime.timestamp(datetime.now())
                t["hash"] = h

                self._update_diff_file(old_t, t)
            else:
                log("Schedule is up to date")

            t["updated"] = hour
            save_file(self._sc_path, t)    
               
        return t


    # Получение данных из расписания
    # ==============================

    def search(self, target):
        """Поиск данных в расписании.

        :param target: Цель для поиска, кабинет или название урока

        :returns: Результаты поиска"""
        res = {}

        if target in self.c_index:
            index = self.c_index
        else:
            index = self.l_index
        
        if target in index:
            # k - номер кабинета/предмет cs - словарь классов
            for k, cs in index[target].items():
                if k not in res:
                    res[k] = [[[] for x in range(8)] for x in range(6)]

                for class_let, days in cs.items():
                    for day, ns in enumerate(days):
                        for n in ns:
                            res[k][day][n].append(class_let)

        return res

    def get_class(self, class_let=None):
        """Возвращает выбранный класс или класс по умолчанию."""

        if class_let is None or class_let not in self.lessons:
            return self.user["class_let"]

        return class_let

    def get_lessons(self, class_let=None):
        """Получает расписание уроков на неделю для класса."""
        return self.lessons[self.get_class(class_let)]


class SPMessages(ScheduleParser):
    """Генератор текстовых сообщений для ScheduleParser.

    :param uid: User ID - кто работает с расписанием
    :param sc_file: Другой путь к файлу расписания
    :param scu_file: Жругой путь к файлу обновлений расписания
    :param users_file: Лругой путь к файлу пользователей
    """

    def __init__(self, uid, sc_file=sc_path, scu_file=sc_updates_path,
                 users_file=users_path):
        super(SPMessages, self).__init__(uid, sc_file, scu_file, users_file)


    # Прочие сообщения парсера
    # ========================

    def send_sc_changes(self):
        """Отправить измененив в расписании."""

        sc_changes = load_file(self._scu_path)
        res = "Обновления в расписании:"

        # Пробегаемся по измененияв в оасписании
        for x in sc_changes["changes"]:
            
            # Добавляем заголовок изменений
            t = datetime.fromtimestamp(x["time"]).strftime("%H:%M:%S")
            res += f'\n⏰ Примерно в {t}:'

            # Пробегаемся по дням
            for day, changes in enumerate(x["diff"]):
                if changes:
                    res += f"\nНа {days_str[day]}:\n"
                    
                    # Пробегаемся по классам
                    for k, v in changes.items():
                        d_str = "" 

                        # Проьегаемся по урокам
                        for i, l in enumerate(v):
                            o = l[0]
                            n = l[1]

                            if n:
                                d_str += f"\n{i+1}: {n[1]} | {o[0]} -> {n[0]}"
                            else:
                                d_str += f"\n{i+1}: {o[1]} | {o[0]}"

                        res += f"\n🔶 Для {k}:{d_str}\n"

        return res

    def set_class(self, class_let=None):
        """Изменяет класс пользователя.
        :param class_let: Новый класс по умолчанию

        :returns: Сообщение о смене класса"""
        
        if class_let in self.lessons:
            self.user["class_let"] = class_let
            self.user["set_class"] = True
            self.user["last_parse"] = self.schedule["last_parse"]
            self.save_user()
            return f'✏ Установлен класс "{class_let}".'
        
        else:
            return f"""🔎 Укажите свой класс в формате "1А".\n🏫 Доступные классы: {'; '.join(self.lessons)}"""


    # Получение расписания уроков
    # ===========================

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
        res = f"\n🔶 На {days_str[today]}:"

        # Собираем сообщение с расписанием
        for i, x in enumerate(lessons):
            tt = ""
            if i < len(timetable):
                tt = f" {timetable[i][0]}"
            
            res += f'\n{i+1}{tt} {x[1]} | {x[0]}'

        return res
        
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

        res = f"🏫 Расписание для {class_let}:"

        for day in days:
            res += "\n"
            res += self.send_day_lessons(day, class_let)
        

        # Обновления в расписаниии
        # ------------------------
        
        if class_let == self.user["class_let"]:
            updates = self.get_lessons_updates()
            
            if updates:
                res += f"\n\n🎉 Изменилось расписание!\n"

                updates = updates - days
                if len(updates) < 3:
                    for day in updates:
                        res += f"{self.send_day_lessons(day)}\n" 
                else:
                    res += f"На {', '.join(map(lambda x: days_str[x], updates))}."

        return res

    def send_today_lessons(self, class_let=None):
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

        return self.send_lessons(today, class_let)


    # Самые частыек уроки/кабинеты
    # ============================

    def count_lessons(self, class_let=None):
        """Считает частоту уроков в расписании.
        Для всех или определённого класса.

        :param class_let: Для какого класса произвести подсчёт

        :returns: Сообщение с самыми частыми классами"""

        if class_let is not None:
            class_let = self.get_class(class_let)

        res = ""
        groups = {}

        # Считаем частоту предметов
        # -------------------------

        for lesson, v in self.l_index.items():
            
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
            res += f"✨ Самые частые уроки у {class_let}:\n"
        else:
            res += f"✨ Самые частые уроки:\n"

        for k, v in sorted(groups.items(), key=lambda x: int(x[0]), reverse=True):
            res += f"\n\n🔶 {k} раз(а):"

            for lesson, cabinets in v.items():
                if len(v) > 1:
                    res += "\n--"
                
                res += f" {lesson} ("

                for c, n in cabinets.items():
                    if n > 1 and len(cabinets) > 1:
                        res += f" {c}:{n}"
                    else:
                        res += f" {c}"
                
                res += ")"

        return res
       
    def count_cabinets(self, class_let=None):
        """Считает частоту кабинетов в расписании.
        Для всех или определённого класса.

        :param class_let: Для какого класса произвести подсчёт

        :returns: Сообщение с самыми частыми кабинетами"""

        if class_let is not None:
            class_let = self.get_class(class_let)

        res = ""
        groups = {}

        # Считаем частоту предметов
        # -------------------------

        for cabinet, v in self.c_index.items():    
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
            res += f"✨ Самые частые кабинеты у {class_let}:"
        else:
            res += f"✨ Самые частые кабинеты:"

        for k, v in sorted(groups.items(), key=lambda x: int(x[0]), reverse=True):
            res += f"\n\n🔶 {k} раз(а):"

            for cabinet, lessons in v.items():
                if len(v) > 1:
                    res += f'\n--'

                res += f" {cabinet} |"

                for l, n in lessons.items():
                    if n > 1 and len(cabinet) > 1:
                        res += f" {l}:{n};"
                    else:
                        res += f" {l};"
                

        return res
  

    def search_lesson(self, lesson, days=None, class_let=None):
        """Поиск упоминаний о уроке.
        Когда (день), где (кабинет), для кого (класс), каким уроком.

        :param lesson: Урок, который нужно найти
        :param days: Для каких дней отображать результат поиска
        :param class_let: Для какого класса отображать результаты

        :returns: Сообщение с результатами поиска."""

        if lesson not in self.l_index:
            return f"❗Неправильно указан предмет.\n🏫 Доступные предметы: {'; '.join(self.l_index)}"

        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))

        if class_let is not None:
            class_let = self.get_class(class_let)

        data = self.search(lesson)

        # Собираем сообщение
        # ------------------

        search_str = f"🔎 Поиск упоминаний \"{lesson}\""
        if days == {0, 1, 2, 3, 4, 5}:
            search_str += f" за неделю"
        elif days:
            search_str += f" за {', '.join(map(lambda x: days_str[x], days))}"

        if class_let:
            search_str += f" для {class_let}"

        res = search_str

        # Пробегаемся по результатам поиска
        for cabinet, v in data.items():
            cabinet_str = ""

            # Пробегаемся по указанным дням
            for day in days:
                ln = v[day]
                day_str = ""

                for i, cs in enumerate(ln):
                    if class_let and class_let not in cs:
                        continue

                    if cs:
                        tt = ""

                        if i < len(timetable):
                            tt = f'В {timetable[i][0]} '

                        day_str += f"\n{i+1} у. {tt}- {', '.join(cs)}"

                if day_str:
                    cabinet_str += f'\n\n⏰ На {days_str[day]}:{day_str}'
            if cabinet_str:
                res += f"\n\n🔶 Кабинет {cabinet}:{cabinet_str}" 

        return res 

    def search_cabinet(self, cabinet, lesson=None, days=None, class_let=None):
        """Поиск упоминаний о кабинете.
        Когда (день), что (урок), для кого (класс), каким уроком.

        :param cabinet: Кабинет, который нужно найти
        :param lesson: Для какого урока отображать результат
        :param days: Для каких дней отображать результат поиска
        :param class_let: Для какого класса отображать результаты

        :returns: Сообщение с результатами поиска."""

        if cabinet not in self.c_index:
            return f"❗Неправильно указан кабинет.\n🏫 Доступные кабинеты: {'; '.join(self,c_index)}"

        days = set(filter(lambda x: x < 6, days or [0, 1, 2, 3, 4, 5]))

        if class_let is not None:
            class_let = self.get_class(class_let)

        data = self.search(cabinet)

        # Собираем сообщение
        # ------------------

        search_str = f"🔎 Поиск по кабнету {cabinet}"
        if days == {0, 1, 2, 3, 4, 5}:
            search_str += f" за неделю"
        elif days:
            search_str += f" за {', '.join(map(lambda x: days_str[x], days))}"

        if class_let:
            search_str += f" для {class_let}"

        if lesson:
            search_str += f" ({lesson})"

        res = search_str

        # Пробегаемся по результатам поиска
        for l, v in data.items():
            lesson_str = ""

            if lesson and lesson != l:
                continue

            # Пробегаемся по указанным дням
            for day in days:
                ln = v[day]
                day_str = ""

                for i, cs in enumerate(ln):
                    if class_let and class_let not in cs:
                        continue

                    if cs:
                        tt = ""

                        if i < len(timetable):
                            tt = f'В {timetable[i][0]} '

                        day_str += f"\n{i+1} у. {tt}- {', '.join(cs)}"

                if day_str:
                    lesson_str += f'\n\n⏰ На {days_str[day]}:{day_str}'
            if lesson_str:
                res += f"\n\n🔶 Урок {l}:{lesson_str}" 

        return res 

  
    def send_status(self):
        """Возвращает некоторую информауию о парсере."""
        last_parse = datetime.fromtimestamp(self.schedule["last_parse"])
        
        res = "SP: ScheduleParserMessages"
        res += "\nВерсия: 3.0 (22)"
        res += "\nАвтор: Milinuri Nirvalen"
        res += f"\n\n* Класс: {self.user['class_let']}"
        res += f"\n\n* Пользователей: {len(load_file(self._users_path))}"
        res += f"\n* Проверено в: {self.schedule['updated']}:00"
        res += f"\n* Обновлено: {last_parse.strftime('%d %h в %H:%M')}"
        res += f"\n* Классов: {len(self.lessons)}"
        res += f"\n* Предметов: ~{len(self.l_index)}"
        res += f"\n* Кабинетов: ~{len(self.c_index)}"

        return res
