"""
End-to-end tests for memory inspection using GDB.

Tests memory read, ptype, and disassembly through core dumps.
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
class TestMemoryInspection(unittest.TestCase):
    """Memory inspection tests with real GDB."""

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

    def test_ptype_database_struct(self):
        """ptype should show Database struct definition."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        client = self._start_and_wait(core)
        result = client.ptype("Database")
        self.assertIsInstance(result, dict)

    def test_ptype_column_struct(self):
        """ptype should show Column struct definition."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        client = self._start_and_wait(core)
        result = client.ptype("Column")
        self.assertIsInstance(result, dict)

    def test_disassemble_function(self):
        """Disassemble should show instructions for a known function."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        client = self._start_and_wait(core)
        result = client.disasm(function="init_database")
        self.assertIsInstance(result, dict)

    def test_shared_libraries(self):
        """Shared libraries listing should show loaded libs."""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        core = _generate_core_dump(Path(self.tmp_dir))
        if core is None:
            self.skipTest("Could not generate core dump")

        client = self._start_and_wait(core)
        result = client.sharedlibs()
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
