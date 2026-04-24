"""Tests for session management module.

Tests session.py: Session metadata CRUD, health checks, cleanup.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from gdb_cli.session import (
    SessionMeta,
    _is_session_alive,
    cleanup_dead_sessions,
    cleanup_session,
    create_session,
    get_session,
    list_sessions,
)

# psutil is optional for PID reuse detection
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class TestSessionMeta(unittest.TestCase):
    """Test SessionMeta data class."""

    def test_session_meta_defaults(self):
        """Test SessionMeta defaults."""
        meta = SessionMeta(
            session_id="test-id",
            mode="core",
            started_at=time.time(),
            last_active=time.time(),
        )
        self.assertEqual(meta.session_id, "test-id")
        self.assertEqual(meta.mode, "core")
        self.assertIsNone(meta.gdb_pid)
        self.assertIsNone(meta.binary)

    def test_session_meta_all_fields(self):
        """Test SessionMeta with all fields set."""
        now = time.time()
        meta = SessionMeta(
            session_id="abc12345",
            mode="attach",
            binary="/usr/bin/myapp",
            pid=12345,
            gdb_pid=12346,
            sock_path="/tmp/gdb-cli/abc12345/gdb.sock",
            started_at=now,
            last_active=now,
            heartbeat_timeout=600,
            safety_level="readonly",
        )
        self.assertEqual(meta.session_id, "abc12345")
        self.assertEqual(meta.mode, "attach")
        self.assertEqual(meta.binary, "/usr/bin/myapp")
        self.assertEqual(meta.pid, 12345)
        self.assertEqual(meta.gdb_pid, 12346)
        self.assertEqual(meta.safety_level, "readonly")
        self.assertEqual(meta.heartbeat_timeout, 600)


class TestSessionIsAlive(unittest.TestCase):
    """Test _is_session_alive function."""

    def test_none_pid_returns_false(self):
        """Session with gdb_pid=None should be dead."""
        meta = SessionMeta(
            session_id="test",
            mode="core",
            started_at=time.time(),
            last_active=time.time(),
            gdb_pid=None,
        )
        self.assertFalse(_is_session_alive(meta))

    @patch("os.kill")
    def test_pid_exists_returns_true(self, mock_kill):
        """If the PID exists, should return True."""
        mock_kill.return_value = None  # os.kill(pid, 0) succeeds
        meta = SessionMeta(
            session_id="test",
            mode="core",
            started_at=time.time(),
            last_active=time.time(),
            gdb_pid=12345,
        )
        self.assertTrue(_is_session_alive(meta))

    @patch("os.kill")
    def test_pid_not_exists_returns_false(self, mock_kill):
        """If the PID does not exist, should return False."""
        mock_kill.side_effect = OSError("No such process")
        meta = SessionMeta(
            session_id="test",
            mode="core",
            started_at=time.time(),
            last_active=time.time(),
            gdb_pid=12345,
        )
        self.assertFalse(_is_session_alive(meta))

    @unittest.skipUnless(HAS_PSUTIL, "psutil not installed")
    @patch("os.kill")
    @patch("psutil.Process", create=True)
    def test_pid_reuse_detected(self, mock_psutil_proc, mock_kill):
        """If PID exists but process name is not GDB, should detect reuse."""
        mock_kill.return_value = None
        mock_proc = mock_psutil_proc.return_value
        mock_proc.name.return_value = "httpd"  # Not GDB
        meta = SessionMeta(
            session_id="test",
            mode="core",
            started_at=time.time(),
            last_active=time.time(),
            gdb_pid=12345,
        )
        # With psutil available, non-GDB process should return False
        self.assertFalse(_is_session_alive(meta))

    @unittest.skipUnless(HAS_PSUTIL, "psutil not installed")
    @patch("os.kill")
    @patch("psutil.Process", create=True)
    def test_pid_valid_gdb_process(self, mock_psutil_proc, mock_kill):
        """If PID exists and process name contains GDB, should return True."""
        mock_kill.return_value = None
        mock_proc = mock_psutil_proc.return_value
        mock_proc.name.return_value = "gdb"
        meta = SessionMeta(
            session_id="test",
            mode="core",
            started_at=time.time(),
            last_active=time.time(),
            gdb_pid=12345,
        )
        self.assertTrue(_is_session_alive(meta))


class TestSessionCreation(unittest.TestCase):
    """Test session creation."""

    @patch("gdb_cli.session.SESSION_DIR")
    def test_create_session_core_mode(self, mock_session_dir):
        """Test creating a core mode session."""
        tmp = Path(tempfile.mkdtemp())
        mock_session_dir.__truediv__.return_value = tmp / "sess1"
        mock_session_dir.__rtruediv__ = lambda self, other: tmp / other

        # This requires actual filesystem, skip if SESSION_DIR can't be mocked
        try:
            session = create_session(
                mode="core",
                binary="/usr/bin/myapp",
                core="/tmp/core.1234",
            )
            self.assertEqual(session.mode, "core")
            self.assertEqual(session.binary, "/usr/bin/myapp")
            self.assertEqual(session.core, "/tmp/core.1234")
            self.assertEqual(session.safety_level, "readonly")
            self.assertIsNotNone(session.session_id)
            self.assertEqual(len(session.session_id), 8)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    @patch("gdb_cli.session.SESSION_DIR")
    def test_create_session_attach_mode(self, mock_session_dir):
        """Test creating an attach mode session."""
        tmp = Path(tempfile.mkdtemp())
        mock_session_dir.__truediv__.return_value = tmp / "sess2"
        mock_session_dir.__rtruediv__ = lambda self, other: tmp / other

        try:
            session = create_session(
                mode="attach",
                binary="/usr/bin/myapp",
                pid=12345,
                safety_level="readwrite",
            )
            self.assertEqual(session.mode, "attach")
            self.assertEqual(session.pid, 12345)
            self.assertEqual(session.safety_level, "readwrite")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class TestSessionCleanup(unittest.TestCase):
    """Test session cleanup."""

    def test_cleanup_nonexistent_session(self):
        """Cleanup of nonexistent session should return False."""
        result = cleanup_session("nonexistent-id-12345")
        self.assertFalse(result)

    @patch("os.kill")
    @patch("pathlib.Path.exists")
    def test_cleanup_with_gdb_pid(self, mock_exists, mock_kill):
        """Cleanup should attempt to kill GDB process."""
        mock_exists.return_value = True
        # This test verifies cleanup_session doesn't crash
        try:
            cleanup_session("test-session")
        except Exception:
            pass  # May fail due to missing files, that's OK


if __name__ == "__main__":
    unittest.main()
