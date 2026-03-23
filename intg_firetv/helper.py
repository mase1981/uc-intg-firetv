"""
Fire TV helper
This is a helper library with useful tools

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import threading
import time
import sys
import asyncio
from typing import Awaitable, Callable, Optional

class AsyncDebounceTimer:
    def __init__(self, delay: float):
        self.delay = delay
        self._task: Optional[asyncio.Task] = None

    def trigger(self, coro_func: Callable[[], Awaitable], *args, **kwargs):
        # Alten Timer abbrechen
        if self._task and not self._task.done():
            self._task.cancel()

        # Neuen Timer starten
        self._task = asyncio.create_task(self._run(coro_func, *args, **kwargs))

    async def _run(self, coro_func: Callable[[], Awaitable], *args, **kwargs):
        try:
            await asyncio.sleep(self.delay)
            await coro_func(*args, **kwargs)
        except asyncio.CancelledError:
            # Erwartet beim Debounce
            pass
        except Exception as e:
            # Optional: Logging
            print(f"Fehler im Debounce-Task: {e}")

class DebounceTimer:
    """This class is used to "unpress" a key after a configurable delay"""
    def __init__(self, delay, action):
        self.delay = delay
        self.action = action
        self.timer = None
        self.lock = threading.Lock()

    def trigger(self, *args, **kwargs):
        with self.lock:
            if self.timer:
                self.timer.cancel()

            self.timer = threading.Timer(
                self.delay,
                self.action,
                args=args,
                kwargs=kwargs
            )
            self.timer.start()

    def cancel(self):
        with self.lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None

def get_my_name():
    """Helper function for logging: Get name of function that is calling this"""
    return sys._getframe().f_back.f_code.co_name
