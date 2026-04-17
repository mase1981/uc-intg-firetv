"""
Fire TV helper.
This is a helper library with useful tools.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import sys
import asyncio
import logging
from typing import Awaitable, Callable, Optional

_LOG = logging.getLogger(__name__)


class AsyncDebounceTimer:
    def __init__(self, delay: float):
        self.delay = delay
        self._task: Optional[asyncio.Task] = None

    def setDelayMS(self, delayMS: int):
        self.delay = delayMS / 1000

    def trigger(self, coro_func: Callable[[], Awaitable], *args, **kwargs):
        if self._task and not self._task.done():
            self._task.cancel()

        self._task = asyncio.create_task(self._run(coro_func, *args, **kwargs))

    async def _run(self, coro_func: Callable[[], Awaitable], *args, **kwargs):
        try:
            await asyncio.sleep(self.delay)
            await coro_func(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOG.error(f"Error in debounce task: {e}")


def get_my_name():
    """Helper function for logging: Get name of function that is calling this."""
    return sys._getframe().f_back.f_code.co_name
