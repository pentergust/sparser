"""Самостоятельный парсер школьного расписания.

Предоставялет компоненты, используемые для
получения расписания и последующей работы с ним.

Содержит:

- Функция для сравнения двух расписаний.
- Функция получения индекса.
- Класс Schedule для работы с самим расписанием.
"""

import csv
import hashlib
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import requests
from loguru import logger

from .intents import Intent
from .utils import load_file, save_file

url = "https://docs.google.com/spreadsheets/d/1pP_qEHh4PBk5Rsb7Wk9iVbJtTA11O9nTQbo1JFjnrGU/export?format=csv"
SC_PATH = Path("sp_data/sc.json")
SC_UPDATES_PATH = Path("sp_data/updates.json")
INDEX_PATH = Path("sp_data/index.json")


# Вспомогательные функции
# =======================

def _get_day_hash(day_lessons: list) -> str:
    return hashlib.md5(("".join(day_lessons)).encode()).hexdigest()

def _clear_day_lessons(day_lessons: list[str]) -> list[str]:
    """Удаляет все пустые уроки с конца списка."""
    while day_lessons:
        lesson = day_lessons[-1].split(":")[0]
        if lesson or lesson not in ("---", "None"):
            return day_lessons
        else:
            day_lessons.pop()
    return []


def get_sc_updates(
    a: dict[str, list], b: dict[str, list]
) -> list[dict[str, list]]:
    """Делает полное сравнение двух расписаний.

    Делает полное построчное сравнение старого и нового расписания.
    Возвращает все найденные изменения в формате.

    .. code-block:: json

        [
            // дни ...
            {
                // классы ...
                "9в" [
                    // уроки ...
                    null, // Ничего не изменилось
                    ["старый:12", "новый:132"] // Предмет изменился
                ]
            }
        ]

    :param a: Исходное расписание для сравнения.
    :type a: dict[str, list]
    :param b: Другое расписание для сравнения с исходным.
    :type b: dict[str, list]
    :return: Результаты поиска изменения в расписании.
    :rtype: list[dict[str, list]]
    """
    updates: list[dict] = [defaultdict(lambda: [None] * 8) for x in range(6)]
    # Проходимся по классам в новом расписании
    for k, v in b.items():
        if k not in a:
            continue

        # Пробегаемся по дням недели в новом расписании
        av = a[k]
        for day, lessons in enumerate(v):
            if _get_day_hash(lessons) == _get_day_hash(av[day]):
                continue

            a_lessons = av[day]
            for i, lesson in enumerate(lessons):
                al = a_lessons[i] if i <= len(a_lessons)-1 else None
                if lesson != al:
                    updates[day][k][i] = (al, lesson)
    return updates

def get_index(
    sp_lessons: dict[str, list[str]],
    lessons_mode: Optional[bool]=True
) -> dict[str, list[dict]]:
    """Преобразует словарь расписания уроков в индекс.

    В данном случае индексом называется словарь, где ключом вместо
    класса является название урока или кабинета.

    Они так же часто используются, как и само расписание.
    Например при подсчёте количества элементов или при поиске в
    расписании определённого урока или кабинета.

    **Описание индексов**:

    - Расписание: `[Класс][День][Уроки]`
    - l_mode True: `[Урок][День][Кабинет][Класс][Номер урока]`
    - l_mode False: `[Кабинет][День][Урок][Класс][Номер урока]`

    :param sp_lessons: Словарь расписания уроков.
    :type sp_lessons: dict[str, list[str]]
    :param lessons_mode: Режим получени индекса уроков. По умолчанию да.
    :type lessons_mode: Optional[bool]
    :return: Индекс уроков или кабинетов.
    :rtype: dict[str, list]
    """
    logger.info("Get {}_index", "l" if lessons_mode else "c")
    index: dict[str, list[dict]] = defaultdict(
        lambda: [defaultdict(
            lambda: defaultdict(list)
        ) for x in range(6)]
    )

    # res = {}
    for cl, v in sp_lessons.items():
        for day, lessons in enumerate(v):
            for n, lesson_data in enumerate(lessons):
                lesson, cabinet = lesson_data.lower().split(":")
                lesson = lesson.strip(" .")
                for old, new in [('-', '='), (' ', '-'), (".-", '.')]:
                    lesson = lesson.replace(old, new)

                # Obj - Первичный ключ индекса, урок или кабинет.
                # another - = Вторичный ключ, противоположый первичному.
                obj = [lesson] if lessons_mode else cabinet.split("/")
                another = cabinet if lessons_mode else lesson

                for x in obj:
                    index[x][day][another][cl].append(n)
    return index


