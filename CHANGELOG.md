# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-04-25

### Security
- Fix RCE via `exec` command: `python` command now blocked, `SafetyFilter` integrated at runtime
- Fix RCE via `thread-apply`: zero safety filtering now enforced with `SafetyFilter.check_command()`
- Fix privilege escalation: server now enforces session-configured `safety_level`, ignores client override

### Added
- Signal handlers (SIGTERM/SIGINT) for clean GDB child process cleanup
- PID reuse detection via `psutil.Process(name)` cross-verification

### Changed
- All handler calls now routed through `gdb.post_event()` for thread safety
- `_wait_for_socket` now checks GDB process health during polling

### Fixed
- FIFO/file descriptor leak in launcher exception paths
- Heartbeat timeout now cleans up socket file before `os._exit()`
- `SafetyFilter` path resolution in `handlers.py` (was pointing to wrong directory)

### Tests
- Rewrote `test_safety.py` (32 tests), `test_handlers.py` (20 tests), `test_session.py` (10 tests), `test_client.py` (11 tests) — previously all `pass` stubs
- Added E2E test suite: `test_e2e_core_analysis.py`, `test_e2e_multithread.py`, `test_e2e_memory.py` (11 tests, skipped when GDB unavailable)
- Added test infrastructure: `conftest.py` with pytest fixtures, `helpers.py` with test utilities

## [0.2.0] - 2026-04-25

### Added
- Multilanguage support (i18n): en, zh-CN, ru — auto-detected from `GDB_CLI_LANG` / `LANG` / `LC_ALL` (#1)
- `target` command: SSH remote debugging via `gdb-cli target --remote HOST:PID`
- `status` now shows elapsed time since session start
- `env-check --gdb-path` option for specifying GDB executable
- Python 3.6.8+ compatibility restored
- `thread-switch` command for switching current thread
- `up`/`down` commands for stack frame navigation
- `sharedlibs` command for viewing loaded shared libraries
- `disasm` command for disassembly

### Changed
- All user-facing error messages now translated via i18n catalog
- License: MIT → Apache 2.0
- Skill renamed to `gdb-cli` for consistency with bunx ecosystem

### Fixed
- Handler thread safety: replaced `gdb.execute()` with Python API
- Commands now execute on Python main thread to avoid GDB concurrency issues
- `sessions` shows GDB process PID instead of target PID in attach mode
- Various lint and CI fixes

### Docs
- DB Core Debugging Skill documentation
- E2E Testing strategy document

## [0.1.0] - 2025-03-21

### Added
- Initial release
- Core dump analysis with symbol resident in memory
- Live attach debugging with non-stop mode support
- Structured JSON output for all commands
- Command whitelist security mechanism
- Heartbeat timeout auto-cleanup
- Session management with idempotency
- SSH remote debugging support
- Multi-language documentation (English, Chinese)

### Commands
- `load` - Load core dump files
- `attach` - Attach to running processes
- `threads` - List threads
- `bt` - Get backtrace
- `eval-cmd` - Evaluate C/C++ expressions
- `eval-element` - Access array/container elements
- `exec` - Execute raw GDB commands
- `thread-apply` - Batch thread operations
- `locals-cmd` - View local variables
- `status` - Check session status
- `sessions` - List active sessions
- `stop` - Stop a session
- `env-check` - Environment validation