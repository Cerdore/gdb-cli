"""Tests for CLI async load/status behavior without requiring Click at runtime."""

import importlib
import sys
import time
import types
import unittest
from unittest.mock import Mock, patch


class _FakeGroup:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def command(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator


class _FakeClick(types.SimpleNamespace):
    class ClickException(Exception):
        pass

    class exceptions:
        class Exit(Exception):
            def __init__(self, code=0):
                super().__init__(code)
                self.exit_code = code

    @staticmethod
    def group(*args, **kwargs):
        def decorator(func):
            return _FakeGroup(func)
        return decorator

    @staticmethod
    def version_option(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    @staticmethod
    def option(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    @staticmethod
    def argument(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    @staticmethod
    def Choice(values):
        return values

    @staticmethod
    def echo(*args, **kwargs):
        return None


class TestCLIAsyncBehavior(unittest.TestCase):
    """Verify CLI surface behavior for async load/status."""

    @classmethod
    def setUpClass(cls):
        sys.modules["click"] = _FakeClick()
        cls.cli = importlib.import_module("gdb_cli.cli")

    def test_load_reports_loading_status(self):
        fake_process = Mock()
        fake_process.pid = 12345
        fake_process.session = types.SimpleNamespace(
            session_id="abc12345",
            mode="core",
            binary="/tmp/a.out",
            core="/tmp/core.1",
            sock_path="/tmp/test.sock",
        )

        with patch.object(self.cli, "find_session_by_core", return_value=None), \
             patch.object(self.cli, "launch_core", return_value=fake_process), \
             patch.object(self.cli, "print_json") as mock_print_json:
            self.cli.load("/tmp/a.out", "/tmp/core.1", None, None, None, 600, "gdb")

        payload = mock_print_json.call_args.args[0]
        self.assertEqual(payload["status"], "loading")
        self.assertEqual(payload["session_id"], "abc12345")

    def test_status_falls_back_to_loading_when_process_alive(self):
        meta = types.SimpleNamespace(gdb_pid=12345, started_at=time.time() - 150)

        with patch.object(self.cli, "get_client", side_effect=self.cli.GDBClientError("socket not ready")), \
             patch.object(self.cli, "get_session", return_value=meta), \
             patch.object(self.cli.os, "kill", return_value=None), \
             patch.object(self.cli, "print_json") as mock_print_json:
            self.cli.status("abc12345")

        payload = mock_print_json.call_args.args[0]
        self.assertEqual(payload["state"], "loading")
        self.assertEqual(payload["session_id"], "abc12345")

    def test_status_errors_when_session_dead(self):
        meta = types.SimpleNamespace(gdb_pid=12345)

        with patch.object(self.cli, "get_client", side_effect=self.cli.GDBClientError("socket not ready")), \
             patch.object(self.cli, "get_session", return_value=meta), \
             patch.object(self.cli.os, "kill", side_effect=OSError()), \
             patch.object(self.cli, "print_error") as mock_print_error:
            with self.assertRaises(self.cli.click.exceptions.Exit):
                self.cli.status("abc12345")

        mock_print_error.assert_called_once()

    def test_status_errors_when_session_missing(self):
        with patch.object(self.cli, "get_client", side_effect=self.cli.GDBClientError("socket not ready")), \
             patch.object(self.cli, "get_session", return_value=None), \
             patch.object(self.cli, "print_error") as mock_print_error:
            with self.assertRaises(self.cli.click.exceptions.Exit):
                self.cli.status("missing")

        mock_print_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
