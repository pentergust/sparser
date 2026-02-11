"""Отправная точна для запуска бота.

Запускает функцию для запуска бота.
Которая в свою очередь запускает Long polling.

```sh
poetry run python -m tg
```
"""

import asyncio

from tg.bot import main

if __name__ == "__main__":
    asyncio.run(main())
