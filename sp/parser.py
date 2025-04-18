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

import hashlib
from collections import defaultdict, deque
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeAlias, TypedDict

import openpyxl
import requests
from loguru import logger

from .intents import Intent
from .utils import load_file, save_file

url = "https://docs.google.com/spreadsheets/d/1pP_qEHh4PBk5Rsb7Wk9iVbJtTA11O9nTQbo1JFjnrGU/export?format=xlsx"
RAW_SC_PATH = Path("sp_data/sc.xlsx")
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

    ```py
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
    ```
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
                al = a_lessons[i] if i <= len(a_lessons) - 1 else None
                if lesson != al:
                    updates[day][k][i] = (al, lesson)
    return updates


def get_index(
    sp_lessons: dict[str, list[list[str]]], lessons_mode: bool | None = True
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
    """
    logger.info("Get {}_index", "l" if lessons_mode else "c")
    index: dict[str, list[dict]] = defaultdict(
        lambda: [defaultdict(lambda: defaultdict(list)) for x in range(6)]
    )

    for cl, v in sp_lessons.items():
        for day, lessons in enumerate(v):
            for n, lesson_data in enumerate(lessons):
                lesson, cabinet = lesson_data.lower().split(":")
                lesson = lesson.strip(" .")
                for old, new in [("-", "="), (" ", "-"), (".-", ".")]:
                    lesson = lesson.replace(old, new)

                # Obj - Первичный ключ индекса, урок или кабинет.
                # another - = Вторичный ключ, противоположный первичному
                obj = [lesson] if lessons_mode else cabinet.split("/")
                another = cabinet if lessons_mode else lesson

                for x in obj:
                    index[x][day][another][cl].append(n)
    return index


def parse_lessons() -> dict[str, list[list[str]]]:  # noqa: PLR0912
    """Разбирает XLSX файл в словарь расписания.

    Расписание в XLSX файле представлено подобным образом.

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


    ```py
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
    ```
    """
    logger.info("Start parse lessons...")

    # lessons: Словарь расписания [Класс][День]
    lessons: dict[str, list] = defaultdict(lambda: [[] for x in range(6)])
    day = -1
    last_row = 8
    sheet = openpyxl.load_workbook(str(RAW_SC_PATH)).active
    if sheet is None:
        raise ValueError("Loaded Schedule active tab is wrong")
    row_iter = sheet.iter_rows()

    # Получает кортеж с именем класса и индексом
    # соответствующего столбца расписания
    next(row_iter)
    cl_header: list[tuple[str, int]] = []
    for i, cl in enumerate(next(row_iter)):
        if isinstance(cl.value, str) and cl.value.strip():
            cl_header.append((cl.value.lower(), i))

    # построчно читаем расписание уроков
    for row in row_iter:
        # Первый элемент строки указывает на день недели.
        if isinstance(row[0].value, str) and len(row[0].value) > 0:
            logger.info("Process group {} ...", row[0].value)

        # Если второй элемент в ряду указывает на номер урока
        if isinstance(row[1].value, int | float):
            # Если вдруг номер урока стал меньше, начался новый день
            if row[1].value < last_row:
                day += 1
            last_row = int(row[1].value)

            for cl, i in cl_header:
                # Если класса нет в расписании, то добавляем его
                # А если строка зачёркнута, то также пропускаем
                if row[i].value is None or row[i].font.strike:
                    lesson = None
                else:
                    lesson = str(row[i].value).strip(" .-").lower() or None

                # Кабинеты иногда представлены числом, иногда строкой
                # Спасибо электронные таблицы, раньше было проще
                if row[i + 1].value is None:
                    cabinet = "None"
                elif isinstance(row[i + 1].value, float):
                    cabinet = str(int(row[i + 1].value))
                elif isinstance(row[i + 1].value, str):
                    cabinet = str(row[i + 1].value).strip().lower() or "0"
                else:
                    raise ValueError(f"Invalid cabinet format: {row[i + 1]}")

                lessons[cl][day].append(f"{lesson}:{cabinet}")

        elif day == 5:  # noqa
            logger.info("CSV file reading completed")
            break

    return {k: [_clear_day_lessons(x) for x in v] for k, v in lessons.items()}


# Дополнительные типы данных
# ==========================


class ScheduleDict(TypedDict):
    """Описывает что собой представляет словарь расписание."""

    hash: str
    last_parse: int
    lessons: dict[str, list[list[str]]]


class UpdateData(TypedDict):
    """Что представляет собой запись об обновлении расписания."""

    start_time: int
    end_time: int
    updates: list[dict[str, list]]


# Определение полезных типов
LessonIndex: TypeAlias = dict[str, list[dict[str, dict[str, int]]]]
ClassIndex: TypeAlias = dict[str, list[dict[str, dict[str, int]]]]
SearchRes: TypeAlias = list[list[list[str]]]


class Schedule:
    """Предоставляет доступ к расписанию уроков.

    В первую очередь занимается получение расписания из гугл таблиц.
    Отслеживает изменения в расписании и записывает их в файл.
    Вы можете получить расписание для конкретного класса,
    произвести полный поиск по урокам или кабинетам, использую фильтры,
    получить список изменений в расписании, также с возможностью
    отфильтровать результаты поиска.
    Также предоставляет доступ к индексам расписания.
    """

    def __init__(
        self,
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
        self._l_index: LessonIndex | None = None
        self._c_index: ClassIndex | None = None
        self._updates: list[UpdateData] | None = None

        #: Полное расписание, включая метаданные, прим. время получения
        self._schedule: ScheduleDict | None = None
        self.next_parse: int | None = None

    @property
    def lessons(self) -> dict[str, list[list[str]]]:
        """Получает словарь расписания уроков по классам.

        При получении расписания также автоматически будет проводить
        проверку обновлений.
        """
        return self.schedule["lessons"]

    @property
    def schedule(self) -> ScheduleDict:
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
        """
        now = int(datetime.timestamp(datetime.now(UTC)))
        if self.next_parse is None or self.next_parse < now:
            t: ScheduleDict = load_file(self.sc_path)
            self._process_update(t, now)
        return self._schedule

    @property
    def l_index(self) -> LessonIndex:
        """Индекс уроков.

        Загружает индекс уроков из файла.
        Индекс урока предоставляет изменённый словарь расписания,
        где вместо ключа используется название урока, а не класс.

        Индексы удобно использовать при поиске данных из расписания.
        К примеру если быстро нужно найти урок и посмотреть где, когда
        и для кого он проводится.

        ```json
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
        ```
        """
        if self._l_index is None:
            self._l_index = load_file(self.index_path)[0]
        return self._l_index

    @property
    def c_index(self) -> ClassIndex:
        """Индекс кабинетов.

        Загружает индекс кабинетов из файла.
        Индекс кабинетов предоставляет изменённый словарь расписания,
        где вместо ключа используется название кабинета, а не класс.

        Удобно использовать для получения информации о кабинете.
        Какой урок, когда, для кого проходит в том или ином кабинете.
        Используется в функции поиска информации по кабинетам.

        ```json
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
        ```
        """
        if self._c_index is None:
            self._c_index = load_file(self.index_path)[1]
        return self._c_index

    @property
    def updates(self) -> list[UpdateData] | None:
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

        ```json
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
        ```
        """
        if self._updates is None:
            file_data: list[UpdateData] = load_file(self.updates_path)
            if not isinstance(file_data, list):
                raise ValueError("Incorrect updates list")
            self._updates = file_data
        return self._updates

    # Получаем расписание
    # ===================

    def _load_schedule(self, url: str) -> str:
        logger.info("Download schedule csv_file ...")
        try:
            csv_file = requests.get(url).content
            with RAW_SC_PATH.open("wb") as f:
                f.write(csv_file)
            return hashlib.md5(csv_file).hexdigest()
        except Exception as e:
            logger.exception(e)
            raise ValueError("Failed to load schedule") from e

    def _update_diff_file(self, a: ScheduleDict, b: ScheduleDict) -> None:
        """Обновляет файл списка изменений расписания.

        Производит полное сравнение старого и нового расписания.
        После сравнения создаёт новую запись о найденных изменениях и
        добавляет её в файл списка изменений.
        """
        logger.info("Update diff file ...")
        sc_changes: deque[UpdateData] = deque(
            load_file(self.updates_path, []), 30
        )
        updates = get_sc_updates(a.get("lessons", {}), b["lessons"])
        if sum(map(len, updates)):
            if len(sc_changes):
                start_time = sc_changes[-1]["end_time"]
            else:
                start_time = b["last_parse"]

            sc_changes.append(
                {
                    "start_time": start_time,
                    "end_time": b["last_parse"],
                    "updates": updates,
                }
            )
            save_file(self.updates_path, list(sc_changes))

    def _update_index_files(self, lessons: dict[str, list[list[str]]]) -> None:
        logger.info("Update index files...")
        save_file(
            self.index_path, [get_index(lessons), get_index(lessons, False)]
        )

    def _save_schedule(self, t: ScheduleDict, overwrite: bool = False) -> None:
        if overwrite or self._schedule is None:
            self._schedule = t
            save_file(self.sc_path, dict(t))

    def _process_update(self, t: ScheduleDict, timestamp: int) -> None:
        """Полное обновление расписания, индексов, файла обновлений.

        Производит полное обновление расписания уроков.
        Загружает файл csv файла расписания.
        Если хеши не отличаются, устанавливаем время следующей
        проверки и завершаем работу.

        Если расписание изменилось, собираем новое расписание из
        csv файла, получаем файл индексов и обновляем список
        изменений.
        """
        logger.info("Start schedule update ...")

        # Скачиваем файл с расписанием
        file_hash = self._load_schedule(url)
        if file_hash is None:
            # Откладываем обновление на минуту
            self.next_parse = timestamp + 60
            self._save_schedule(t)
            return

        # Сравниваем хеши расписаний
        if t.get("hash", "") == file_hash:
            logger.info("Schedule is up to date")
            self.next_parse = timestamp + 1800
            self._save_schedule(t)
            return

        try:
            lessons = parse_lessons()
            self._update_index_files(lessons)
        except Exception as e:
            logger.exception(e)

            # Откладываем обновление на минуту
            self.next_parse = timestamp + 60
            self._save_schedule(t)
            return

        # Собираем новое расписание уроков
        new_t: ScheduleDict = {
            "hash": file_hash,
            "lessons": lessons,
            "last_parse": timestamp,
        }

        self.next_parse = timestamp + 1800
        self._update_diff_file(t, new_t)
        self._save_schedule(new_t, overwrite=True)

    # Получение данных из расписания
    # ==============================

    def get_lessons(self, cl: str | None = None) -> list[list[str]]:
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
        """
        if cl is None:
            raise ValueError("User class let is None")
        return self.lessons.get(cl, [[], [], [], [], [], []])

    def get_updates(
        self, intent: Intent, offset: int | None = None
    ) -> list[UpdateData]:
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
        """
        updates: list[UpdateData] = []

        if self.updates is None:
            raise ValueError("Updates list is None. Updates file broken?")

        # Пробегаемся по списку обновлений
        for update in self.updates:
            if update is None:
                continue

            # Пропускаем обновления согласно сдвигу
            if offset is not None and update["end_time"] < offset:
                continue

            # Собираем новый список изменений, используя намерения
            new_update: list[dict[str, list[str]]] = [{} for x in range(6)]
            for day, day_updates in enumerate(update["updates"]):
                if intent.days and day not in intent.days:
                    continue

                for cl, cl_updates in day_updates.items():
                    if intent.cl and cl not in intent.cl:
                        continue

                    new_update[day][cl] = cl_updates

            # Если в итоге какие-то обновления есть - добавляем
            if sum(map(len, new_update)):
                updates.append(
                    {
                        "start_time": update["start_time"],
                        "end_time": update["end_time"],
                        "updates": new_update,
                    }
                )

        return updates

    def search(
        self, target: str, intent: Intent, cabinets: bool | None = False
    ) -> SearchRes:
        """Производит поиск в расписании по индексу расписания.

        Сама же цель - название кабинета/урока.
        Для уточнения результатов поиска используются намерения.
        Например чтобы получить результаты на определённый день.
        Ну или к примеру в определённых кабинетах, если речь об уроке.

        Поиск немного изменяется в зависимости от режима.

        +----------+---------+---------+
        | cabinets | obj     | another |
        +==========+=========+=========+
        | false    | lesson  | cabinet |
        +----------+---------+---------+
        | true     | cabinet | lesson  |
        +----------+---------+---------+

        Результат поиска возвращает подобный расписанию формат.

        ```json
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
        ```

        Формат строки результата зависит от некоторых условий:

        - ``{cl}`` - Если в намерении 1 кабинет и указаны уроки.
        - ``{obj}`` - Если в намерении 1 класс (опускаем описание класса).
        - ``{cl}:{obj}`` - Для всех прочих случаев.
        """
        res: SearchRes = [[[] for x in range(8)] for x in range(6)]

        # Определяем какой индекс использовать
        target_index = self.c_index if cabinets else self.l_index
        index: list[dict] = target_index.get(target, [])

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

    def construct_intent(
        self,
        cl: Iterable[str] | str = (),
        days: Iterable[int] | int = (),
        lessons: Iterable[str] | str = (),
        cabinets: Iterable[str] | str = (),
    ) -> Intent:
        """Создаёт новое намерение для текущего расписания.

        Сокращение для ``Intent.construct()``.

        .. code-block:: python

            # Можно использовать любой вариант
            i = Intent.construct(sc, ...)
            i = sc.construct_intent(...)
        """
        return Intent.construct(self, cl, days, lessons, cabinets)

    def parse_intent(self, args: Iterable[str]) -> Intent:
        """Парсит намерение из строковых аргументов.

        Сокращение для ``Intent.parse()``

        .. code-block:: python

            # Можно использовать любой вариант
            i = Intent.parse(sc, args)
            i = sc.parse_intent(args)
        """
        return Intent.parse(self, args)
