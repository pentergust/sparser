"""Счётчики элементов расписания.

Проедостовляют вспомогательные функции для подсчёта количества
элементов в расписании.
Эти статистические функции могут использоваться для последующего
анализа расписания.
Все функции используют намерения, для уточнения результатов
подсчёта элементов.

Обрабите внимение, что счётчики возвращают "сырой" результат.
Который вы можеет в последствии самостоятельно обработать
в необходимый вам формат.

.. warning:: Новый класс счётчика

    Поскольку появлися новый класс счётчика ``Counter``, более нет
    необходимости использовать ``TextCounter``, от чего последний
    был удалён.

Старый вариант:

.. code-block:: python

    from sp.counters import days_counter
    from sp.parser import Schedule
    from sp.messages import send_counter

    sc = Schedule()
    res = days_counter(sc, sc.construct_intent())
    groups = _group_counter_res(res)
    message = send_counter(groups, target="cl")

Новый вариант:

Содержит:

- Перечисление подгрупп счётчика.
- Вспомогательные функции для результатов счётчиков.
- Счётчики:
    - классы.
    - Дни.
    - Индексы (уроки/кабинеты).
"""

from collections import Counter, defaultdict
from enum import Enum
from typing import Optional, Union

from .intents import Intent
from .parser import Schedule


class CounterTarget(Enum):
    """Описывает все доступные подгруппы счётчиков.

    Пример использования с TextCounter:

    .. code-block:: python

        # coutnter - экземпляр TextCounter с переданным Schedule
        message = counter.cl(
            sc.construct_intent()
            target=CounterTarget.CL
        )

    - `NONE`: То же самое что и None, без цели отображения.
    - `CL`: По классам в расписании.
    - `DAYS`: По дням недели.
    - `LESSONS`: По урокам (l_index).
    - `CABINETS`: По кабинетам (c_index).
    - `MAIN`: Противоположный выбранному счётчику индекса.
        Если это счётчик уроков - то по кабинетам.
        И напротив, если это счётчик кабентов, то по урокам.
    """

    NONE = "none"
    CL = "cl"
    DAYS = "days"
    LESSONS = "lessons"
    CABINETS = "cabinets"
    MAIN = "main"


# Вспомогательные функции
# =======================

def _group_counter_res(counter_res: dict[str, dict[str, Union[int, Counter]]]
) -> dict[int, dict[str, dict]]:
    """Группирует результат работы счётчиков по total ключу.

    Формат вывода:

    .. code-block:: python

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

    :param counter_res: Результаты работы счётчика расписания.
    :type counter_res: dict[str, dict[str, Union[int, Counter]]]
    :return: Сгруппированные результаты работы счётчика.
    :rtype: dict[int, dict[str, dict]]
    """
    groups = defaultdict(dict)
    for k, v in counter_res.items():
        key = v["total"]
        if not key:
            continue

        groups[key][k] = v

    return groups

def reverse_counter(cnt: Counter) -> dict[int, list[str]]:
    """Меняет ключ и занчение collections.Counter местами.

    Перевоварачивает счётчик из name:count -> count:[name, name, name].
    Используется в групперовке результатов работы счётчиков по
    количеству.
    Также он будет пропускать пустые значения при подсчёте.

    :param cnt: Счётчик элементов расписаия.
    :type cnt: Сounter
    :return: Перевёрнутый счётчик расписнаия.
    :rtype: dict[int, list[str]]
    """
    res = defaultdict(list)
    for k, v in cnt.items():
        if not v:
            continue

        res[v].append(k)
    return res


# Функции счётчиков
# =================

