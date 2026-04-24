"""Tests for command handlers module.

Tests handlers.py: command handlers with mocked gdb module.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock

# Mock gdb module before any imports that depend on it
sys.modules['gdb'] = MagicMock()

# Set up the server directory for value_formatter import
_server_dir = str(Path(__file__).parent.parent / "src" / "gdb_cli" / "gdb_server")
os.environ["GDB_CLI_SERVER_DIR"] = _server_dir


class TestHandleExec(unittest.TestCase):
    """Test raw command execution handler with safety filtering."""

    def setUp(self):
        import importlib

        import gdb_cli.gdb_server.handlers as handlers_mod
        importlib.reload(handlers_mod)
        self.handlers = handlers_mod

    def test_exec_allowed_read_command(self):
        """exec of a read command should be allowed."""
        # Make gdb.post_event call the function directly
        sys.modules['gdb'].post_event = lambda fn: fn()
        sys.modules['gdb'].execute = Mock(return_value="#0 main at foo.c:10")

        result = self.handlers.handle_exec("bt", safety_level="readonly")
        self.assertIn("command", result)
        self.assertEqual(result["command"], "bt")

    def test_exec_shell_blocked(self):
        """exec of 'shell' must be blocked."""
        result = self.handlers.handle_exec("shell ls", safety_level="readonly")
        self.assertIn("error", result)

    def test_exec_python_blocked(self):
        """exec of 'python' must be blocked (Issue #1 fix)."""
        result = self.handlers.handle_exec("python import os; os.system('id')", safety_level="readonly")
        self.assertIn("error", result)

    def test_exec_python_interactive_blocked(self):
        """exec of 'python-interactive' must be blocked."""
        result = self.handlers.handle_exec("python-interactive", safety_level="readonly")
        self.assertIn("error", result)

    def test_exec_quit_blocked(self):
        """exec of 'quit' must be blocked."""
        result = self.handlers.handle_exec("quit", safety_level="readonly")
        self.assertIn("error", result)

    def test_exec_kill_blocked(self):
        """exec of 'kill' must be blocked."""
        result = self.handlers.handle_exec("kill", safety_level="readonly")
        self.assertIn("error", result)

    def test_exec_signal_blocked(self):
        """exec of 'signal' must be blocked."""
        result = self.handlers.handle_exec("signal 9", safety_level="readonly")
        self.assertIn("error", result)

    def test_exec_set_blocked_in_readonly(self):
        """exec of 'set' must be blocked in readonly mode."""
        result = self.handlers.handle_exec("set variable x=42", safety_level="readonly")
        self.assertIn("error", result)

    def test_exec_set_allowed_in_full(self):
        """exec of 'set' must be allowed in full mode."""
        # Make gdb.post_event call the function directly
        sys.modules['gdb'].post_event = lambda fn: fn()
        sys.modules['gdb'].execute = Mock(return_value="")

        result = self.handlers.handle_exec("set variable x=42", safety_level="full")
        self.assertNotIn("error", result)

    def test_exec_attach_blocked(self):
        """exec of 'attach' must be blocked."""
        result = self.handlers.handle_exec("attach 12345", safety_level="full")
        self.assertIn("error", result)

    def test_exec_detach_blocked(self):
        """exec of 'detach' must be blocked."""
        result = self.handlers.handle_exec("detach", safety_level="full")
        self.assertIn("error", result)

    def test_exec_target_blocked(self):
        """exec of 'target' must be blocked."""
        result = self.handlers.handle_exec("target extended-remote :3333", safety_level="full")
        self.assertIn("error", result)


class TestHandleThreadApply(unittest.TestCase):
    """Test thread_apply handler with safety filtering."""

    def setUp(self):
        import importlib

        import gdb_cli.gdb_server.handlers as handlers_mod
        importlib.reload(handlers_mod)
        self.handlers = handlers_mod

    def test_thread_apply_shell_blocked(self):
        """thread-apply with 'shell' must be blocked (Issue #2 fix)."""
        # Mock inferior threads
        mock_thread = Mock()
        mock_thread.num = 1
        mock_inferior = Mock()
        mock_inferior.threads.return_value = [mock_thread]
        sys.modules['gdb'].selected_inferior = Mock(return_value=mock_inferior)
        sys.modules['gdb'].selected_thread = Mock(return_value=mock_thread)

        result = self.handlers.handle_thread_apply(
            command="shell ls",
            all_threads=True,
            safety_level="readonly",
        )
        self.assertIn("error", result)

    def test_thread_apply_python_blocked(self):
        """thread-apply with 'python' must be blocked (Issue #2 fix)."""
        mock_thread = Mock()
        mock_thread.num = 1
        mock_inferior = Mock()
        mock_inferior.threads.return_value = [mock_thread]
        sys.modules['gdb'].selected_inferior = Mock(return_value=mock_inferior)
        sys.modules['gdb'].selected_thread = Mock(return_value=mock_thread)

        result = self.handlers.handle_thread_apply(
            command="python import os",
            all_threads=True,
            safety_level="readonly",
        )
        self.assertIn("error", result)

    def test_thread_apply_quit_blocked(self):
        """thread-apply with 'quit' must be blocked."""
        mock_thread = Mock()
        mock_thread.num = 1
        mock_inferior = Mock()
        mock_inferior.threads.return_value = [mock_thread]
        sys.modules['gdb'].selected_inferior = Mock(return_value=mock_inferior)
        sys.modules['gdb'].selected_thread = Mock(return_value=mock_thread)

        result = self.handlers.handle_thread_apply(
            command="quit",
            all_threads=True,
            safety_level="readonly",
        )
        self.assertIn("error", result)

    def test_thread_apply_allowed_read_command(self):
        """thread-apply with 'bt' should be allowed."""
        mock_thread = Mock()
        mock_thread.num = 1
        mock_inferior = Mock()
        mock_inferior.threads.return_value = [mock_thread]
        sys.modules['gdb'].selected_inferior = Mock(return_value=mock_inferior)
        sys.modules['gdb'].selected_thread = Mock(return_value=mock_thread)
        sys.modules['gdb'].execute = Mock(return_value="#0 main at foo.c:10")

        result = self.handlers.handle_thread_apply(
            command="bt",
            all_threads=True,
            safety_level="readonly",
        )
        self.assertNotIn("error", result)
        self.assertIn("results", result)


class TestHandleEval(unittest.TestCase):
    """Test eval expression handler."""

    def setUp(self):
        import importlib

        import gdb_cli.gdb_server.handlers as handlers_mod
        importlib.reload(handlers_mod)
        self.handlers = handlers_mod

    def test_eval_simple_expression(self):
        """Test eval simple expression returns expression key."""
        mock_val = Mock()
        mock_val.type.name = "int"
        mock_val.type.code = 1
        mock_val.__str__ = Mock(return_value="42")
        sys.modules['gdb'].parse_and_eval = Mock(return_value=mock_val)

        result = self.handlers.handle_eval("42")
        self.assertIn("expression", result)
        self.assertEqual(result["expression"], "42")

    def test_eval_variable(self):
        """Test eval variable expression."""
        mock_val = Mock()
        mock_val.type.name = "int"
        mock_val.type.code = 1
        mock_val.__str__ = Mock(return_value="7")
        sys.modules['gdb'].parse_and_eval = Mock(return_value=mock_val)

        result = self.handlers.handle_eval("x")
        self.assertIn("expression", result)
        self.assertEqual(result["expression"], "x")


class TestHandleThreads(unittest.TestCase):
    """Test threads listing handler."""

    def setUp(self):
        import importlib

        import gdb_cli.gdb_server.handlers as handlers_mod
        importlib.reload(handlers_mod)
        self.handlers = handlers_mod

    def test_threads_basic(self):
        """Test basic threads listing."""
        t1 = Mock()
        t1.num = 1
        t1.ptid = (1, 1, 0)
        t1.name = "Thread 1"
        t1.is_running.return_value = False
        t1.is_stopped.return_value = True

        mock_inferior = Mock()
        mock_inferior.threads.return_value = [t1]
        sys.modules['gdb'].selected_inferior = Mock(return_value=mock_inferior)

        result = self.handlers.handle_threads()
        self.assertIn("threads", result)
        self.assertGreaterEqual(len(result["threads"]), 1)


class TestHandleStatus(unittest.TestCase):
    """Test session status handler."""

    def setUp(self):
        import importlib

        import gdb_cli.gdb_server.handlers as handlers_mod
        importlib.reload(handlers_mod)
        self.handlers = handlers_mod

    def test_status_returns_session_meta(self):
        """Test status returns session metadata."""
        session_meta = {"mode": "core", "binary": "./myapp", "core": "./core.1234"}
        result = self.handlers.handle_status(_session_meta=session_meta)
        self.assertIn("mode", result)
        self.assertEqual(result["mode"], "core")


if __name__ == "__main__":
    unittest.main()
