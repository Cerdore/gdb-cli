"""
pytest fixtures for GDB-CLI E2E tests.
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def gdb_available():
    """Check if GDB is available on the system."""
    try:
        result = subprocess.run(
            ["gdb", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def crash_test_binary():
    """Build and return the path to the crash test binary."""
    crash_dir = Path(__file__).parent / "crash_test"
    binary = crash_dir / "crash_test"

    if not binary.exists():
        result = subprocess.run(
            ["make", "-C", str(crash_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"Failed to build crash_test: {result.stderr}")

    return binary


@pytest.fixture()
def core_file(crash_test_binary, tmp_path):
    """Generate a core dump from the crash test binary.

    Returns the path to the core file, or None if core generation fails
    (e.g., on macOS where core dumps are handled differently).
    """
    core_pattern = tmp_path / "core"

    # Try to generate a core dump
    env = os.environ.copy()
    # On Linux, set core pattern via /proc
    try:
        with open("/proc/sys/kernel/core_pattern", "w") as f:
            f.write(str(core_pattern) + "\n")
    except (FileNotFoundError, PermissionError):
        pass

    try:
        result = subprocess.run(
            [str(crash_test_binary), "1"],
            env={**env, "ULIMIT_CORE": "unlimited"},
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=10,
            preexec_fn=lambda: (
                __import__("resource").setrlimit(
                    __import__("resource").RLIMIT_CORE,
                    (__import__("resource").RLIM_INFINITY,
                     __import__("resource").RLIM_INFINITY),
                )
            ),
        )
    except (subprocess.TimeoutExpired, Exception):
        pass

    # Find core file in tmp_path
    core_files = list(tmp_path.glob("core*"))
    if core_files:
        return core_files[0]

    # On macOS, core dumps go to /cores/
    core_files = list(Path("/cores").glob("core.*"))
    if core_files:
        return core_files[0]

    return None


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "needs_gdb: test requires GDB")
    config.addinivalue_line("markers", "e2e: end-to-end test")
