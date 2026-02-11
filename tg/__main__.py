"""Точка входа для запуска бота.

```sh
uv run -m tg
```
"""

import asyncio

from tg.bot import main

if __name__ == "__main__":
    asyncio.run(main())
