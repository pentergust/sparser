messages
========

.. automodule:: sp.messages

.. hint:: Новое хранилище пользователй

    Теперь генератор сообщения не отвечает за пользователей.
    Более подробно узнать о работе нового хранилища можно узнать:

    - Хринилище пользователей: :py:class:`sp.users.storage.FileUserStorage`.
    - Пользователь: :py:class:`sp.users.storage.User`.


Расписание звонков
------------------

.. caution:: Это временное решение.

    Эти методы не должны здесь находится, однако они тут.
    До того как буедт создан класс для работы с расписание звонков
    эти методы будет располагаться в генераторе сообщений.
    Однако мы не рекомендуем вам их сейчас использовать.

.. autoclass:: LessonTime

.. autofunction:: time_to_seconds
.. autofunction:: seconds_to_time
.. autofunction:: get_current_lesson


Функции отображения
-------------------

Используеются для преобразования "сырых" данных расписания в готовые
текстовые сообщения, которые можно использовать в чат-ботах.

.. autofunction:: send_day_lessons
.. autofunction:: send_search_res


Генератор сообщений
-------------------

.. autoclass:: SPMessages

    .. autoattribute:: sc

    .. automethod:: send_status

    .. automethod:: get_current_day
    .. automethod:: send_lessons
    .. automethod:: send_today_lessons

    .. automethod:: search
    .. automethod:: send_update
    .. automethod:: check_updates
    .. automethod:: send_counter
