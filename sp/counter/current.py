from typing import Optional

from sp.parser import Schedule
from sp.intents import Intent

class CurrentCounter:
    def __init__(self, sc: Schedule, intent: Intent):
        self.sc = sc
        self.intent = intent

    def cl(self, intent: Optional[Intnt]=None
    ) -> dict[str, dict[str, Union[int, Counter]]]:
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

        :param intent: Намерения для уточнения рещультатов подсчёта.
        :type intent: Optional[Intent]
        :return: Подсчитанные элементы расписания по классам.
        :rtype: dict[str, dict[str, Union[int, Counter]]]
        """
        if intent is None:
            intent = self.intent

        # Пробегаемся по урокам и дням в расписании
        for cl, days in sc.lessons.items():
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
        return res


    def days(self, intent: Optional[Intent]
    ) -> dict[str, dict[str, Union[int, Counter]]]:
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

        :param intent: Намерения для уточнения резульатов поиска.
        :type intent: Optional[Intent]
        :return: Подсчитанные элементы расписнаия по дням.
        :rtype: dict[str, dict[str, Union[int, Counter]]]
        """
        if intent is None:
            intent = self.intent

        res: dict[int, dict[str, Union[int, Counter]]] = {
            str(x): {"cl": Counter(),
                    "total": 0,
                    "lessons": Counter(),
                    "cabinets": Counter()
        } for x in range(6)}

        for cl, days in sc.lessons.items():
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

        return res

    def index(
        intent: Intent,
        cabinets_mode: Optional[bool]=False
    ) -> dict[str, dict[str, Union[int, Counter]]]:
        """Счётчик уроков/кабинетов с использованием индексов.

        Производит подсчёт элементов расписания в счётиках.
        В зависимости от режима считает уроки или кабинеты.
        Использует намерения, для уточнения результатов счётчика.

        .. caution:: Этот счётик сильно отличается

            Обратите внимаение, что поскольку этот счётчик использует
            в подсчёте индексы, то и шалон результатов рабоыт этого
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

        :param intent: Намерения для уточнения резульатов поиска.
        :type intent: Intent
        :param cabinets_mode: Длеать ли подсчёты по кабинетам.
        :type cabinets_mode: Optional[bool]
        :return: Подсчитанные элементы расписнаия по урокам/кабинетам.
        :rtype: dict[str, dict[str, Union[int, Counter]]]
        """
        if intent is None:
            intent = self.intent

        res: dict[str, dict[str, Union[int, Counter]]] = defaultdict(
            lambda: {
                "total": 0, "days": Counter(), "cl": Counter(), "main": Counter()
            }
        )

        if cabinets_mode:
            index = sc.c_index
            obj_filter = intent.cabinets
            another_filter = intent.lessons
        else:
            index = sc.l_index
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
        return res
