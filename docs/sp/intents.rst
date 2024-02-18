intents
=======

.. automodule:: sp.intents

.. autoclass:: Intent

    .. autoattribute:: cl
    .. autoattribute:: days
    .. autoattribute:: lessons
    .. autoattribute:: cabinets

    .. automethod:: to_str

    Сборка намерения
    ----------------

    Методы, используемые для сборки новоего намерения.

    .. automethod:: from_str

    .. automethod:: construct
    .. automethod:: parse

    Пересборка намерения
    --------------------

    Методы чтобы создать новое намерение, основываясь на старом.

    .. deprecated:: v5.7

        Считаются устаревшими и будут удалены вместе с классом Intents.

    .. automethod:: reconstruct
    .. automethod:: reparse
