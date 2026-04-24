# GDB CLI for AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

English | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | [Русский](README.ru.md) | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Italiano](README.it.md)

A GDB debugging tool designed for AI Agents (Claude Code, etc.). Uses a "thin client CLI + GDB built-in Python RPC Server" architecture, enabling stateful GDB debugging through Bash.

## Features

- **Core Dump Analysis**: Load core dumps with symbols resident in memory for millisecond-level response
- **Live Attach Debugging**: Attach to running processes with non-stop mode support
- **Structured JSON Output**: All commands output JSON with automatic truncation/pagination and operation hints
- **Security Mechanisms**: Command whitelist, heartbeat timeout auto-cleanup, idempotency guarantees
- **Database-Optimized**: scheduler-locking, large object pagination, multi-thread truncation

## Requirements

- **Python**: 3.6.8+
- **GDB**: 9.0+ with **Python support enabled**
- **OS**: Linux

### Check GDB Python Support

```bash
# Check if GDB has Python support
gdb -nx -q -batch -ex "python print('OK')"

# If system GDB lacks Python, check GCC Toolset (RHEL/CentOS)
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Installation

```bash
# Install from PyPI
pip install gdb-cli

# Or install from GitHub
pip install git+https://github.com/Cerdore/gdb-cli.git

# Or clone and install locally
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# Environment check
gdb-cli env-check
```

## Quick Start

### 1. Load Core Dump

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Output:
```json
{
  "session_id": "f465d650",
  "mode": "core",
  "binary": "./my_program",
  "core": "./core.12345",
  "gdb_pid": 12345,
  "status": "loading"
}
```

When loading a large binary or core file, poll until the session becomes ready:

```bash
gdb-cli status -s f465d650
```

```json
{
  "session_id": "f465d650",
  "state": "ready",
  "mode": "core",
  "binary": "./my_program"
}
```

> If your system's default GDB doesn't have Python support, specify it with `--gdb-path`:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Debugging Operations

All operations use `--session` / `-s` to specify the session ID:

```bash
SESSION="f465d650"

# List threads
gdb-cli threads -s $SESSION

# Get backtrace (default: current thread)
gdb-cli bt -s $SESSION

# Get backtrace for a specific thread
gdb-cli bt -s $SESSION --thread 3

# Evaluate C/C++ expressions
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Access array elements
gdb-cli eval-element -s $SESSION "my_array" --index 5

# View local variables
gdb-cli locals-cmd -s $SESSION

# Execute raw GDB commands
gdb-cli exec -s $SESSION "info registers"

# Check session status
gdb-cli status -s $SESSION
```

### 3. Session Management

```bash
# List all active sessions
gdb-cli sessions

# Stop a session
gdb-cli stop -s $SESSION
```

### 4. Live Attach Debugging

```bash
# Attach to a running process (default: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Attach with symbol file
gdb-cli attach --pid 9876 --binary ./my_program

# Allow memory modification and function calls
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Full Command Reference

### load — Load Core Dump

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      Executable file path (required)
  --core, -c        Core dump file path (required)
  --sysroot         sysroot path (for cross-machine debugging)
  --solib-prefix    Shared library prefix
  --source-dir      Source code directory
  --timeout         Heartbeat timeout in seconds (default: 600)
  --gdb-path        GDB executable path (default: "gdb")
```

`load` returns immediately with `"status": "loading"` after the RPC server becomes reachable. Use `gdb-cli status -s <session>` and wait for `"state": "ready"` before heavy inspection commands.

### attach — Attach to Process

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               Process PID (required)
  --binary                Executable file path (optional)
  --scheduler-locking     Enable scheduler-locking (default: true)
  --non-stop              Enable non-stop mode (default: true)
  --timeout               Heartbeat timeout in seconds (default: 600)
  --allow-write           Allow memory modification
  --allow-call            Allow function calls
```

### threads — List Threads

```
gdb-cli threads -s <session> [options]

  --range           Thread range, e.g., "3-10"
  --limit           Maximum return count (default: 20)
  --filter-state    Filter by state ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      Specify thread ID
  --limit           Maximum frame count (default: 30)
  --full            Include local variables
  --range           Frame range, e.g., "5-15"
```

