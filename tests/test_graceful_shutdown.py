"""Tests for the graceful shutdown handler."""

from __future__ import annotations

import signal
import pytest

from src.core.graceful_shutdown import ShutdownHandler


# ---------------------------------------------------------------------------
# Basic state
# ---------------------------------------------------------------------------


class TestShutdownHandlerState:
    def test_initial_state(self):
        handler = ShutdownHandler()
        assert not handler.should_stop
        assert handler.signal_received is None

    def test_install_and_uninstall(self):
        handler = ShutdownHandler()
        handler.install()
        assert True  # Should not raise
        handler.uninstall()

    def test_double_install_is_safe(self):
        handler = ShutdownHandler()
        handler.install()
        handler.install()  # Second call should be no-op
        handler.uninstall()

    def test_double_uninstall_is_safe(self):
        handler = ShutdownHandler()
        handler.install()
        handler.uninstall()
        handler.uninstall()  # Second call should be no-op

    def test_context_manager(self):
        with ShutdownHandler() as handler:
            assert not handler.should_stop
        # Uninstall happens automatically


# ---------------------------------------------------------------------------
# Signal simulation
# ---------------------------------------------------------------------------


class TestShutdownSignalHandling:
    def test_simulated_sigint_sets_should_stop(self):
        handler = ShutdownHandler()
        handler.install()
        try:
            # Simulate receiving SIGINT
            handler._handle_signal(signal.SIGINT, None)
            assert handler.should_stop
            assert handler.signal_received == "SIGINT"
        finally:
            handler.uninstall()

    def test_simulated_sigterm_sets_should_stop(self):
        handler = ShutdownHandler()
        handler.install()
        try:
            handler._handle_signal(signal.SIGTERM, None)
            assert handler.should_stop
            assert handler.signal_received == "SIGTERM"
        finally:
            handler.uninstall()

    def test_stop_event_is_set(self):
        handler = ShutdownHandler()
        handler.install()
        try:
            assert not handler.stop_event.is_set()
            handler._handle_signal(signal.SIGINT, None)
            assert handler.stop_event.is_set()
        finally:
            handler.uninstall()


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


class TestShutdownCallbacks:
    def test_callback_runs_on_shutdown(self):
        handler = ShutdownHandler()
        handler.install()
        callback_called = []
        handler.on_shutdown(lambda: callback_called.append(True))
        try:
            handler._handle_signal(signal.SIGINT, None)
            assert len(callback_called) == 1
        finally:
            handler.uninstall()

    def test_multiple_callbacks(self):
        handler = ShutdownHandler()
        handler.install()
        results = []
        handler.on_shutdown(lambda: results.append("a"))
        handler.on_shutdown(lambda: results.append("b"))
        handler.on_shutdown(lambda: results.append("c"))
        try:
            handler._handle_signal(signal.SIGINT, None)
            assert results == ["a", "b", "c"]
        finally:
            handler.uninstall()

    def test_callback_error_does_not_prevent_others(self):
        handler = ShutdownHandler()
        handler.install()
        results = []
        handler.on_shutdown(lambda: results.append("before"))
        handler.on_shutdown(lambda: (_ for _ in ()).throw(ValueError("oops")))
        handler.on_shutdown(lambda: results.append("after"))
        try:
            handler._handle_signal(signal.SIGINT, None)
            assert "before" in results
            # "after" should still run despite the error in the middle
            assert "after" in results
        finally:
            handler.uninstall()


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestShutdownReset:
    def test_reset_clears_state(self):
        handler = ShutdownHandler()
        handler.install()
        try:
            handler._handle_signal(signal.SIGINT, None)
            assert handler.should_stop
            handler.reset()
            assert not handler.should_stop
            assert handler.signal_received is None
            assert not handler.stop_event.is_set()
        finally:
            handler.uninstall()


# ---------------------------------------------------------------------------
# Integration: loop pattern
# ---------------------------------------------------------------------------


class TestShutdownLoopPattern:
    def test_loop_stops_on_signal(self):
        handler = ShutdownHandler()
        processed = []

        # Simulate processing items with shutdown mid-way
        items = range(10)
        for i, item in enumerate(items):
            if handler.should_stop:
                break
            processed.append(item)
            # Simulate signal after 3rd item
            if i == 2:
                handler._should_stop = True

        assert len(processed) == 3
        assert processed == [0, 1, 2]