class CurrentCounter:
    """Счтётчих элементов текущего расписания."""

    def __init__(self, sc: Schedule, intent: Intent) -> None:
        self.sc = sc
        self.intent = intent

    def cl(
        self,
        intent: Optional[Intent]=None
    ) -> dict[int, dict[str, dict]]:
        """Счётчик по классам с использованием sp.lessons.

        Считает элементы расписнаия, пробегаясь по sp.lessons.
        Использует намерения для уточнения результатов поиска.

        Пример результатов работы счетчика:

        .. code-block:: python

            {
                "7а": { # Классы
                    "total": 12, # Общее количество элементов.
                    "days": Counter(), # Количество элементов по дням.
                    "lessons": Counter(), # Количесво элементов по урокам.
                    "cabinets": Counter(), # Элементы по кабинетам.
                }
            }

        :param intent: Намерения для уточнения результатов подсчёта.
        :type intent: Optional[Intent]
        :return: Подсчитанные элементы расписания по классам.
        :rtype: dict[int, dict[str, dict]]
        """
        res: dict[str, Union[int, Counter]] = {}
        if intent is None:
            intent = self.intent

        # Пробегаемся по урокам и дням в расписании
        for cl, days in self.sc.lessons.items():
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
        intent: Optional[Intent] = None,
    ) -> dict[int, dict[str, dict]]:
        """Счётчик по дням с использованием sc.lessons.

        Производит подсчёт элементов относительно дней недели в расписании.
        Использует намерения для уточнения результатов работы счётчиков.

        Пример результатов работы счётчика:

        .. code-block:: python

            {
                "1": { # День недели (0 - понедельник, 5 - суббота).
                    "total": 12 # Общее количесво элементов расписания.
                    "cl": Counter() # Количество элементов по классам.
                    "lessons": Counter() # Количесвто элементов по урокам.
                    "cabinets": Counter() # Количесво элементов по кабнетам.
                }
            }

        :param intent: Намерения для уточнения результатов подсчёта.
        :type intent: Optional[Intent]
        :return: Подсчитанные элементы расписнаия по дням.
        :rtype: dict[int, dict[str, dict]]
        """
        res: dict[int, dict[str, Union[int, Counter]]] = {
            str(x): {"cl": Counter(),
                    "total": 0,
                    "lessons": Counter(),
                    "cabinets": Counter()
        } for x in range(6)}
        if intent is None:
            intent = self.intent

        for cl, days in self.sc.lessons.items():
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
        intent: Optional[Intent] = None,
        cabinets_mode: Optional[bool]=False
    ) -> dict[int, dict[str, dict]]:
        """Счётчик уроков/кабинетов с использованием индексов.

        Производит подсчёт элементов расписания в счётиках.
        В зависимости от режима считает уроки или кабинеты.
        Использует намерения, для уточнения результатов счётчика.

        .. caution:: Этот счётик сильно отличается

            Обратите внимаение, что поскольку этот счётчик использует
            в подсчёте индексы, то и шаблон результатов работы этого
            счётчика отличается.

        .. table::

                +----------+---------+---------+
                | cabinets | obj     | another |
                +==========+=========+=========+
                | false    | lesson  | cabinet |
                +----------+---------+---------+
                | true     | cabinet | lesson  |
                +----------+---------+---------+

        Пример результатов работы счётчика:

        .. code-block:: python

            {
                "obj": { # урок или кабинет в зависимости от режима.
                    "total": 12 # Общее количесво элементов расписания.
                    "cl": Counter() # Количество элементов по классам.
                    "days": Counter() # Количесвто элементов по дням.
                    "main": Counter() # Количесво элементов по `another`.
                }
            }

        :param intent: Намерения для уточнения результатов подсчёта.
        :type intent: Optional[Intent]
        :param cabinets_mode: Делать ли подсчёты по кабинетам (c_index).
        :type cabinets_mode: Optional[bool]
        :return: Подсчитанные элементы расписнаия по урокам/кабинетам.
        :rtype: dict[int, dict[str, dict]]
        """
        res: dict[str, dict[str, Union[int, Counter]]] = defaultdict(
            lambda: {
                "total": 0,
                "days": Counter(),
                "cl": Counter(),
                "main": Counter()
            }
        )
        if intent is None:
            intent = self.intent

        if cabinets_mode:
            index = self.sc.c_index
            obj_filter = intent.cabinets
            another_filter = intent.lessons
        else:
            index = self.sc.l_index
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