### eval-cmd — Evaluate Expression

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Recursion depth limit (default: 3)
  --max-elements    Array element limit (default: 50)
```

### eval-element — Access Array/Container Elements

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Execute Raw GDB Command

```
gdb-cli exec -s <session> <command>

  --safety-level    Safety level (readonly / readwrite / full)
```

### thread-apply — Batch Thread Operations

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Output Examples

### threads

```json
{
  "threads": [
    {"id": 1, "global_id": 1, "state": "stopped"},
    {"id": 2, "global_id": 2, "state": "stopped"}
  ],
  "total_count": 5,
  "truncated": true,
  "current_thread": {"id": 1, "global_id": 1, "state": "stopped"},
  "hint": "use 'threads --range START-END' for specific threads"
}
```

### eval-cmd

```json
{
  "expression": "(int)5+3",
  "value": 8,
  "type": "int",
  "size": 4
}
```

### bt

```json
{
  "frames": [
    {"number": 0, "function": "crash_thread", "address": "0x400a1c", "file": "test.c", "line": 42},
    {"number": 1, "function": "start_thread", "address": "0x7f3fa2e13fa"}
  ],
  "total_count": 2,
  "truncated": false
}
```

## Security Mechanisms

### Command Whitelist (Attach Mode)

| Safety Level | Allowed Commands |
|--------------|------------------|
| `readonly` (default) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` are always blocked.

### Heartbeat Timeout

Automatically detaches and quits after 10 minutes of inactivity by default. Configurable via `--timeout`.

### Idempotency

Only one session per PID / Core file is allowed. Repeated load/attach returns the existing session_id.

## Cross-Machine Core Dump Debugging

When analyzing core dumps from other machines, shared library paths may differ:

```bash
# Set sysroot (path prefix replacement)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Set source directory (for source-level debugging)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Development

### Project Structure

```
src/gdb_cli/
├── cli.py              # CLI entry point (Click)
├── client.py           # Unix Socket client
├── launcher.py         # GDB process launcher
├── session.py          # Session metadata management
├── safety.py           # Command whitelist filter
├── formatters.py       # JSON output formatting
├── env_check.py        # Environment check
├── errors.py           # Error classification
└── gdb_server/
    ├── gdb_rpc_server.py   # RPC Server core
    ├── handlers.py         # Command handlers
    ├── value_formatter.py  # gdb.Value serialization
    └── heartbeat.py         # Heartbeat timeout management

skills/
└── gdb-cli/               # Claude Code skill for intelligent debugging
    ├── SKILL.md            # Skill definition
    └── evals/              # Test cases for skill evaluation
```

### Run Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### End-to-End Testing

Requires GDB with Python support. Use the crash test program in `tests/crash_test/`:

```bash
# Compile test program
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Generate coredump
ulimit -c unlimited
./crash_test  # Will SIGSEGV

# Find core file
ls /path/to/core_dumps/core-crash_test-*

# Run E2E test
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Known Limitations

- No `target remote` support (use SSH for remote debugging, see below)
- No multi-inferior debugging support
- GDB 12.x Guile pretty printers are not thread-safe, workaround via `format_string(raw=True)`
- GDB embedded Python version may be older (e.g., 3.6.8), code has compatibility handling

## Remote Debugging via SSH

Install and run on remote machine in one command:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

Or install first, then debug:

```bash
# Install on remote
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Run debugging
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Claude Code Skills

This project includes a **gdb-cli skill** for Claude Code that provides intelligent debugging assistance by combining source code analysis with runtime state inspection.

### Install the Skill

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Usage in Claude Code

```
/gdb-cli

# Or describe your debugging need:
I have a core dump at ./core.1234 and binary at ./myapp. Help me debug it.
```

### Features

- **Source Code Correlation**: Automatically reads source files around crash points
- **Deadlock Detection**: Identifies circular wait patterns in multi-threaded programs
- **Safety Warnings**: Alerts about production environment risks when attaching to live processes
- **Structured Reports**: Generates analysis with root cause hypotheses and next steps

See [skills/README.md](skills/README.md) for more details.

## License

Apache License 2.0