def parse_lessons(csv_file: str) -> dict[str, list[list[str]]]:
    """Пересобирает CSV файл в словарь расписания.

    Расписание в CSV файле представленно подобным образом.

    .. code-block::

        +--+-------+---------+
        |  | класс |         | <- Шапка с классами в расписание
        +--+-------+---------+
        | 1| урок  | кабинет | <- Первый урок понедельника.
        | n| ...   | ...     |
        +--+-------+---------+
        | 1| урок  | кабинет | <- Первый урок вторника.
        | n| ...   | ...     |
        +--+-------+---------+

    Задача этой функции преобразовать таблицу выше в словарь расписания
    уроков формата:

    .. code-block:: json

        {
            // Классы
            "класс" {
                // Дни
                [
                    // Уроки в днях
                    "урок:кабинет"
                ]
            }
        }

    :param csv_file: Данные CSV файла расписания.
    :type csv_file: bytes
    :return: Словарь расписания уроков.
    :rtype: dict[str, list[str]]
    """
    logger.info("Start parse lessons...")

    # lessons: Словарь расписания [Класс][День]
    lessons: dict[str, list] = defaultdict(lambda: [[] for x in range(6)])
    day = -1
    last_row = 8
    reader = csv.reader(csv_file.splitlines())

    # Получает кортеж с именем класса и индексом
    # соответствующего столбца расписания
    next(reader)
    cl_header = [(cl.lower(), i)
        for i, cl in enumerate(next(reader)) if cl.strip()
    ]

    # Построчкно читаем расписание уроков
    for row in reader:
        # Первый элемент строки указывает на день недели.
        if len(row[0]) > 0:
            logger.info("Process group {} ...", row[0])

        # Если второй элемент в ряду указывает на номер урока
        if row[1].isdigit():
            # Если вдруг номер урока стал меньше, начался новый день
            if int(row[1]) < last_row:
                day += 1
            last_row = int(row[1])

            logger.debug("Row: {}", row)
            for cl, i in cl_header:
                # Если класса нет в расписании, то добавляем его
                logger.debug("{}:{}", row[i], row[i+1])
                lesson = row[i].strip(" .-").lower() or None
                cabinet = row[i+1].strip().lower() or 0
                lessons[cl][day].append(f"{lesson}:{cabinet}")

        elif day == 5: # noqa
            logger.info("CSV file reading completed")
            break

    return {k: [
        _clear_day_lessons(x) for x in v
    ] for k, v in lessons.items()}


