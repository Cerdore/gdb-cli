"""Unit tests for the _format_elapsed() helper in cli.py."""

import importlib
import sys
import types
import unittest


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


class TestFormatElapsed(unittest.TestCase):
    """Boundary tests for _format_elapsed()."""

    @classmethod
    def setUpClass(cls):
        sys.modules["click"] = _FakeClick()
        cls.cli = importlib.import_module("gdb_cli.cli")

    def _f(self, seconds):
        return self.cli._format_elapsed(seconds)

    def test_negative_returns_zero_seconds(self):
        self.assertEqual(self._f(-5), "0s")

    def test_zero(self):
        self.assertEqual(self._f(0), "0s")

    def test_59_seconds(self):
        self.assertEqual(self._f(59), "59s")

    def test_60_seconds(self):
        self.assertEqual(self._f(60), "1m0s")

    def test_150_seconds(self):
        self.assertEqual(self._f(150), "2m30s")

    def test_3600_seconds(self):
        self.assertEqual(self._f(3600), "1h0m")

    def test_3661_seconds(self):
        self.assertEqual(self._f(3661), "1h1m")

    def test_90000_seconds(self):
        self.assertEqual(self._f(90000), "25h0m")


if __name__ == "__main__":
    unittest.main()
