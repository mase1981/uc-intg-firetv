"""
Fire TV debounce Timer
This is used to "unpress" a key after a configurable delay

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import threading
import time

class DebounceTimer:
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