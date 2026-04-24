"""
Test helpers for GDB-CLI tests.
"""

import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

# Default socket path for test sessions
TEST_SOCK_DIR = Path(tempfile.mkdtemp(prefix="gdbcli_test_"))


def compile_test_binary(source_path: Path, output_path: Path) -> bool:
    """Compile a C test binary with debug symbols.

    Args:
        source_path: Path to .c source file
        output_path: Path for compiled binary

    Returns:
        True on success, False on failure
    """
    try:
        result = subprocess.run(
            ["gcc", "-g", "-O0", "-o", str(output_path), str(source_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def wait_for_session_ready(client, timeout: float = 60.0) -> bool:
    """Poll status until GDB session is ready.

    Args:
        client: Connected GDBClient
        timeout: Maximum wait time in seconds

    Returns:
        True if session is ready, False on timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = client.status()
            if result.get("state") == "ready":
                return True
            if result.get("state") == "error":
                return False
        except Exception:
            pass
        time.sleep(0.5)
    return False


def stop_session_safe(session_id: str) -> None:
    """Stop a GDB session and clean up, ignoring errors."""
    from gdb_cli.session import cleanup_session
    try:
        cleanup_session(session_id)
    except Exception:
        pass


def send_signal_to_pid(pid: int, sig: int = signal.SIGTERM) -> bool:
    """Send a signal to a process."""
    try:
        os.kill(pid, sig)
        return True
    except OSError:
        return False
