# Session 元数据修复 & env-check --gdb-path 支持

> Date: 2026-03-24
> Status: Draft
> Scope: 3 个独立修复，涉及 launcher.py, cli.py, env_check.py

## 1. 背景

在远程机器上使用 gdb-cli 时发现三个问题：

1. `gdb-cli status -s <id>` 返回 `"binary": null`，但 session 实际加载了 binary
2. `gdb-cli sessions` 在 core 模式下 `"pid": null`，缺少有意义的进程信息
3. 同一台机器上可能存在多个 GDB（有的支持 Python，有的不支持），`env-check` 无法指定检查哪个 GDB

## 2. 问题分析

### 2.1 status 返回 binary: null

**根因**：`launcher.py:249` 的 `start_server()` 调用中，session_meta 参数只传了精简 dict：

```python
# launcher.py line 249 (当前代码)
f"python start_server('{session.sock_path}', "
f"{json.dumps({'session_id': session.session_id, 'mode': session.mode})}, "
f"{session.heartbeat_timeout})"
```

虽然第 243 行通过环境变量 `GDB_CLI_SESSION_META` 设置了完整 meta（包含 binary/core/pid），但 `start_server()` 的第二个参数直接用了精简 dict，覆盖了完整数据。

`handle_status()` 从 `_session_meta.get("binary")` 读取时，精简 dict 中没有 `binary` 键，返回 `None`。

**影响**：所有 session 的 `status` 命令都会返回 `binary: null`。

### 2.2 sessions 输出 pid: null (core 模式)

**现状**：`SessionMeta.pid` 语义是"目标进程 PID"，仅在 attach 模式下有值。Core 模式无活进程，`pid` 始终为 `None`。

**期望**：用户希望看到 GDB 进程的 PID（`SessionMeta.gdb_pid`），用于判断 GDB 是否存活、方便 kill 等操作。

### 2.3 env-check 不支持 --gdb-path

**现状**：`env-check` 通过 `shutil.which("gdb")` 查找 PATH 中的第一个 gdb，无法指定检查特定路径的 GDB。

**场景**：机器上存在多个 GDB 安装（如 `/usr/bin/gdb` 不支持 Python，`/usr/libexec/gdb` 支持），用户需要验证特定 GDB 是否可用。

## 3. 修复方案

### 3.1 Fix: status binary null

**文件**: `src/gdb_cli/launcher.py`

将 `_build_server_commands()` 第 249 行的 `start_server()` 调用改为从环境变量读取完整 meta，而非内联构造精简 dict：

```python
# Before (line 249):
f"python start_server('{sock}', {{...精简dict...}}, {timeout})"

# After:
f"python import json as _json; start_server('{sock}', "
f"_json.loads(os.environ['GDB_CLI_SESSION_META']), {timeout})"
```

这样 `handle_status()` 能读到完整的 `binary`、`core`、`pid` 等字段。

### 3.2 Fix: sessions 显示 gdb_pid

**文件**: `src/gdb_cli/cli.py`

`sessions` 命令输出中，将 `pid` 字段的值从 `s.pid`（目标进程 PID）改为 `s.gdb_pid`（GDB 进程 PID）：

```python
# Before (cli.py sessions command):
"pid": s.pid,

# After:
"pid": s.gdb_pid,
```

对于 attach 模式，目标进程 PID 已可通过 `status` 命令获取，`sessions` 列表展示 GDB 进程 PID 更实用。

### 3.3 Feature: env-check --gdb-path

**文件**: `src/gdb_cli/env_check.py`, `src/gdb_cli/cli.py`

#### cli.py 改动

```python
@main.command()
@click.option("--gdb-path", default=None, help="指定 GDB 可执行文件路径")
def env_check(gdb_path: str) -> None:
    results = get_env_check_cli_output(gdb_path=gdb_path)
    print_json(results)
```

#### env_check.py 改动

- `check_environment(gdb_path=None)` 接受可选参数
- `_check_gdb(report, gdb_path=None)` 优先使用传入路径，否则 fallback 到 `shutil.which("gdb")`
- `get_env_check_cli_output(gdb_path=None)` 透传参数

```python
def _check_gdb(report, gdb_path=None):
    if gdb_path is None:
        gdb_path = shutil.which("gdb")
    if not gdb_path:
        report.errors.append("GDB not found in PATH")
        ...
        return
    report.gdb_path = gdb_path
    # ... 后续版本检测不变
```

## 4. 验证计划

| 场景 | 预期结果 |
|------|----------|
| `gdb-cli status -s <id>` (core 模式) | `binary` 返回实际路径，非 null |
| `gdb-cli sessions` (core 模式) | `pid` 返回 GDB 进程 PID，非 null |
| `gdb-cli sessions` (attach 模式) | `pid` 返回 GDB 进程 PID |
| `gdb-cli env-check` | 默认检查 PATH 中的 gdb |
| `gdb-cli env-check --gdb-path /usr/libexec/gdb` | 检查指定路径的 gdb |
| `gdb-cli env-check --gdb-path /nonexistent` | 报错 GDB not found |

## 5. 实现清单

- [ ] Fix `_build_server_commands()` 传完整 session_meta 给 `start_server()`
- [ ] Fix `sessions` 命令输出 `gdb_pid` 替代 `pid`
- [ ] Add `--gdb-path` option to `env-check` command
- [ ] Update `check_environment()` / `_check_gdb()` 支持自定义 gdb_path
- [ ] 更新主 spec §2.8 文档
