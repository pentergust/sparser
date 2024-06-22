User Intents storage
====================

.. automodule:: sp.users.intents

.. autoclass:: IntentObject

.. note:: Историческая справка

    Первоначально хранилище намерений появилось в рамках ``sp_tg``.
    Однако после было перенесено внутрь ядра проекта.
    Поскольку функционал работы с намерениями пользователя вскоре
    вытеснет такое понятие как **Класс по умолчанию**.
    Поскольку класс по умолчанию свого рода тоже является намерением
    получить конкретный класс из расписания.

.. autoclass:: UserIntentsStorage

    Список намерений
    ----------------

    .. automethod:: get
    .. automethod:: get_intent
    .. automethod:: remove_all

    Редактирование намерений
    ------------------------

    .. automethod:: add
    .. automethod:: rename
    .. automethod:: remove
