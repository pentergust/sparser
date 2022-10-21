"""
Самостоятельный парсер школьного расписания.
Умеет запоминать пользователей и сообщать об изменениях в расписании.

Author: Milinuri Nirvalen
Ver: 1.4

Modules:
    os: Провенрка существования файлов
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
"""

url = "https://docs.google.com/spreadsheets/d/1pP_qEHh4PBk5Rsb7Wk9iVbJtTA11O9nTQbo1JFjnrGU/export?format=csv"
users_path = "users.json"
sc_path = "sc.json"
user_data = {"class_let":"9г", "day_hashes":[None, None, None, None, None, None]}
days_str = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу"]


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

def log(text):
    """Отправка сообщений о датой в консоль.
    :param text: Текст сообщения"""

    now = datetime.now().strftime("%H:%M:%S")
    print(f'\033[90m{now} \033[93m[SP] \033[32m{text}\033[0m')


class ScheduledParser:
    """Парсер школьного расписание
    
    :param uid: User ID или кто работает с расписанием
    :param custom_sc_path: Не стандартный путь к файлу расписания
    :param custom_users_path: Не стандартный путь к файлу пользователей
    """
    
    def __init__(self, uid, custom_sc_path=sc_path,
                 custom_users_path=users_path):
        super(ScheduledParser, self).__init__()
        self.uid = uid
        self.sc_path = custom_sc_path
        self.users_path = custom_users_path

        # Получаем данные пользователя и расписание
        self.user = self.get_user()
        self.schedule = self.get_schedule()


    # Вспомогательные методы
    # ======================

    def get_user(self):
        """Возвращает данные пользователя или данные по умолчанию."""
        return load_file(self.users_path).get(self.uid, user_data)

    def save_user(self):
        """Записывает данные пользователя в self.users_path."""

        users = load_file(self.users_path, {})
        users[self.uid] = self.user
        save_file(self.users_path, users)
        log(f'Write: {self.uid}')


    def get_day_hashes(self, class_let=None):
        """Получчает хеши уроков за каждый день недели.
        :param class_let: Класс для которого нужно получить хеши

        :returns: Список хешей уроков для каждого дня"""

        if class_let is None:
            class_let = self.user["class_let"]

        return list(map(lambda x: x["hash"],
                        self.schedule["schedule"][class_let]))

    def get_diff_day_hashes(self, class_let=None):
        """Получает разницу в хешах дней.

        :return: Номера дней, для которых изменилось расписание"""

        day_hashes = self.get_day_hashes(class_let)
        res = []

        for i, x in enumerate(self.user["day_hashes"]):
            if x != day_hashes[i]:
                if x is not None:
                    res.append(i)
                    
                self.user["day_hashes"][i] = day_hashes[i]

        if res:
            self.save_user()

        return res


    # Парсер расписания
    # =================

    def parse_schedule(self, update=False):
        """Хрупкий парсер школьного распеисания.
        Преобразует CSV файл в удобный формат

        :param update: Принудительное обновление файла

        :return: Преобразованное расписание"""
        
        log('Get schedule file...')
        res = load_file(self.sc_path, {})
        
        r = requests.get(url).content
        h = hashlib.md5(r).hexdigest()
        
        res["updated"] = datetime.now().hour

        if res.get("hash", "") == h and not update:
            log('Schedule is uptime!')
            return res

        res["hash"] = h
        
        # Вспомогательные переменные
        # -------------------------
        # class_index: Словарь с классами и их столбцам в расписании
        #   sc: Словарь расписания sc[КЛАСС][ДЕНЬ][УРОК]
        #   dlines: Указание строки начала дней
        # lessons: Максимальное кол-во урокеов в день
        #     lt_line: Строка с расписаним звонков
        #          lt: Расписание звонков [[Начало, Конец], [...], ...]
        
        class_index = {}
        sc = {}
        dlines = [3, 11, 19, 27, 35, 43, 49]
        d = 0
        lessons = 8
        lt_line = 52

        
        log('-> Read CSV file...')
        reader = csv.reader(r.decode("utf-8").splitlines(), delimiter=',')

        # Построчно читаем CSV файл расписания
        # i - номер (индекс) строки, row - содержимое строки
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

        # получение хешей дней
        # ====================

        log('-> Get day hsshes...')
        for class_let, days in sc.items():
            n_days = []
            
            for day in days:
                

                h = hashlib.md5(bytearray(f";".join(day["lessons"]),
                                          'utf-8')).hexdigest()
                day["hash"] = h
                n_days.append(day)
            sc[class_let] = n_days

        res["schedule"] = sc
        
        return res

    def get_schedule(self, update=False):
        """Получаем и обновляем расписание.

        :param update: Принудительное обновление расписания

        :return: Словарь расписания уроков"""

        t = load_file(self.sc_path)
        hour = datetime.now().hour
        
        if not t or t.get('updated', 0) != hour or update:
            t = self.parse_schedule(update)
            if t is not None:
                save_file(self.sc_path, t)
               
        return t


    # Методы представления
    # ====================

    def set_class(self, class_let=None):
        """Изменяет класс пользователя.

        :param class_let: Новый класс по умолчанию

        :return: Сообщение о смене класса"""
        
        if class_let in self.schedule["schedule"]:
            self.user["class_let"] = class_let
            self.user["day_hashes"] = self.get_day_hashes()
            self.save_user()
            return f"✏ Класс изменён на \"{class_let}\"!"
        
        else:
            return f"""❗Номер класса введён неверно!
✏ Пожалуйста исправьте ошибку!
🔎 Введиие номер своего класса в формате: \"1А\"

🏫 Доступные классы: {', '.join(self.schedule['schedule'])}"""

    def get_day_lessons(self, today=0, class_let=None):
        """Получает расписание уроков на день.
        
        :param today: День недеди (0-5)
        :param class_let: Класс, для которого нужно получить расписание
        
        :return: Строковое расписание на день"""
        
        # Ограничение дней
        if today > 5:
            today = 0
    
        lessons = self.schedule["schedule"][class_let][today]["lessons"]
        res = "\n"

        # Пропускаем пустые уроки с конца списка
        while True:
            l = lessons[-1].split("|")[0].strip() 
            if not l or l == "---":
                lessons.pop()
            else:
                break
        
        for i, x in enumerate(lessons):
            if not x:
                continue

            if x.strip() == "|":
                x = "---"

            res += f'\n{i+1}. {x}'

        return res
        
    def get_lessons(self, days=[0], class_let=None):
        """Получает расписание уроков.

        :param days: Дни недели, для которых нужно расписание
        :param class_let: Класс, для которого нужно расписание

        :return: Сообщение с расписанием"""

        if isinstance(days, int):
            days = [days]     
        
        # Проверка правильности класса
        if class_let is None or class_let not in self.schedule["schedule"]:
            class_let = self.user["class_let"]

        weekday = ", ".join(map(lambda x: days_str[x], days))
        res = f"🏫 {class_let} расписание на {weekday}:"

        for day in days:
            res += self.get_day_lessons(day, class_let)
        
        if class_let == self.user["class_let"]:
            
            updates = self.get_diff_day_hashes(class_let)

            if updates:
                weekday = ", ".join(map(lambda x: days_str[x], updates))
                res += f"\n\nИзменилось расписание на {weekday}:"

                for day in updates:
                    if day in days:
                        continue
                        
                    res += self.get_day_lessons(day, class_let)
                

        return res

