counters
========

.. automodule:: sp.counters

.. autoclass:: CounterTarget

Вспомогательные функции
-----------------------

Используеются для поддержания работы основных функций счётчиков.

.. autofunction:: group_counter_res
.. autofunction:: reverse_counter


Функции счётчиков
-----------------

Это базовые счётчики, которые используются для подсчёта количества
элементов в расписании.
Возможно после будет переписан как отдельный класс.

Используйте базовые счётчики, если планируете самостоятельно
обрабатывать результат подсчётов.

.. autofunction:: cl_counter
.. autofunction:: days_counter
.. autofunction:: index_counter
