"""Отправная точна для запуска бота.

Запускает функцию для запуска бота.
Которая в свою очередь запускает Long polling.

```sh
poetry run python -m sp_tg
```
"""

import asyncio

from sp_tg.bot import main

if __name__ == "__main__":
    asyncio.run(main())
