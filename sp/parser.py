"""Самостоятельный парсер школьного расписания.

Содержит компоненты, связанные с получением расписания.
Такие как получение расписание, его кеширование, отслеживание
изменений, сборка индекс и поиск по расписанию.

Содержит:

- Функция для сравнения двух расписаний.
- Функция получения индекса.
- функция получения расписания.
- Методы кеширования расписания.
- Класс Schedule для работы с расписанием и его сохранением.
"""

import csv
import hashlib
from collections import defaultdict, deque
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

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
        if lesson and lesson not in ("---", "None"):
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
    lessons_mode: bool | None=True
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
    :param lessons_mode: Режим получения индекса уроков. (уроки).
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
                # another - = Вторичный ключ, противоположный первичному
                obj = [lesson] if lessons_mode else cabinet.split("/")
                another = cabinet if lessons_mode else lesson

                for x in obj:
                    index[x][day][another][cl].append(n)
    return index


def parse_lessons(csv_file: str) -> dict[str, list[list[str]]]:
    """Разбирает CSV файл в словарь расписания.

    Расписание в CSV файле представлено подобным образом.

    .. code-block:: text

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

    # построчно читаем расписание уроков
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

            for cl, i in cl_header:
                # Если класса нет в расписании, то добавляем его
                lesson = row[i].strip(" .-").lower() or None
                cabinet = row[i+1].strip().lower() or 0
                lessons[cl][day].append(f"{lesson}:{cabinet}")

        elif day == 5: # noqa
            logger.info("CSV file reading completed")
            break

    return {k: [
        _clear_day_lessons(x) for x in v
    ] for k, v in lessons.items()}

class ScheduleFile(NamedTuple):
    """Описывает скачанный из сети CSV файл расписания.

    Данный класс используется внутри методов обновления и загрузки
    расписания, для лучшей структуризации.

    :param content: Содержимое файла расписания.
    :type content: bytes
    :param hash: Посчитанный хеш расписания.
    :type hash: str
    """

    content: bytes
    hash: str


class Schedule:
    """Предоставляет доступ к расписанию уроков.

    В первую очередь занимается получение расписания из гугл таблиц.
    Отслеживает изменения в расписании и записывает их в файл.
    Вы можете получить расписание для конкретного класса,
    произвести полный поиск по урокам или кабинетам, использую фильтры,
    получить список изменений в расписании, также с возможностью
    отфильтровать результаты поиска.
    Также предоставляет доступ к индексам расписания.

    :param sc_path: Ваш путь к файлу расписания.
    :type sc_path: Path | str
    :param updates_path: Ваш путь к файлу списка изменений расписания.
    :type updates_path: Path | str
    :param index_path: Ваш путь для сохранения индексов расписания.
    :type index_path: Path | str
    """

    def __init__(self,
        sc_path: Path | str = SC_PATH,
        updates_path: Path | str = SC_UPDATES_PATH,
        index_path: Path | str = INDEX_PATH,
    ) -> None:
        super().__init__()
        # Определение путей к файлам.
        self.sc_path = Path(sc_path)
        self.updates_path = Path(updates_path)
        self.index_path = Path(index_path)

        # Определение индексов расписания.
        self._l_index: dict[str, list[dict]] = None
        self._c_index: dict[str, list[dict]] = None
        self._updates = None

        #: Полное расписание, включая метаданные, прим. время получения
        self._schedule: dict[str, int | dict | str] | None = None
        self.next_parse: int | None = None
        #: Расписание уроков, он же индекс классов (часто используется)
        # self.lessons: dict[str, list[str]] = self.schedule.get("lessons", {})

    @property
    def lessons(self) -> dict[str, list[list[str]]]:
        """Получает словарь расписания уроков по классам.

        При получении расписания также автоматически будет проводить
        проверку обновлений.

        :return: Расписание уроков по классам.
        :rtype: dict[str, list[list[str]]]
        """
        return self.schedule["lessons"]

    @property
    def schedule(self) -> dict[str, int | dict | str]:
        """Получает расписание уроков.

        Если расписание уроков пустое или таймер истёк, запускает
        процесс обновления.

        **Процесс обновления**:

        - Загрузка файла расписания.
            - Если не удалось, передвигаем метку обновления.
        - Сравниваем хеши расписаний.
        - Если различаются:
            - Разбирает расписание из файла.
            - Обновляем индексы расписания.
            - Сравниваем и записывает изменения в расписании.
        - Сдвигаем временную метку следующего обновления.

        Расписание уроков представляет собой словарь:

        - ``hash``: Хеш сумма расписания уроков.
        - ``last_parse``: UnixTime последней проверки расписания.
        - ``next_parse``: UnixTime следующей проверки расписания.
        - ``lessons``: Сам словарь расписаний уроков по классам.

        :return: Словарь данных расписания уроков.
        :rtype: dict[str, Union[int, dict, str]]
        """
        now = int(datetime.timestamp(datetime.now()))
        if self.next_parse is None or self.next_parse < now:
            t = load_file(self.sc_path)
            self._process_update(t, now)
        return self._schedule

    @property
    def l_index(self) -> dict[str, list[dict]]:
        """Индекс уроков.

        Загружает индекс уроков из файла.
        Индекс урока предоставляет изменённый словарь расписания,
        где вместо ключа используется название урока, а не класс.

        Индексы удобно использовать при поиске данных из расписания.
        К примеру если быстро нужно найти урок и посмотреть где, когда
        и для кого он проводится.

        .. code-block:: json

            {
                "матем": [ // Урок ...
                    { // Понедельник ...
                        "204" { // Кабинет
                            "8в" [ // класс
                                3 // Номер урока
                            ]
                        }
                    },
                    {}, // Вторник ...
                    {}, // Среда ...
                    // ...
                ]
            }

        :return: Полный индекс уроков.
        :rtype: dict[str, list[dict]]
        """
        if self._l_index is None:
            self._l_index = load_file(self.index_path)[0]
        return self._l_index

    @property
    def c_index(self) -> dict[str, list[dict]]:
        """Индекс кабинетов.

        Загружает индекс кабинетов из файла.
        Индекс кабинетов предоставляет изменённый словарь расписания,
        где вместо ключа используется название кабинета, а не класс.

        Удобно использовать для получения информации о кабинете.
        Какой урок, когда, для кого проходит в том или ином кабинете.
        Используется в функции поиска информации по кабинетам.

        .. code-block:: json

            {
                "204": [ // Кабинет
                    { // Понедельник ...
                        "матем" { // Какой урок проходит
                            "8в" [ // класс для которого проходит
                                3 // Номер урока в расписании
                            ]
                        }
                    },
                    {}, // Вторник ...
                    {}, // Среда ...
                    // ...
                ]
            }

        :return: Полный индекс уроков.
        :rtype: dict[str, list[dict]]
        """
        if not self._c_index:
            self._c_index = load_file(self.index_path)[1]
        return self._c_index

    @property
    def updates(self) -> list[dict[str, int | list[dict]]] | None:
        """Список изменений в расписании.

        Загружает полный список изменений из файла.
        Список изменений представляет собой перечень последних 30-ти
        зафиксированных изменений.
        Включая время начала и конца временного промежутка, когда эти
        изменения были зафиксированы.

        Если вы хотите получить не все обновления или хотите
        отфильтровать результаты намерения при помощи Намерения, то
        воспользуйтесь методом get_updates.

        Пример одной из записей:

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
                            // И так далее...
                        ],
                    },
                    {}, // Вторник ...
                    {}, // Среда ...
                    // ...
                ]
            }

        :return: Полный список изменений в расписании.
        :rtype: list[dict[str, int | list[dict]]] | None
        """
        if self._updates is None:
            self._updates = load_file(self.updates_path)
        return self._updates


    # Получаем расписание
    # ===================

    def _load_schedule(self, url: str) -> ScheduleFile | None:
        logger.info("Download schedule csv_file ...")
        try:
            csv_file = requests.get(url).content
            h = hashlib.md5(csv_file).hexdigest()
            return ScheduleFile(csv_file, h)
        except Exception as e:
            logger.exception(e)
            return

    def _update_diff_file(
        self,
        a: dict[str, list | int | str],
        b: dict[str, list | int | str]
     ) -> None:
        """Обновляет файл списка изменений расписания.

        Производит полное сравнение старого и нового расписания.
        После сравнения создаёт новую запись о найденных изменениях и
        добавляет её в файл списка изменений.

        :param a: Исходное полное расписание.
        :type a: dict[str, Union[list, int, str]]
        :param b: Новое полное расписание уроков.
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
        logger.info("Update index files...")
        save_file(self.index_path,
            [get_index(sp_lessons), get_index(sp_lessons, False)]
        )

    def _save_schedule(self, t: dict[str, dict | int | str],
        overwrite: bool=False
    ) -> None:
        if overwrite or self._schedule is None:
            self._schedule = t
            save_file(self.sc_path, t)


    def _process_update(
        self,
        t: dict[str, dict | int | str],
        timestamp: int
    ) -> None:
        """Полное обновление расписания, индексов, файла обновлений.

        Производит полное обновление расписания уроков.
        Загружает файл csv файла расписания.
        Если хеши не отличаются, устанавливаем время следующей
        проверки и завершаем работу.

        Если расписание изменилось, собираем новое расписание из
        csv файла, получаем файл индексов и обновляем список
        изменений.

        :param t: Текущее расписание уроков.
        :type t: dict[str, Union[list, int, str]]
        :param timestamp: Текущее время в UNIX формате
        :type timestamp: int
        """
        logger.info("Start schedule update ...")

        # Скачиваем файл с расписанием
        csv_file = self._load_schedule(url)
        if csv_file is None:
            # Откладываем обновление на минуту
            self.next_parse = timestamp+60
            self._save_schedule(t)
            return

        # Сравниваем хеши расписаний
        if t.get("hash", "") == csv_file.hash:
            logger.info("Schedule is up to date")
            self.next_parse = timestamp+1800
            self._save_schedule(t)
            return

        try:
            lessons = parse_lessons(csv_file.content.decode("utf-8"))
            self._update_index_files(lessons)
        except Exception as e:
            logger.exception(e)

            # Откладываем обновление на минуту
            self.next_parse = timestamp+60
            self._save_schedule(t)
            return

        # Собираем новое расписание уроков
        new_t = {
            "hash": csv_file.hash,
            "lessons": lessons,
            "last_parse": timestamp,
        }

        self.next_parse = timestamp+1800
        self._update_diff_file(t, new_t)
        self._save_schedule(new_t, overwrite=True)


    # Получение данных из расписания
    # ==============================

    def get_lessons(self, cl: str | None=None) -> list[list[str]]:
        """Получает полное расписание уроков для указанного класса.

        .. deprecated:: 5.8 Данный метод может быть переработан

            - Поскольку он зависит от внутреннего аттрибута класса.
            - Не поддерживает намерения для фильтрации результата.

        Возвращает полное расписание уроков для указанного класса.
        Если не указать класс, берёт класс из аттрибута расписания.
        Если такого класса в расписании нету, то вернёт пустое
        расписание на неделю.
        Обратите внимание, что даже при неправильном классе результат
        вернётся корректный.

        :param cl: Для какого класса получить расписание.
        :type cl: Optional[str]
        :return: расписание уроков на неделю для класса.
        :rtype: list[list[str]]
        """
        if cl is None:
            raise ValueError("User class let is None")
        return self.lessons.get(cl, [[], [], [], [], [], []])

    def get_updates(self, intent: Intent, offset: int | None=None
    ) -> list[list[dict[str, int | list[dict]]]]:
        """Получает список изменений расписания.

        Это более продвинутый метод получения записей об изменениях
        в расписании.
        Проходится по всему списку изменений, возвращая необходимые
        вам результаты.
        Для уточнения результатов используется Намерение.
        К примеру чтобы получить все изменения для одного класса.
        Или посмотреть как изменялось расписание в определённый день.

        Помимо этого вы можете передавать временную метку обновления,
        начиная с которой будет производиться поиск изменений.
        Это используется при отправке именно новых обновлений в
        расписании пользователей.

        Ежели ваша цель - просто получить список всех изменений в
        расписании, то воспользуйтесь аттрибутом ``updates``.

        :param intent: Намерения для уточнения поиска изменений.
        :type intent: Intent
        :param offset: С какой временной метки обновления начать.
        :type offset: int | None
        :return: Список обновлений расписания.
        :rtype: list[list[dict[str, int | list[dict]]]]
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
        cabinets: bool | None=False
    ) -> list[list[list[str]]]:
        """Производит поиск в расписании по индексу расписания.

        Сама же цель - название кабинета/урока.
        Для уточнения результатов поиска используются намерения.
        Например чтобы получить результаты на определённый день.
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

        Результат поиска возвращает подобный расписанию формат.

        .. code-block:: json

            [ // Дни
                [ // Уроки (по умолчанию 8)
                    [ // Найденные результаты
                        "{cl}",
                        "{obj}",
                        "{cl}:{obj}",
                        "..."
                    ],
                    [], // Если список пустой - ничего не найдено
                    // Дальше все прочие уроки.
                ],
                [], // Вторник ...
                // Среда ...
            ]

        Формат строки результата зависит от некоторых условий:

        - ``{cl}`` - Если в намерении 1 кабинет и указаны уроки.
        - ``{obj}`` - Если в намерении 1 класс (опускаем описание класса).
        - ``{cl}:{obj}`` - Для всех прочих случаев.

        :param target: Цель для поиска, урок или кабинет.
        :type target: str
        :param intent: Намерения для уточнения результатов поиска.
        :type intent: Intent
        :param cabinets: Что ищем, урок или кабинет. Обычно урок.
        :type cabinets: bool
        :return: Результаты поиска в расписании
        :rtype: list[list[list[str]]]
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

    # Работа с намерениями
    # ====================

    def construct_intent(self,
        cl: Iterable[str] | str = (),
        days: Iterable[int] | int = (),
        lessons: Iterable[str] | str = (),
        cabinets: Iterable[str] | str = ()
    ) -> Intent:
        """Создаёт новое намерение для текущего расписания.

        Сокращение для ``Intent.construct()``.

        .. code-block:: python

            # Можно использовать любой вариант
            i = Intent.construct(sc, ...)
            i = sc.construct_intent(...)

        :param cl: Какие классы расписания добавить в намерение
        :type cl: Iterable[str] | str
        :param days: Какие дни добавить в намерение (0-5)
        :type days: Iterable[int] | int
        :param lessons: Какие уроки добавить в намерение (из l_index).
        :type lessons: Iterable[str] | str
        :param cabinets: Какие кабинеты добавить в намерение (c_index).
        :type cabinets: Iterable[str] | str
        :return: Проверенное намерение из переданных аргументов
        :rtype: Intent
        """
        return Intent.construct(self, cl, days, lessons, cabinets)

    def parse_intent(self, args: Iterable[str]) -> Intent:
        """Парсит намерение из строковых аргументов.

        Сокращение для ``Intent.parse()``

        .. code-block:: python

            # Можно использовать любой вариант
            i = Intent.parse(sc, args)
            i = sc.parse_intent(args)

        :param args: Аргументы дя сборки намерений.
        :type args: Iterable[str]
        :return: Готовое намерение из строковых аргументов.
        :rtype: Intent
        """
        return Intent.parse(self, args)
