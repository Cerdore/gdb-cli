"""Tests for async load command ordering and loading state handling."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gdb_cli.session import SessionMeta


class TestLaunchCoreAsyncOrder(unittest.TestCase):
    """Ensure core loading starts the RPC server before heavy file/core work."""

    @patch("gdb_cli.launcher._start_gdb_process")
    @patch("gdb_cli.launcher.create_session")
    def test_launch_core_starts_server_before_file_and_core(self, mock_create_session, mock_start):
        from gdb_cli.launcher import launch_core

        session = SessionMeta(
            session_id="test1234",
            mode="core",
            binary="/tmp/a.out",
            core="/tmp/core.1",
            sock_path="/tmp/test.sock",
            heartbeat_timeout=123,
        )
        session._gdb_process = Mock(pid=4321)
        mock_create_session.return_value = session

        result = launch_core(
            binary="/tmp/a.out",
            core="/tmp/core.1",
            timeout=123,
        )

        self.assertEqual(result.session.session_id, "test1234")
        args = mock_start.call_args.args[0]
        commands = [args[i + 1] for i, value in enumerate(args[:-1]) if value == "-ex"]

        start_index = commands.index(next(cmd for cmd in commands if "start_server(" in cmd))
        file_index = commands.index("file /tmp/a.out")
        core_index = commands.index("core-file /tmp/core.1")
        ready_index = commands.index("python _gdb_rpc_server.set_ready()")

        self.assertLess(start_index, file_index)
        self.assertLess(file_index, core_index)
        self.assertLess(core_index, ready_index)
        self.assertEqual(mock_start.call_args.kwargs["timeout"], 123.0)


class TestGDBRPCServerLoadingState(unittest.TestCase):
    """Verify loading mode only exposes safe commands."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        os.environ["GDB_CLI_SERVER_DIR"] = str(
            Path(__file__).resolve().parent.parent / "src" / "gdb_cli" / "gdb_server"
        )

        gdb_mock = Mock()
        gdb_mock.MemoryError = type("MemoryError", (Exception,), {})
        gdb_mock.error = type("GDBError", (Exception,), {})
        gdb_mock.events = Mock()
        gdb_mock.events.new_objfile = Mock()
        gdb_mock.events.new_objfile.connect = Mock()
        gdb_mock.events.before_prompt = Mock()
        gdb_mock.events.before_prompt.connect = Mock()
        gdb_mock.write = Mock()
        sys.modules["gdb"] = gdb_mock

    def test_dispatch_blocks_non_status_while_loading(self):
        from gdb_cli.gdb_server.gdb_rpc_server import GDBRPCServer

        server = GDBRPCServer(
            sock_path=str(Path(self.temp_dir) / "sock"),
            session_meta={"session_id": "abc123", "mode": "core"},
        )
        server._handlers = {"bt": Mock(return_value={"frames": []})}

        with self.assertRaisesRegex(ValueError, "Session is loading"):
            server._dispatch({"cmd": "bt"})

    def test_dispatch_returns_lightweight_status_while_loading(self):
        from gdb_cli.gdb_server.gdb_rpc_server import GDBRPCServer

        server = GDBRPCServer(
            sock_path=str(Path(self.temp_dir) / "sock"),
            session_meta={"session_id": "abc123", "mode": "core"},
        )

        result = server._dispatch({"cmd": "status"})

        self.assertEqual(result["state"], "loading")
        self.assertIn("elapsed", result)
        self.assertEqual(result["session_meta"]["session_id"], "abc123")

    def test_set_ready_allows_normal_dispatch(self):
        from gdb_cli.gdb_server.gdb_rpc_server import GDBRPCServer

        handler = Mock(return_value={"state": "ready"})
        server = GDBRPCServer(
            sock_path=str(Path(self.temp_dir) / "sock"),
            session_meta={"session_id": "abc123", "mode": "core"},
        )
        server._handlers = {"status": handler}

        server.set_ready()
        result = server._dispatch({"cmd": "status"})

        self.assertEqual(result["state"], "ready")
        handler.assert_called_once()

    def test_start_server_exports_global_for_followup_python_commands(self):
        import __main__
        from gdb_cli.gdb_server.gdb_rpc_server import start_server

        fake_server = Mock()

        with patch("gdb_cli.gdb_server.gdb_rpc_server.GDBRPCServer", return_value=fake_server):
            start_server("/tmp/test.sock", {"session_id": "abc123"}, 600)

        self.assertIs(__main__._gdb_rpc_server, fake_server)


if __name__ == "__main__":
    unittest.main()
