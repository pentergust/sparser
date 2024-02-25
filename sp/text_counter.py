"""Обёртка над счётчиками.

Содержит вспомогательный класс для более удобной генерации
текстовых результатов работы счётчиков.

Вмето того, чтобы использовать множество функций.
Проще будет использовать всего один класс.

Старый вариант:

.. code-block:: python

    from sp.counters import days_counter
    from sp.parser import Schedule
    from sp.messages import send_counter

    sc = Schedule()
    res = days_counter(sc, sc.construct_intent())
    groups = group_counter_res(res)
    message = send_counter(groups, target="cl")

Новый вариант:

.. code-block:: python

    from sp.counters import CounterTarget
    from sp.parser import Schedule
    from sp.text_counter import TextCounter, CounterTarget

    sc = Schedule()
    counter = TextCounter(sc)
    message = counter.days(
        sc.construct_intent(),
        target=CounterTarget.CL
    )
"""

from enum import Enum
from typing import Optional

from sp.parser import Schedule
from sp.messages import send_counter
from sp.intents import Intent
from sp.counters import (
    group_counter_res, cl_counter, days_counter, index_counter, CounterTarget
)


class TextCounter:
    """Вспомогательный класс для более удобной работы со счётчиками
    элементов расписания.

    Предоставляет доступ к счётчикам расписнаия.
    Предварительно обработв результат и собрав текстовые сообщения.

    :param sc: Экземпляр расписания, для которого считать элементы.
    :type sc: Schedule
    """
    def __init__(self, sc: Schedule):
        self.sc = sc

    def cl(self, intent: Intent, target: Optional[CounterTarget]=None) -> str:
        """Счётчик по классам в расписании (sc.lessons).

        Является обёрткой над cl_counter.
        Группирует результаты и формарует текстовое сообщение.
        Использует намерения, для уточнения результатов подсчётов.
        Вы также можете выбрать какую отображать подгруппу.

        **Доступные подгруппы**:

        - CounterTarget.DAYS.
        - CounterTarget.LESSONS.
        - CounterTarget.CABINETS.

        Пример использования:

        .. code-block:: python

            from sp.counters import CounterTarget
            from sp.parser import Schedule
            from sp.text_counter import TextCounter

            sc = Schedule()
            counter = TextCounter(sc)
            message = counter.cl(sc.construct_intent())

        :param intent: Намерение для уточнения результатов подсчёта.
        :type intent: Intent
        :param target: Какую добавить подгруппу.
        :type target: Optional[CounterTarget]
        :return: Сообщение с результатом работы счётчика.
        :rtype: str
        """
        return send_counter(
            groups=group_counter_res(cl_counter(self.sc, intent)),
            target=target
        )

    def days(self, intent: Intent, target: Optional[CounterTarget]=None) -> str:
        """Счётчик по дням в расписании (sc.lessons).

        Является обёрткой над days_counter.
        Группирует результаты и формарует текстовое сообщение.
        Использует намерения, для уточнения результатов подсчётов.
        Вы также можете выбрать какую отображать подгруппу.

        **Доступные подгруппы**:

        - CounterTarget.CL.
        - CounterTarget.LESSONS.
        - CounterTarget.CABINETS.

        Пример использования:

        .. code-block:: python

            from sp.counters import CounterTarget
            from sp.parser import Schedule
            from sp.text_counter import TextCounter

            sc = Schedule()
            counter = TextCounter(sc)
            message = counter.days(
                sc.construct_intent(),
                target=CounterTarget.CL
            )

        :param intent: Намерение для уточнения результатов подсчёта.
        :type intent: Intent
        :param target: Какую добавить подгруппу.
        :type target: Optional[CounterTarget]
        :return: Сообщение с результатом работы счётчика.
        :rtype: str
        """
        return send_counter(
            groups=group_counter_res(days_counter(self.sc, intent)),
            target=target,
            days_counter=True
        )

    def index(
        self,
        intent: Intent,
        cabinets_mode: Optional[bool]=False,
        target: Optional[CounterTarget]=None) -> str:
        """Счётчик по урокам/кабинетам в расписании (имдексам).

        Является обёрткой над index_counter.
        Группирует результаты и формарует текстовое сообщение.
        Использует намерения, для уточнения результатов подсчётов.
        Вы также можете выбрать какую отображать подгруппу.

        **Доступные подгруппы**:

        - CounterTarget.CL.
        - CounterTarget.DAYS.
        - CounterTarget.MAIN.

        Пример использования:

        .. code-block:: python

            from sp.counters import CounterTarget
            from sp.parser import Schedule
            from sp.text_counter import TextCounter

            sc = Schedule()
            counter = TextCounter(sc)
            message = counter.index(
                sc.construct_intent(),
                cabinets_mode=True,
                target=CounterTarget.CL
            )

        :param intent: Намерение для уточнения результатов подсчёта.
        :type intent: Intent
        :param cabinets_mode: Использовать индекс кабинетов.
        :param target: Какую добавить подгруппу.
        :type target: Optional[CounterTarget]
        :return: Сообщение с результатом работы счётчика.
        :rtype: str
        """
        return send_counter(
            groups=group_counter_res(index_counter(
                self.sc, intent, cabinets_mode
            )),
            target=target
        )
