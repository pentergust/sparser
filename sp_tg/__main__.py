"""Отправная точна для запуска бота.

Запускает функцию для запуска бота.
Которая в свою очередь запускает Long polling.

.. code-block:: shell

    python sp_tg
"""

import asyncio

from sp_tg.bot import main

if __name__ == "__main__":
    asyncio.run(main())
