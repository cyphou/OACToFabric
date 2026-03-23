"""Graceful shutdown handler — intercept SIGINT/SIGTERM and persist state.

When a migration run is interrupted (Ctrl+C, container shutdown, etc.),
this module ensures:

1. The currently running agent finishes its *current item* (but not
   subsequent items).
2. The checkpoint is saved with the correct resumption point.
3. Open resources (HTTP sessions, file handles) are cleaned up.
4. A non-zero exit code is returned.

Usage::

    from src.core.graceful_shutdown import ShutdownHandler

    handler = ShutdownHandler()
    handler.install()

    # In your main loop
    for item in items:
        if handler.should_stop:
            break
        process(item)

    handler.uninstall()
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shutdown Handler
# ---------------------------------------------------------------------------


class ShutdownHandler:
    """Handles SIGINT/SIGTERM for graceful migration shutdown."""

    def __init__(self) -> None:
        self._should_stop = False
        self._stop_event = threading.Event()
        self._callbacks: list[Callable[[], Any]] = []
        self._original_sigint: Any = None
        self._original_sigterm: Any = None
        self._installed = False
        self._signal_received: str | None = None
        self._signal_count = 0

    @property
    def should_stop(self) -> bool:
        """True if a shutdown signal has been received."""
        return self._should_stop

    @property
    def signal_received(self) -> str | None:
        """Name of the signal that triggered shutdown, if any."""
        return self._signal_received

    @property
    def stop_event(self) -> threading.Event:
        """Event that is set when shutdown is requested."""
        return self._stop_event

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------

    def install(self) -> None:
        """Install signal handlers for SIGINT and SIGTERM.

        Safe to call multiple times; only the first call has effect.
        """
        if self._installed:
            return

        self._original_sigint = signal.getsignal(signal.SIGINT)
        self._original_sigterm = signal.getsignal(signal.SIGTERM)

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self._installed = True
        logger.debug("Shutdown handler installed")

    def uninstall(self) -> None:
        """Restore original signal handlers."""
        if not self._installed:
            return

        if self._original_sigint is not None:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm)

        self._installed = False
        logger.debug("Shutdown handler uninstalled")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_shutdown(self, callback: Callable[[], Any]) -> None:
        """Register a callback to run during graceful shutdown.

        Callbacks are executed in registration order when a signal is
        received.
        """
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # Signal handler
    # ------------------------------------------------------------------

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Handle incoming SIGINT or SIGTERM."""
        sig_name = signal.Signals(signum).name
        self._signal_count += 1
        self._signal_received = sig_name

        if self._signal_count == 1:
            logger.warning(
                "Received %s — initiating graceful shutdown. "
                "Press Ctrl+C again to force exit.",
                sig_name,
            )
            self._should_stop = True
            self._stop_event.set()
            self._run_callbacks()
        else:
            # Second signal — force exit
            logger.critical(
                "Received %s again — forcing immediate exit.", sig_name
            )
            sys.exit(128 + signum)

    def _run_callbacks(self) -> None:
        """Execute registered shutdown callbacks."""
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                logger.exception("Error in shutdown callback: %s", cb)

    # ------------------------------------------------------------------
    # Async support
    # ------------------------------------------------------------------

    async def wait_for_shutdown(self, timeout: float | None = None) -> bool:
        """Async wait until a shutdown signal is received.

        Returns True if shutdown was requested, False on timeout.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._stop_event.wait, timeout
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> ShutdownHandler:
        self.install()
        return self

    def __exit__(self, *args: Any) -> None:
        self.uninstall()

    # ------------------------------------------------------------------
    # Reset (for testing)
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset internal state. Useful for tests."""
        self._should_stop = False
        self._stop_event.clear()
        self._signal_received = None
        self._signal_count = 0
        self._callbacks.clear()