class Schedule:
    """Предоставляет доступ к расписанию уроков.

    В первую очередь занимается получение расписания из гугл таблиц.
    Отслеживает изменения в расписании и записывает их в файл.
    Вы можете получить расписание для конкретного класса,
    произвести полный поиск по урокам или кабинетам, использую фильтры,
    получить список изменений в расписании, также с возможностью
    отфильтровать результаты поиска.
    Тажке предосталвяет доступ к индексам расписания.

    :param cl: Ваш класс по умолчанию.
    :type cl: Optional[str]
    :param sc_path: Ваш путь к файлу расписания.
    :type sc_path: Optional[Union[Path, str]]
    :param updates_path: Ваш путь к файлу списка изменений расписания.
    :type updates_path: Optional[Union[Path, str]]
    :param index_path: Ваш путь для сохранения индексов расписания.
    :type index_path: Optional[Union[Path, str]]
    """

    def __init__(self, cl: Optional[str]=None,
        sc_path: Union[Path, str]=SC_PATH,
        updates_path: Union[Path, str]=SC_UPDATES_PATH,
        index_path: Union[Path, str]=INDEX_PATH,
    ) -> None:
        super().__init__()
        self.cl = cl

        # Определение путей к файлам.
        self.sc_path = Path(sc_path)
        self.updates_path = Path(updates_path)
        self.index_path = Path(index_path)

        # Определнеи индексов расписания.
        self._l_index = None
        self._c_index = None
        self._updates = None

        self.schedule = self.get()
        self.lessons = self.schedule["lessons"]

    @property
    def l_index(self) -> Optional[dict[str, list[dict]]]:
        """Индекс уроков.

        Загружает индекс урокво из файла.
        Индекс урока предоставляет изменённый словарь расписания,
        где вместо ключа используется название урока, а не класс.

        Пример структуры индекса:

        .. code-block:: json

            {
                "матем": [
                    { // Понедельник ...
                        "204" { // Каибнет
                            "8в" [ // класс
                                3 // Номер урока
                            ]
                        }
                    },
                    {}, // Вторник ...
                    {}, // Среда ...
                    {}, // ...
                    {},
                    {},
                ]
            }

        :return: Полный индекс уроков.
        :rtype: dict[str, list[dict]]
        """
        if self._l_index is None:
            self._l_index = load_file(self.index_path)[0]
        return self._l_index

    @property
    def c_index(self) -> Optional[dict[str, list[dict]]]:
        """Индекс кабинетов.

        Загружает индекс уроков из файла.
        Индекс кабинетов предоставляет изменённый словарь расписания,
        где вместо ключа используется название кабинета, а не класс.

        Пример структуры индекса:

        .. code-block:: json

            {
                "204": [
                    { // Понедельник ...
                        "матем" { // Каибнет
                            "8в" [ // класс
                                3 // Номер урока
                            ]
                        }
                    },
                    {}, // Вторник ...
                    {}, // Среда ...
                    {}, // ...
                    {},
                    {},
                ]
            }

        :return: Полный индекс уроков.
        :rtype: dict[str, list[dict]]
        """
        if not self._c_index:
            self._c_index = load_file(self.index_path)[1]
        return self._c_index

    @property
    def updates(self) -> Optional[list[dict[str, Union[int, dict]]]]:
        """Список изменений в расписании.

        Загружает полный список изменений из файла.
        Список изменений представляет собой список из последних
        30-ти записях об изменениях в расписании.

        Каждая запись содержит начало и конец временрого отрезка,
        когда были зафиксированы изменеия.
        Также каждая запись содержит полный список изменений.

        Пример одной из записи:

        .. code-block:: json

            {
                "start_time": 1703479133.752195,
                "end_time": 1703486843.468643,
                "updates": [ // Дни недели
                    {
                        "5а": [ // Классы ...
                            [ // Изменение в расписании
                                "тфк:110", // Старый урок:класс
                                "None:110" // Новый урок:класс
                            ],
                            null, // Если уроки не изменились
                            null,
                            null,
                            null,
                            null,
                            null,
                            null
                        ],
                    },
                    {}, // Вторик ...
                    {}, // Среда ...
                    {}, // ...
                    {},
                    {}
                ]
            }

        :return: Полный список изменений в расписании.
        :rtype: list[dict[str, Union[int, dict]]]
        """
        if self._updates is None:
            self._updates = load_file(self.updates_path)
        return self._updates


    # Получаем расписание
    # ===================

    def _update_diff_file(
        self,
        a: dict[str, Union[list, int, str]],
        b: dict[str, Union[list, int, str]]
     ) -> None:
        """Обновляет файл списка изменений расписания.

        Производит сравнение старого и нового расписнаия.
        После сравнения вносит найдкнные изменений в файл.

        :param a: Исходное расписание.
        :type a: dict[str, Union[list, int, str]]
        :param b: Новое расписание уроков.
        :type b: dict[str, Union[list, int, str]]
        """
        logger.info("Update diff file ...")
        sc_changes = deque(load_file(self.updates_path, []), 30)
        updates = get_sc_updates(a.get("lessons", {}), b["lessons"])
        if sum(map(len, updates)):
            if len(sc_changes):
                start_time = sc_changes[-1]["end_time"]
            else:
                start_time = b["last_parse"]

            sc_changes.append({
                "start_time": start_time,
                "end_time": b["last_parse"],
                "updates": updates}
            )
            save_file(self.updates_path, list(sc_changes))

    def _update_index_files(self, sp_lessons: dict[str, list]) -> None:
        """Обновляет файл индексов.

        :param sp_lessons: Расписание уроков.
        :type sp_lessons: dict[str, list]
        """
        logger.info("Udate index files...")
        save_file(self.index_path,
            [get_index(sp_lessons), get_index(sp_lessons, False)]
        )

    def _process_update(self, t: dict[str, Union[list, int, str]]) -> None:
        """Полное обновление расписания, индексов, файла обновлений.

        Производит полное обновление расписания уроков.
        Загружает файл csv файла расписания.
        Если хеши не отличаются, устанавливаем время следующей
        проверки и завершаем работу.

        Если расписание изменилось, парсим новое расписние из
        csv файла, получаем файл индексов и обновляем список
        изменений.

        :param t: Текущее расписание уроков.
        :type t: dict[str, Union[list, int, str]]
        """
        logger.info("Start schedule update ...")
        now = datetime.now()
        timestamp = int(datetime.timestamp(now))

        # Скачяиваем файла с расписанием
        try:
            logger.info("Download schedule csv_file ...")
            csv_file = requests.get(url).content
        except Exception as e:
            logger.exception(e)

            # Откладываем обновление на минуту
            t["next_update"] = timestamp+60
            save_file(self.sc_path, t)
        else:
            h = hashlib.md5(csv_file).hexdigest()

            # Сравниваем хеши расписаний
            if t.get("hash", "") == h:
                logger.info("Schedule is up to date")
                t["last_parse"] = timestamp + 1800
                save_file(self.sc_path, t)
            else:
                lessons = parse_lessons(csv_file.decode("utf-8"))
                self._update_index_files(lessons)

                # Собираем новое расписанеи уроков
                new_t = {
                    "hash": h,
                    "lessons": lessons,
                    "last_parse": timestamp,
                    "next_parse": timestamp+1800
                }

                self._update_diff_file(t, new_t)
                save_file(self.sc_path, new_t)


    def get(self) -> dict[str, Union[int, dict, str]]:
        """Получает расписание уроков.

        Если расписание уроков пустое или таймёр истёк, запускает
        процесс обновления.

        **Процесс обновления**:

        - Загрузка файла расписания.
            - Если не удалосью, передвигаем метку обновления.
        - Сравниваем хеши расписаний.
        - Если различаются:
            - Парсим расписание из файла.
            - Обновляем индексы расписания.
            - Отслеживает и записывает изменения в расписании.
        - Сдвигаем временнцую метку следующего обновления.

        Расписание уроков представляет собой словарь:

        - `hash`: Хеш сумма рсписания уроков.
        - `last_parse`: Unixtime посленей проверки расписания.
        - `next_parse`: Ubixtume следующей проверки расписания.
        - `lessons`: Сам словарь расписаний уроков по классам.

        :return: Словарь данных расписания уроков.
        :rtype: dict[str, Union[int, dict, str]]
        """
        now = datetime.timestamp(datetime.now())
        t = load_file(self.sc_path)

        if not t or t.get("next_update", 0) < now:
            self._process_update(t)

        return t


    # Получение данных из расписания
    # ==============================

    def get_class(self, cl: str) -> str:
        """Получает класс из расписания.

        .. deprecated:: 5.7 Этот метод будет вскоре удалён

            Лучшще используйте вместо этого:

            .. code-block:: python

                if cl in sp.lessons: ...
        """
        return cl if cl in self.lessons else self.cl

    def get_lessons(self, cl: Optional[str]=None) -> list[list[str]]:
        """Получает полное расписание уроков для указанного класса.

        :param cl: Для какого класса получить расписание.
        :type cl: str
        :return: расписание уроков на неделю.
        :rtype: list[list[str]]
        """
        if cl is None:
            cl = self.cl

        return self.lessons.get(cl, [[], [], [], [], [], []])

    def get_updates(self, intent: Intent, offset: Optional[int]=None
    ) -> list[dict[str, Union[int, dict]]]:
        """Получает список изменений расписания.

        Проходится по списку обновленй в расписании.
        Для уточнения результата использует намерения.
        К примеру, получить все изменения на вторник.
        Ну или же для определённого класса.

        :param intent: Намерения для уточнения результатов.
        :type intent: Intent
        :param offset: С какой временной метки обновления начать.
        :type offset: int
        :return: Список обновлений расписания.
        :rtype: list[dict[str, Union[int, dict]]]
        """
        updates = []

        # Пробегаемся по списку обновлений
        for update in self.updates:
            if update is None:
                continue

            # Пропускаем обновления согласно сдвигу
            if offset is not None and update["end_time"] < offset:
                continue

            # Собираем новый список изменений, используя намерения
            new_update = [{} for x in range(6)]
            for day, day_updates in enumerate(update["updates"]):
                if intent.days and day not in intent.days:
                    continue

                for cl, cl_updates in day_updates.items():
                    if intent.cl and cl not in intent.cl:
                        continue

                    new_update[day][cl] = cl_updates

            # Если в итоге какие-то обновления есть - добавляем
            if sum(map(len, new_update)):
                updates.append({
                    "start_time": update["start_time"],
                    "end_time": update["end_time"],
                    "updates": new_update
                })

        return updates

    def search(
        self, target: str, intent: Intent,
        cabinets: Optional[bool]=False
    ) -> list[list[list[str]]]:
        """Производит поиск в расписании.

        Для поиска цели в индексах расписания.
        Сама же цель - название кабинета или урока.
        Для уточнения результатов поиска используются намерения.
        Например чтобы получить результаты на опрелдённый день.
        Ну или к примеру в определённых кабинетах, если речь об уроке.

        Поиск немного изменяется в зависимости от режима.

        .. table::

            +----------+---------+---------+
            | cabinets | obj     | another |
            +==========+=========+=========+
            | false    | lesson  | cabinet |
            +----------+---------+---------+
            | true     | cabinet | lesson  |
            +----------+---------+---------+

        Результат поиска возаращем подобный расписанию формат.

        .. code-block:: json

            [ // Дни
                [ // Уроки (по умолчанию 8)
                    [ // Найдённые результаты
                        "{cl}",
                        "{obj}",
                        "{cl}:{obj}",
                        "..."
                    ],
                    [], // Если список пустой - ничего не найдено
                    [],
                    [],
                    [],
                    [],
                    [],
                    []
                ],
                [], // Вторник ...
                [], // Среда ...
                [], // ...
                [],
                []
            ]

        Как вы могли заметить, результат поиска - строка.
        Формат строки зависит от некоторых условий:

        - `{cl}` - Если в намерении 1 кабинет и указаны уроки.
        - `{obj}` - Если в намерении 1 класс (опускаем описание класса).
        - `{cl}:{obj}` - Для всех прочих случаев.

        :param target: Цель для поиска, урок или кабинет.
        :type target: str
        :param cabinets: Что ищём, урок или кабинет. Обычно урок.
        :type cabinets: bool
        :return: Результаты поиска в расписании
        """
        res = [[[] for x in range(8)] for x in range(6)]

        # Определяем какой индекс использовать
        if cabinets:
            index = self.c_index.get(target, {})
        else:
            index = self.l_index.get(target, {})

        # Пробегаемся по индексу
        for day, objs in enumerate(index):
            if intent.days and day not in intent.days:
                continue

            for obj, another in objs.items():
                if cabinets and intent.lessons and obj not in intent.lessons:
                    continue

                for cl, i in another.items():
                    if intent.cl and cl not in intent.cl:
                        continue

                    for x in i:
                        if len(intent.cabinets) == 1 and len(intent.lessons):
                            res[day][x].append(f"{cl}")
                        elif len(intent.cl) == 1:
                            res[day][x].append(f"{obj}")
                        else:
                            res[day][x].append(f"{cl}:{obj}")
        return res
