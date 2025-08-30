"""Самостоятельный парсер школьного расписания.

Содержит компоненты, связанные с получением расписания.
Такие как получение расписание, его кеширование, отслеживание
изменений, сборка индекс и поиск по расписанию.
"""

from collections.abc import Iterable
from typing import TypedDict

from sp.intents import Intent
from sp.updates import UpdateData

# Дополнительные типы данных
# ==========================


# TODO: Разобрать
class ScheduleDict(TypedDict):
    """Описывает что собой представляет словарь расписание."""

    hash: str
    last_parse: int
    lessons: dict[str, list[list[str]]]


LessonIndex = dict[str, list[dict[str, dict[str, list[int]]]]]
ClassIndex = dict[str, list[dict[str, dict[str, list[int]]]]]
SearchRes = list[list[list[str]]]


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
        schedule: dict[str, list[list[str]]],
        hash: str,
        loaded_at: int,
        l_index: LessonIndex,
        c_index: ClassIndex,
        updates: list[UpdateData],
    ) -> None:
        super().__init__()
        self._schedule = schedule
        self.hash = hash
        self.loaded_at = loaded_at
        self._l_index = l_index
        self._c_index = c_index
        self._updates = updates

    @property
    def schedule(self) -> dict[str, list[list[str]]]:
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

    # TODO: Переработать метод
    def lessons(self, cl: str | None = None) -> list[list[str]]:
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

    # TODO: Использовать более общий аргумент
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
    # TODO: Удалить после переноса намерений
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
