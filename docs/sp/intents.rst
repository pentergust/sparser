Intents
=======

.. automodule:: sp.intents

.. autoclass:: Intent

    .. hint:: Альтернатива

        Помимо встренных методов для создания намерения есть также
        и их синонимы в :py:class:`sp.parser.Schedule`.

        - Для comstruct - :py:func:`sp.parser.Schedule.construct_intent`
        - Для parse - :py:func:`sp.parser.Schedule.parse_intent`

    .. autoattribute:: cl
    .. autoattribute:: days
    .. autoattribute:: lessons
    .. autoattribute:: cabinets

    .. automethod:: to_str

    Сборка намерения
    ----------------

    Различные методы, позволяющие собирать новые намерения.
    Используются как основной способ создания намерений.

    .. automethod:: from_str

    .. automethod:: construct
    .. automethod:: parse

    Пересборка намерения
    --------------------

    Методы чтобы создать новое намерение, основываясь на старом.

    .. deprecated:: v5.7

        Считаются устаревшими и будут удалены вместе с классом Intents.

        - Метод ``reparse`` удалён в версии ``v6.1``.

    .. automethod:: reconstruct
