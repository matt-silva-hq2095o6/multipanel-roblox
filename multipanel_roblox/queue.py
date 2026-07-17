import asyncio
import logging
from typing import Callable, Coroutine, Any, List, Tuple

logger = logging.getLogger("multipanel_roblox.queue")


class ActionQueue:
    """Worker pool for firing off parallel requests without hitting Open Cloud rate limits."""

    def __init__(self, concurrency: int = 4, delay_between: float = 0.15):
        self.concurrency = concurrency
        self.delay = delay_between
        self._queue: asyncio.Queue = asyncio.Queue()
        self._results: List[Any] = []
        self._errors: List[Tuple[str, Exception]] = []
        self._running = False

    async def add(self, tag: str, coro_fn: Callable[..., Coroutine], *args, **kwargs):
        await self._queue.put((tag, coro_fn, args, kwargs))

    async def _worker(self):
        while True:
            try:
                tag, coro_fn, args, kwargs = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                if not self._running:
                    break
                await asyncio.sleep(0.05)
                continue

            try:
                res = await coro_fn(*args, **kwargs)
                self._results.append((tag, res))
            except Exception as e:
                # print(f"DEBUG fail on {tag}: {e}")
                logger.debug("queue action %s failed: %s", tag, e)
                self._errors.append((tag, e))
            finally:
                self._queue.task_done()
                # Open Cloud limits are universe-bound; small sleep protects against bursting
                if self.delay > 0:
                    await asyncio.sleep(self.delay)

    async def run_all(self) -> Tuple[List[Any], List[Tuple[str, Exception]]]:
        self._running = True
        workers = [asyncio.create_task(self._worker()) for _ in range(self.concurrency)]
        await self._queue.join()
        self._running = False
        await asyncio.gather(*workers, return_exceptions=True)
        return self._results, self._errors
