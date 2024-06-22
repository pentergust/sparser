"""Отправная точна для запуска бота.

.. code-block:: shell

    python -m sp_tg
"""

import asyncio

from sp_tg.bot import main

if __name__ == "__main__":
    asyncio.run(main())
