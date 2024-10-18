"""Счётчики элементов расписания.

Предоставляет вспомогательный класс для подсчёта количества
элементов в расписании.
Используется для последующего анализа расписания.
Все функции используют намерения, для уточнения результатов подсчёта.

Обратите внимание, что счётчики возвращают "сырой" результат.
Который вы может в последствии самостоятельно обработать
в необходимый вам формат.

Warning: Новый класс счётчика.
    Поскольку появился новый класс счётчика `CurrentCounter`,
    более нет необходимости использовать `TextCounter`, от чего
    последний был удалён.
"""

from collections import Counter, defaultdict
from enum import Enum

from .intents import Intent
from .parser import Schedule


class CounterTarget(Enum):
    """Описывает все доступные подгруппы счётчиков.

    Используется при отображении результатов подсчёта из CurrentCounter.
    """

    NONE = "none"
    """То же самое что и None, без цели отображения."""

    CL = "cl"
    """По классам в расписании."""

    DAYS = "days"
    """По дням недели в числовом формате."""

    LESSONS = "lessons"
    """По урокам (из l_index)."""

    CABINETS = "cabinets"
    """По кабинетам (из c_index)."""

    MAIN = "main"
    """Противоположный выбранному счётчику индекса.
    Если это счётчик уроков - то по кабинетам.
    И напротив, если это счётчик кабинетов, то по урокам.
    """


# Вспомогательные функции
# =======================

def _group_counter_res(counter_res: dict[str, dict[str, int | Counter]]
) -> dict[int, dict[str, dict]]:
    """Группирует результат работы счётчиков по total ключу.

    Формат вывода:

    ```json
        {
            2: { # Общее количество ("total" счётчика)
                "8в" { # Некоторые счётчики, не обязательно класс.
                    # ...
                },
                "...", {
                    # ...
                }
            }
        }
    ```

    Args:
        counter_res (dict[str, dict[str, int | Counter]]):
            Результаты работы счётчика расписания.

    Returns:
        dict[int, dict[str, dict]]:
            Сгруппированные результаты работы счётчика.
    """
    groups = defaultdict(dict)
    for k, v in counter_res.items():
        key = v["total"]
        if not key:
            continue

        groups[key][k] = v

    return groups

def reverse_counter(cnt: Counter) -> dict[int, list[str]]:
    """Меняет ключ и значение `collections.Counter` местами.

    Переворачивает счётчик из name:count -> count:[name, name, name].
    Используется в группировке результатов работы счётчиков по
    количеству.
    Также будет пропускать пустые значения при подсчёте.

    Args:
        cnt (Counter): Счётчик элементов расписания.

    Returns:
        dict[int, list[str]]: Перевёрнутый счётчик расписания.
    """
    res = defaultdict(list)
    for k, v in cnt.items():
        if not v:
            continue

        res[v].append(k)
    return res


# Класс счётчика
# ==============

