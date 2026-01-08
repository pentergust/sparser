"""Автоматическая проверка обновлений."""

import asyncio

from loguru import logger

from provider.provider import Provider


class Checker:
    """Таймер для проверки событий."""

    def __init__(self, provider: Provider) -> None:
        self._provider = provider
        self._task: asyncio.Task[None] | None = None
        self._stop_next: bool = False

    async def run(self) -> None:
        """Start the timer task."""
        self._task = asyncio.create_task(self._loopy_loop())
        self._task.add_done_callback(self._handle_result)

    def stop(self) -> None:
        """Gracefully stop the loop."""
        if self._task and not self._task.done():
            self._stop_next = True

    def cancel(self) -> None:
        """Cancel the loop."""
        if not self._task:
            return

        self._task.cancel()
        self._task = None

    async def _loopy_loop(self) -> None:
        """Implement main loop logic."""
        try:
            await self._provider.update()
        except Exception as e:
            logger.exception(e)

        while not self._stop_next:
            await asyncio.sleep(1080)  # 30 minutes
            try:
                await self._provider.update()
            except Exception as e:
                logger.exception(e)
        self.cancel()

    def _handle_result(self, task: asyncio.Task[None]) -> None:
        """Handle the result of the task."""
        if task.cancelled():
            return

        try:
            task.result()
        except Exception as e:
            logger.exception(e)
