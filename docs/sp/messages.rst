messages
========

.. automodule:: sp.messages


Вспомогательные функции
-----------------------

.. autofunction:: get_complited_lessons


Список изменений
----------------

Вспомогательные функции, которые используются для просмотра
списка изменений уроков в расписании.

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

    .. autoattribute:: user
    .. autoattribute:: sc

    .. automethod:: send_status

    Управление пользователями:

    .. deprecated:: v5.8

        Обновление будет посвящено отделению функционала генератора
        сообщений и хранилиа пользователей.

    .. automethod:: get_user
    .. automethod:: save_user
    .. automethod:: reset_user
    .. automethod:: set_class
    .. automethod:: get_lessons_updates

    Методы для работы с расписанием:

    .. automethod:: search