class CurrentCounter:
    """Счётчик элементов текущего расписания.

    Предоставляет методы для подсчёта элементов текущего расписания.
    Возвращает сырые результаты, которое после можно обработать через
    класс представления.

    Examples:
        Пример использования вместе с `Platform`:

        ```python
        cc = CurrentCounter(platform.view.sc, Intent())
        res = platform.counter(cc.cl(), CounterTarget.NONE)
        ```
    """

    def __init__(self, sc: Schedule, intent: Intent) -> None:
        """Создаёт новый экземпляр счётчика.

        Каждый счётчик привязывается к расписанию.
        А также здесь можно указать намерения по умолчанию для всех
        счётчиков.

        Args:
            sc (Schedule): Расписание, для которого будет производиться подсчёт.
            intent (Intent): Уточняющее намерение при подсчёте элементов.
        """
        self._sc = sc
        self._intent = intent

    def cl(
        self, intent: Intent | None=None
    ) -> dict[int, dict[str, dict]]:
        """Счётчик по классам с использованием `sp.lessons`.

        Считает элементы расписания, пробегаясь по `sp.lessons`.
        Использует намерение для уточнения результатов поиска.

        Examples:
            Пример результатов работы счетчика:

            ``` python
            {
                "7а": { # Классы
                    "total": 12, # Общее количество элементов.
                    "days": Counter(), # Количество элементов по дням.
                    "lessons": Counter(), # Количество элементов по урокам.
                    "cabinets": Counter(), # Элементы по кабинетам.
                }
            }
            ```

        Args:
            intent (Intent | None):
                Намерения для уточнения результатов подсчёта.

        Returns:
            dict[int, dict[str, dict]]:
                Подсчитанные элементы расписания по классам.
        """
        res: dict[str, int | Counter] = {}
        if intent is None:
            intent = self._intent

        # Пробегаемся по урокам и дням в расписании
        for cl, days in self._sc.lessons.items():
            if intent.cl and cl not in intent.cl:
                continue

            day_counter = Counter()
            lessons_counter = Counter()
            cabinets_counter = Counter()

            for day, lessons in enumerate(days):
                if intent.days and day not in intent.days:
                    continue

                for x in lessons:
                    x = x.split(":") # noqa

                    lessons_counter[x[0]] += 1
                    for cabinet in x[1].split("/"):
                        cabinets_counter[cabinet] += 1

                day_counter[str(day)] = len(lessons)

            res[cl] = {"total": sum(day_counter.values()),
                    "days": day_counter,
                    "lessons": lessons_counter,
                    "cabinets": cabinets_counter}
        return _group_counter_res(res)

    def days(
        self,
        intent: Intent | None = None,
    ) -> dict[int, dict[str, dict]]:
        """Счётчик по дням с использованием `sc.lessons`.

        Производит подсчёт элементов относительно дней недели.
        Использует намерение для уточнения результатов работы счётчиков.
        По совей работе противоположен `cl` счётчику.

        Examples:
            Пример результатов работы счётчика:

            ``` python
            {
                "1": { # День недели (0 - понедельник, 5 - суббота).
                    "total": 12 # Общее количество элементов расписания.
                    "cl": Counter() # Количество элементов по классам.
                    "lessons": Counter() # Элементов по урокам.
                    "cabinets": Counter() # Элементов по кабинетам.
                }
            }
            ```

        Args:
            intent (Intent | None):
                Намерения для уточнения результатов подсчёта.

        Returns:
            dict[int, dict[str, dict]]:
                Подсчитанные элементы расписания по дням.
        """
        res: dict[int, dict[str, int | Counter]] = {
            str(x): {"cl": Counter(),
                    "total": 0,
                    "lessons": Counter(),
                    "cabinets": Counter()
        } for x in range(6)}
        if intent is None:
            intent = self._intent

        for cl, days in self._sc.lessons.items():
            if intent.cl and cl not in intent.cl:
                continue

            for day, lessons in enumerate(days):
                if intent.days and day not in intent.days:
                    continue

                for lesson in lessons:
                    lesson = lesson.split(":") # noqa
                    res[str(day)]["cl"][cl] += 1
                    res[str(day)]["lessons"][lesson[0]] += 1
                    res[str(day)]["total"] += 1

                    for x in lesson[1].split("/"):
                        res[str(day)]["cabinets"][x] += 1

        return _group_counter_res(res)

    def index(
        self,
        intent: Intent | None = None,
        cabinets_mode: bool = False
    ) -> dict[int, dict[str, dict]]:
        """Счётчик уроков/кабинетов с использованием индексов.

        Производит подсчёт элементов расписания в счётчиках.
        В зависимости от режима считает уроки или кабинеты.
        Использует намерение, для уточнения результатов счётчика.

        !!! hint Этот счётчик сильно отличается

            Обратите внимание, что поскольку этот счётчик использует
            в подсчёте индексы, то и шаблон результатов работы этого
            счётчика отличается.

            | cabinets | obj     | another |
            | -------- | ------- | ------- |
            | false    | lesson  | cabinet |
            | true     | cabinet | lesson  |

        Examples:
            ``` python
            {
                "obj": { # урок или кабинет в зависимости от режима.
                    "total": 12 # Общее количество элементов расписания.
                    "cl": Counter() # Количество элементов по классам.
                    "days": Counter() # Элементов по дням.
                    "main": Counter() # Элементов по `another`.
                }
            }
            ```

        Args:
            intent (Intent | None):
                Намерение для уточнения результатов подсчёта.
            cabinets_mode (bool): Делать ли подсчёты по кабинетам (c_index).

        Returns:
            dict[int, dict[str, dict]]:
                Подсчитанные элементы расписания по урокам/кабинетам.
        """
        res: dict[str, dict[str, int | Counter]] = defaultdict(
            lambda: {
                "total": 0,
                "days": Counter(),
                "cl": Counter(),
                "main": Counter()
            }
        )
        if intent is None:
            intent = self._intent

        if cabinets_mode:
            index = self._sc.c_index
            obj_filter = intent.cabinets
            another_filter = intent.lessons
        else:
            index = self._sc.l_index
            obj_filter = intent.lessons
            another_filter = intent.cabinets

        for k, v in index.items():
            if obj_filter and k not in obj_filter:
                continue

            for day, another_v in enumerate(v):
                if intent.days and day not in intent.days:
                    continue

                for another, cl_s in another_v.items():
                    if another_filter and another not in another_filter:
                        continue

                    for cl, i in cl_s.items():
                        if intent.cl and cl not in intent.cl:
                            continue

                        res[k]["total"] += len(i)
                        res[k]["cl"][cl] += len(i)
                        res[k]["days"][str(day)] += len(i)
                        res[k]["main"][another] += len(i)
        return _group_counter_res(res)
