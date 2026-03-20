"""Tests for session management module.

Tests session.py: Session 元数据管理
- Session 创建/查询/清理
- 幂等性：同 PID 重复 attach 返回已有 session
- 僵尸 session 清理

Based on Spec §4.2:
    SessionMeta:
        session_id: str          # UUID
        mode: str                # "core" | "attach"
        binary: Optional[str]
        core: Optional[str]
        pid: Optional[int]
        gdb_pid: int             # GDB 进程 PID
        sock_path: str           # Unix Socket 路径
        started_at: float
        last_active: float
        safety_level: str        # "readonly" | "readwrite" | "full"

    Functions:
        create_session(meta: SessionMeta)
        list_sessions() -> list[SessionMeta]
        get_session(session_id: str) -> Optional[SessionMeta]
        cleanup_dead_sessions()
        find_session_by_pid(pid: int) -> Optional[SessionMeta]
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

# Import will be available after developer implements session.py
# from gdb_cli.session import (
#     SessionMeta,
#     create_session,
#     list_sessions,
#     get_session,
#     cleanup_dead_sessions,
#     find_session_by_pid,
#     SESSION_DIR,
# )


class TestSessionMeta(unittest.TestCase):
    """Test SessionMeta data class."""

    def test_session_meta_creation(self):
        """Test SessionMeta can be created with all fields."""
        # Create SessionMeta with required fields
        # meta = SessionMeta(
        #     session_id="test-uuid",
        #     mode="core",
        #     binary="./my_program",
        #     core="./core.1234",
        #     gdb_pid=12345,
        #     sock_path="/home/user/.gdb-cli/sessions/test/gdb.sock",
        #     started_at=1234567890.0,
        #     last_active=1234567890.0,
        #     safety_level="readonly",
        # )
        pass  # Placeholder until implementation

    def test_session_meta_optional_fields(self):
        """Test SessionMeta with optional fields."""
        # pid is optional for core mode
        # binary is optional for attach mode
        pass  # Placeholder until implementation

    def test_session_meta_validation(self):
        """Test SessionMeta field validation."""
        # Invalid mode: "invalid"
        # Invalid safety_level: "invalid"
        # Expected: ValueError
        pass  # Placeholder until implementation

    def test_session_meta_to_dict(self):
        """Test SessionMeta serialization to dict."""
        # meta.to_dict() should return JSON-serializable dict
        pass  # Placeholder until implementation

    def test_session_meta_from_dict(self):
        """Test SessionMeta deserialization from dict."""
        # SessionMeta.from_dict({...}) should reconstruct object
        pass  # Placeholder until implementation

    def test_session_meta_is_alive(self):
        """Test SessionMeta.is_alive property."""
        # Check if gdb_pid process is still running
        pass  # Placeholder until implementation


class TestCreateSession(unittest.TestCase):
    """Test session creation."""

    @patch("pathlib.Path.mkdir")
    def test_create_session_creates_directory(self, mock_mkdir):
        """Test create_session creates session directory."""
        # Creates: ~/.gdb-cli/sessions/<session_id>/
        pass  # Placeholder until implementation

    @patch("builtins.open", mock_open())
    def test_create_session_writes_meta_json(self):
        """Test create_session writes meta.json."""
        # meta.json should contain serialized SessionMeta
        pass  # Placeholder until implementation

    def test_create_session_generates_uuid(self):
        """Test create_session generates unique session_id."""
        # Each call should generate unique UUID
        pass  # Placeholder until implementation

    def test_create_session_sets_timestamps(self):
        """Test create_session sets started_at and last_active."""
        # Both timestamps should be set to current time
        pass  # Placeholder until implementation

    def test_create_session_socket_path(self):
        """Test create_session creates socket path."""
        # sock_path = SESSION_DIR / session_id / "gdb.sock"
        pass  # Placeholder until implementation


class TestListSessions(unittest.TestCase):
    """Test listing active sessions."""

    def test_list_sessions_empty(self):
        """Test listing sessions when none exist."""
        # No session directories
        # Expected: []
        pass  # Placeholder until implementation

    @patch("pathlib.Path.iterdir")
    @patch("gdb_cli.session.get_session")
    def test_list_sessions_returns_active(self, mock_get, mock_iterdir):
        """Test list_sessions returns active sessions."""
        # Multiple session directories
        # Filter out dead sessions
        pass  # Placeholder until implementation

    @patch("pathlib.Path.iterdir")
    def test_list_sessions_skips_invalid(self, mock_iterdir):
        """Test list_sessions skips invalid session directories."""
        # Directory without meta.json
        # Expected: skipped silently
        pass  # Placeholder until implementation

    def test_list_sessions_sorting(self):
        """Test list_sessions sort order."""
        # By default: most recently active first
        pass  # Placeholder until implementation


class TestGetSession(unittest.TestCase):
    """Test retrieving specific session."""

    @patch("builtins.open", mock_open(read_data='{"session_id": "test"}'))
    def test_get_session_exists(self):
        """Test get_session returns SessionMeta for existing session."""
        # Valid session_id -> SessionMeta
        pass  # Placeholder until implementation

    def test_get_session_not_exists(self):
        """Test get_session returns None for non-existent session."""
        # Invalid session_id -> None
        pass  # Placeholder until implementation

    @patch("builtins.open", mock_open(read_data="invalid json"))
    def test_get_session_corrupted_meta(self):
        """Test get_session handles corrupted meta.json."""
        # Corrupted JSON -> None or error
        pass  # Placeholder until implementation

    def test_get_session_checks_gdb_alive(self):
        """Test get_session verifies GDB process is alive."""
        # Check gdb_pid is running
        # If dead, return None or mark as dead
        pass  # Placeholder until implementation


class TestCleanupDeadSessions(unittest.TestCase):
    """Test zombie session cleanup."""

    @patch("gdb_cli.session.list_sessions")
    @patch("gdb_cli.session._is_session_alive")
    def test_cleanup_removes_dead_sessions(self, mock_alive, mock_list):
        """Test cleanup removes sessions with dead GDB processes."""
        # mock_list returns sessions
        # mock_alive returns False for some
        # Expected: dead session directories removed
        pass  # Placeholder until implementation

    @patch("pathlib.Path.unlink")
    @patch("shutil.rmtree")
    def test_cleanup_removes_files(self, mock_rmtree, mock_unlink):
        """Test cleanup removes socket files and directories."""
        # Removes: gdb.sock, meta.json, session directory
        pass  # Placeholder until implementation

    def test_cleanup_preserves_active_sessions(self):
        """Test cleanup preserves sessions with alive GDB."""
        # Active sessions should not be touched
        pass  # Placeholder until implementation

    def test_cleanup_handles_missing_files(self):
        """Test cleanup handles already-deleted files gracefully."""
        # FileNotFoundError during cleanup should be ignored
        pass  # Placeholder until implementation


class TestFindSessionByPid(unittest.TestCase):
    """Test finding session by attached PID."""

    def test_find_session_by_pid_exists(self):
        """Test find_session_by_pid returns session for attached PID."""
        # Spec §2.7: 幂等性保证
        # Session with matching pid exists
        # Expected: SessionMeta
        pass  # Placeholder until implementation

    def test_find_session_by_pid_not_exists(self):
        """Test find_session_by_pid returns None when no match."""
        # No session with given pid
        # Expected: None
        pass  # Placeholder until implementation

    def test_find_session_by_pid_core_mode(self):
        """Test find_session_by_pid ignores core mode sessions."""
        # Core mode sessions have no pid
        # Should not match
        pass  # Placeholder until implementation

    def test_find_session_by_pid_checks_alive(self):
        """Test find_session_by_pid only returns alive sessions."""
        # Matching pid but GDB dead
        # Expected: None (session cleaned up or filtered)
        pass  # Placeholder until implementation


class TestIdempotency(unittest.TestCase):
    """Test session creation idempotency."""

    @patch("gdb_cli.session.find_session_by_pid")
    @patch("gdb_cli.session.create_session")
    def test_attach_same_pid_returns_existing(self, mock_create, mock_find):
        """Test attach to same PID returns existing session."""
        # Spec §2.7: 同一 PID 同时只允许一个 session
        # First call creates session
        # Second call with same PID returns existing
        # Expected: Same session_id, create_session not called twice
        pass  # Placeholder until implementation

    @patch("gdb_cli.session.find_session_by_pid")
    def test_attach_different_pid_creates_new(self, mock_find):
        """Test attach to different PID creates new session."""
        # Different PID -> new session
        pass  # Placeholder until implementation

    def test_attach_reuses_socket(self):
        """Test re-attach reuses existing socket."""
        # Same session -> same sock_path
        pass  # Placeholder until implementation


class TestSessionPersistence(unittest.TestCase):
    """Test session metadata persistence."""

    def test_meta_json_format(self):
        """Test meta.json file format."""
        # Should be valid JSON
        # Should contain all SessionMeta fields
        pass  # Placeholder until implementation

    def test_meta_json_roundtrip(self):
        """Test SessionMeta survives save/load roundtrip."""
        # Create -> save -> load -> compare
        pass  # Placeholder until implementation

    def test_update_last_active(self):
        """Test updating last_active timestamp."""
        # After each command, last_active should update
        pass  # Placeholder until implementation


class TestSessionEdgeCases(unittest.TestCase):
    """Edge case tests for session management."""

    def test_session_dir_permission_denied(self):
        """Test handling of permission denied on SESSION_DIR."""
        # Cannot create/write to session directory
        # Expected: clear error with path info
        pass  # Placeholder until implementation

    def test_session_dir_full_disk(self):
        """Test handling of disk full error."""
        # Write to meta.json fails due to disk full
        pass  # Placeholder until implementation

    def test_concurrent_session_creation(self):
        """Test concurrent session creation safety."""
        # Race condition: two threads creating sessions
        # Expected: Each gets unique session_id
        pass  # Placeholder until implementation

    def test_very_long_session_id(self):
        """Test handling of very long session_id."""
        # UUID should be fixed length, but test edge case
        pass  # Placeholder until implementation

    def test_session_with_special_chars_in_path(self):
        """Test session with special characters in binary/core path."""
        # Paths with spaces, unicode, special chars
        # Expected: Properly escaped in JSON
        pass  # Placeholder until implementation


if __name__ == "__main__":
    unittest.main()
