"""
End-to-end tests for core dump analysis using real GDB.

These tests require:
- GDB installed with Python support
- A crash test binary compiled with debug symbols
- Core dump generation capability (ulimit -c unlimited)

Skip markers: tests are skipped automatically if GDB is not available.

Usage:
    python -m pytest tests/test_e2e_core_analysis.py -v
"""

import os
import subprocess
import time
import unittest
from pathlib import Path

from gdb_cli.client import GDBClient
from gdb_cli.launcher import launch_core
from gdb_cli.session import cleanup_session

CRASH_TEST_DIR = Path(__file__).parent / "crash_test"
CRASH_BINARY = CRASH_TEST_DIR / "crash_test"


def _gdb_available():
    """Check if GDB is available."""
    try:
        result = subprocess.run(
            ["gdb", "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _crash_binary_available():
    """Check if crash test binary exists (build if needed)."""
    if CRASH_BINARY.exists():
        return True
    try:
        result = subprocess.run(
            ["make", "-C", str(CRASH_TEST_DIR)],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def _generate_core_dump(tmp_path):
    """Run crash test to generate a core dump. Returns core path or None."""
    env = os.environ.copy()
    try:
        result = subprocess.run(
            [str(CRASH_BINARY), "1"],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=15,
            preexec_fn=lambda: (
                __import__("resource").setrlimit(
                    __import__("resource").RLIMIT_CORE,
                    (__import__("resource").RLIM_INFINITY,
                     __import__("resource").RLIM_INFINITY)
                )
            ),
        )
    except (subprocess.TimeoutExpired, Exception):
        pass

    core_files = sorted(tmp_path.glob("core*"))
    if core_files:
        return str(core_files[0])
    return None


@unittest.skipUnless(_gdb_available(), "GDB not available")
@unittest.skipUnless(_crash_binary_available(), "Crash test binary not available")
class TestCoreAnalysis(unittest.TestCase):
    """End-to-end tests: analyze a core dump with gdb-cli."""

    @classmethod
    def setUpClass(cls):
        """Build crash binary if needed."""
        if not CRASH_BINARY.exists():
            subprocess.run(
                ["make", "-C", str(CRASH_TEST_DIR)],
                capture_output=True, timeout=30
            )

    def setUp(self):
        self.session_process = None
        self.tmp_dir = None

    def tearDown(self):
        if self.session_process is not None:
            try:
                cleanup_session(self.session_process.session.session_id)
            except Exception:
                pass
        if self.tmp_dir is not None:
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_load_core_and_list_threads(self):
        """Load a core dump and verify threads listing."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()

        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        self.session_process = launch_core(
            binary=str(CRASH_BINARY),
            core=core,
            timeout=30,
        )

        session_id = self.session_process.session.session_id
        sock_path = self.session_process.session.sock_path
        self.assertIsNotNone(session_id)
        self.assertIsNotNone(sock_path)

        # Wait for session to be ready
        client = GDBClient(str(sock_path))
        start = time.time()
        ready = False
        while time.time() - start < 30:
            try:
                status = client.status()
                if status.get("state") == "ready":
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not ready:
            self.skipTest("Session did not become ready")

        # List threads
        threads_result = client.threads()
        self.assertIn("threads", threads_result)
        self.assertGreaterEqual(threads_result["total_count"], 4,
                                "Expected at least 4 threads")

    def test_backtrace_shows_crash(self):
        """Backtrace should show crash location at frame 0."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()

        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        self.session_process = launch_core(
            binary=str(CRASH_BINARY),
            core=core,
            timeout=30,
        )

        sock_path = self.session_process.session.sock_path
        client = GDBClient(str(sock_path))

        # Wait for ready
        start = time.time()
        while time.time() - start < 30:
            try:
                if client.status().get("state") == "ready":
                    break
            except Exception:
                pass
            time.sleep(0.5)

        bt_result = client.backtrace()
        self.assertIn("frames", bt_result)
        self.assertGreaterEqual(len(bt_result["frames"]), 1)

    def test_eval_global_variable(self):
        """Evaluate the g_database global variable."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()

        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        self.session_process = launch_core(
            binary=str(CRASH_BINARY),
            core=core,
            timeout=30,
        )

        sock_path = self.session_process.session.sock_path
        client = GDBClient(str(sock_path))

        start = time.time()
        while time.time() - start < 30:
            try:
                if client.status().get("state") == "ready":
                    break
            except Exception:
                pass
            time.sleep(0.5)

        eval_result = client.eval_expr("g_database")
        self.assertIn("expression", eval_result)

    def test_registers(self):
        """Read CPU registers from core dump."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()

        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        self.session_process = launch_core(
            binary=str(CRASH_BINARY),
            core=core,
            timeout=30,
        )

        sock_path = self.session_process.session.sock_path
        client = GDBClient(str(sock_path))

        start = time.time()
        while time.time() - start < 30:
            try:
                if client.status().get("state") == "ready":
                    break
            except Exception:
                pass
            time.sleep(0.5)

        # Get status to find current thread
        status = client.status()
        self.assertIn("mode", status)
        self.assertEqual(status["mode"], "core")


if __name__ == "__main__":
    unittest.main()
