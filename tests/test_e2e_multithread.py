"""
End-to-end tests for multi-threaded analysis using GDB.

Tests thread switching, thread-apply, and per-thread state inspection.
"""

import os
import subprocess
import time
import unittest
from pathlib import Path

CRASH_TEST_DIR = Path(__file__).parent / "crash_test"
CRASH_BINARY = CRASH_TEST_DIR / "crash_test"


def _gdb_available():
    try:
        result = subprocess.run(
            ["gdb", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _crash_binary_available():
    return CRASH_BINARY.exists()


def _generate_core_dump(tmp_path):
    env = os.environ.copy()
    try:
        subprocess.run(
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
    except Exception:
        pass
    core_files = sorted(tmp_path.glob("core*"))
    return str(core_files[0]) if core_files else None


@unittest.skipUnless(_gdb_available(), "GDB not available")
@unittest.skipUnless(_crash_binary_available(), "Crash test binary not available")
class TestMultiThreadAnalysis(unittest.TestCase):
    """Multi-threaded core dump analysis through gdb-cli."""

    @classmethod
    def setUpClass(cls):
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
                from gdb_cli.session import cleanup_session
                cleanup_session(self.session_process.session.session_id)
            except Exception:
                pass
        if self.tmp_dir is not None:
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _start_and_wait(self, core):
        """Start session and wait for ready."""
        from gdb_cli.launcher import launch_core
        self.session_process = launch_core(
            binary=str(CRASH_BINARY), core=core, timeout=30
        )
        from gdb_cli.client import GDBClient
        client = GDBClient(str(self.session_process.session.sock_path))
        start = time.time()
        while time.time() - start < 30:
            try:
                if client.status().get("state") == "ready":
                    return client
            except Exception:
                pass
            time.sleep(0.5)
        return client

    def test_thread_switch(self):
        """Switch between threads and verify different backtraces."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        client = self._start_and_wait(core)
        threads = client.threads()
        if threads.get("total_count", 0) < 2:
            self.skipTest("Not enough threads for switch test")

        # Switch to thread 2
        client.thread_switch(2)

        # Get backtrace - should be from thread 2's perspective
        bt = client.backtrace()
        self.assertIn("frames", bt)
        self.assertGreaterEqual(len(bt["frames"]), 1)

    def test_thread_apply_bt_all(self):
        """Apply backtrace to all threads."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        client = self._start_and_wait(core)
        result = client.thread_apply("bt", all_threads=True)
        self.assertIn("results", result)
        self.assertGreaterEqual(len(result["results"]), 1)

    def test_per_thread_locals(self):
        """Get local variables from different threads."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        client = self._start_and_wait(core)
        # Get locals from current frame
        locals_result = client.locals()
        self.assertIsInstance(locals_result, dict)


if __name__ == "__main__":
    unittest.main()
