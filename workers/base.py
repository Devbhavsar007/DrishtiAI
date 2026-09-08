"""Base worker class for background services."""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Abstract base worker with thread lifecycle and safe shutdown."""

    def __init__(self, name: str, interval_seconds: float = 10.0):
        self.name = name
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_heartbeat: float = 0.0

    def start(self) -> None:
        """Start the worker thread."""
        if self._thread and self._thread.is_alive():
            log.warning("Worker %s is already running", self.name)
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name=self.name, daemon=True)
        self._thread.start()
        log.info("Worker %s started (interval=%.1fs)", self.name, self.interval_seconds)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the worker to stop and wait for termination."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        log.info("Worker %s stopped", self.name)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self._last_heartbeat = time.time()
            try:
                self.step()
            except Exception as e:
                log.error("Unhandled exception in worker %s: %s", self.name, e, exc_info=True)

            self._stop_event.wait(self.interval_seconds)

    @abstractmethod
    def step(self) -> None:
        """Execute a single polling/work cycle."""
        pass

    @property
    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
