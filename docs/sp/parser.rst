parser
======

.. automodule:: sp.parser


Функции для работы с расписанием
--------------------------------

Некоторые отдельные функции, которые используются при работе
с расписанием и могут быть использованы отдельно от экземпляра класса
`Scheule`.

.. autofunction:: get_sc_updates

.. autofunction:: get_index

.. autofunction:: parse_lessons


Класс расписания
----------------

Используется для прямой работы с самим расписанием уроков.
Предоставляет так называемые "сырые" результаты.
Которые вы после можете самостоятельно обработать.

.. hint:: Генератор сообщений.

    Если же вас интересует готовый результат, обратитесь к
    классу представления или так называемому **генератору сообщений**
    :py:class:`sp.messages.SPMessages`.
    В отличие от класса расписания, класс представления возвращает
    уже готовые текстовые сообщения, которые вы можете испльзовать
    например в чат-ботах.

.. autoclass:: sp.parser.Schedule

    .. autoattribute:: schedule
    .. autoattribute:: lessons

    .. tip::

        Более подробно прочитать про значение `schedule` можно в методе
        `get`.

        Более побробно почитать про значение `lessons` можно в функции
        `parse_lessons`.

    Аттрибуты расписания:

    .. autoproperty:: l_index
    .. autoproperty:: c_index
    .. autoproperty:: updates

    Методы для получения расписания:

    .. automethod:: get

    Методы для работы с расписанием:

    .. automethod:: get_class
    .. automethod:: get_lessons
    .. automethod:: get_updates
    .. automethod:: search

    Методы для работы с намерениями:

    .. automethod:: construct_intent
    .. automethod:: parse_intent


Смотрите также
--------------

- :doc:`messages` - Генератор текстовых сообещний расписания.