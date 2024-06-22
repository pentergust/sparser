Users storage
=============

.. automodule:: sp.users.storage


Вспомогательные контейнеры
--------------------------

.. autoclass:: UserData
.. autoclass:: CountedUsers


Хранилище пользователей
-----------------------

.. autoclass:: FileUserStorage

    Файл хранилища
    ~~~~~~~~~~~~~~

    .. automethod:: get_users
    .. automethod:: remove_users
    .. automethod:: save_users
    .. automethod:: count_users

    Управление пользователями
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    .. automethod:: create_user
    .. automethod:: get_user
    .. automethod:: set_class
    .. automethod:: unset_class
    .. automethod:: update_user


.. autoclass:: User

    .. automethod:: create
    .. automethod:: remove
    .. automethod:: set_class
    .. automethod:: unset_class
    .. automethod:: save
    .. automethod:: update
    .. automethod:: get_updates

    Настройка оповещений
    ~~~~~~~~~~~~~~~~~~~~

    .. automethod:: set_notify_on
    .. automethod:: set_notify_off
    .. automethod:: add_notify_hour
    .. automethod:: remove_notify_hour
    .. automethod:: reset_notify

