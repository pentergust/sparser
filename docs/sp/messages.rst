messages
========

.. automodule:: sp.messages

.. hint:: Новое хранилище пользователй

    Теперь генератор сообщения не отвечает за пользователей.
    Более подробно узнать о работе нового хранилища можно узнать:

    - Хринилище пользователей: :py:class:`sp.users.storage.FileUserStorage`.
    - Пользователь :py:class:`sp.users.storage.User`.


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


Список изменений
----------------

Вспомогательные функции, которые используются для просмотра
списка изменений уроков в расписании.

.. caution:: Перенос функицй

    Поскольку больше нет надобность указывать пользователя.
    Можно спокойно использовать методы платформы вне заисимости от
    пользователя.
    Так что надобность данных функций отпадает.
    Вскоре они будут перемещены внутрь класса представления.

.. autofunction:: send_cl_updates
.. autofunction:: get_update_header
.. autofunction:: send_update


Функции отображения
-------------------

Используеются для преобразования "сырых" данных расписания в готовые
текстовые сообщения, которые можно использовать в чат-ботах.

.. autofunction:: send_day_lessons
.. autofunction:: send_search_res
.. autofunction:: send_counter


Генератор сообщений
-------------------

.. autoclass:: SPMessages

    .. autoattribute:: sc

    .. automethod:: send_status

    .. automethod:: send_lessons
    .. automethod:: send_today_lessons
    .. automethod:: get_current_day

    .. automethod:: search
