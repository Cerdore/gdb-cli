# GDB CLI for AI

[English](README.md) | [中文](README.zh-CN.md)

一个为 AI Agent（Claude Code 等）设计的 GDB 调试工具。采用"瘦客户端 CLI + GDB 内置 Python RPC Server"架构，通过 Bash 即可完成有状态的 GDB 调试。

## 特性

- **Core Dump 分析**: 加载 core dump，符号表常驻内存，毫秒级响应
- **Live Attach 调试**: Attach 到运行中进程，支持 non-stop 模式
- **结构化 JSON 输出**: 所有命令输出 JSON，自动截断/分页，附带操作提示
- **安全机制**: 命令白名单、心跳超时自动清理、幂等性保证
- **数据库场景优化**: scheduler-locking、大对象分页、多线程截断

## 环境要求

- **Python**: 3.8+
- **GDB**: 9.0+，**必须带 Python 支持**
- **OS**: Linux

### GDB Python 支持检查

```bash
# 检查 GDB 是否带 Python 支持
gdb -nx -q -batch -ex "python print('OK')"

# 如果系统 GDB 不带 Python，检查 GCC Toolset（RHEL/CentOS）
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## 安装

```bash
# clone 后本地安装
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .

# 环境自检
gdb-cli env-check
```

## 快速开始

### 1. 加载 Core Dump

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

输出：
```json
{
  "session_id": "f465d650",
  "mode": "core",
  "binary": "./my_program",
  "core": "./core.12345",
  "gdb_pid": 12345,
  "status": "started"
}
```

> 如果系统默认 GDB 没有 Python 支持，通过 `--gdb-path` 指定：
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. 调试操作

所有操作命令通过 `--session` / `-s` 指定会话 ID：

```bash
SESSION="f465d650"

# 列出线程
gdb-cli threads -s $SESSION

# 获取 backtrace（默认当前线程）
gdb-cli bt -s $SESSION

# 获取指定线程的 backtrace
gdb-cli bt -s $SESSION --thread 3

# 求值 C/C++ 表达式
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# 访问数组元素
gdb-cli eval-element -s $SESSION "my_array" --index 5

# 查看局部变量
gdb-cli locals-cmd -s $SESSION

# 执行原始 GDB 命令
gdb-cli exec -s $SESSION "info registers"

# 查看会话状态
gdb-cli status -s $SESSION
```

### 3. 会话管理

```bash
# 列出所有活跃会话
gdb-cli sessions

# 停止会话
gdb-cli stop -s $SESSION
```

### 4. Live Attach 调试

```bash
# Attach 到运行中进程（默认 scheduler-locking + non-stop）
gdb-cli attach --pid 9876

# 带符号文件 attach
gdb-cli attach --pid 9876 --binary ./my_program

# 允许内存修改和函数调用
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## 完整命令参考

### load — 加载 Core Dump

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      可执行文件路径（必需）
  --core, -c        Core dump 文件路径（必需）
  --sysroot         sysroot 路径（跨机器调试时使用）
  --solib-prefix    共享库前缀
  --source-dir      源码目录
  --timeout         心跳超时秒数（默认 600）
  --gdb-path        GDB 可执行文件路径（默认 "gdb"）
```

### attach — Attach 到进程

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               进程 PID（必需）
  --binary                可执行文件路径（可选）
  --scheduler-locking     启用 scheduler-locking（默认 true）
  --non-stop              启用 non-stop 模式（默认 true）
  --timeout               心跳超时秒数（默认 600）
  --allow-write           允许内存修改
  --allow-call            允许函数调用
```

### threads — 列出线程

```
gdb-cli threads -s <session> [options]

  --range           线程范围，如 "3-10"
  --limit           最大返回数量（默认 20）
  --filter-state    过滤状态（"running" / "stopped"）
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      指定线程 ID
  --limit           最大帧数（默认 30）
  --full            包含局部变量
  --range           帧范围，如 "5-15"
```

### eval-cmd — 表达式求值

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       递归深度限制（默认 3）
  --max-elements    数组元素限制（默认 50）
```

### eval-element — 访问数组/容器元素

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — 执行原始 GDB 命令

```
gdb-cli exec -s <session> <command>

  --safety-level    安全级别（readonly / readwrite / full）
```

### thread-apply — 批量线程操作

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## 输出示例

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

## 安全机制

### 命令白名单（attach 模式）

| 安全等级 | 允许的命令 |
|---------|-----------|
| `readonly`（默认）| bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`、`kill`、`shell`、`signal` 始终禁止。

### 心跳超时

默认 10 分钟无操作自动 detach + quit，可通过 `--timeout` 配置。

### 幂等性

同一 PID / Core 文件只允许一个 session。重复 load/attach 返回已有 session_id。

## 跨机器 Core Dump 调试

当 core dump 在其他机器上分析时，共享库路径可能不同：

```bash
# 设置 sysroot（整体路径前缀替换）
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# 设置源码目录（用于源码级调试）
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## 开发

### 项目结构

```
src/gdb_cli/
├── cli.py              # CLI 入口 (Click)
├── client.py           # Unix Socket 客户端
├── launcher.py         # GDB 进程启动器
├── session.py          # Session 元数据管理
├── safety.py           # 命令白名单过滤
├── formatters.py       # JSON 输出格式化
├── env_check.py        # 环境自检
├── errors.py           # 错误分类
└── gdb_server/
    ├── gdb_rpc_server.py   # RPC Server 核心
    ├── handlers.py         # 命令处理器
    ├── value_formatter.py  # gdb.Value 序列化
    └── heartbeat.py        # 心跳超时管理
```

### 运行测试

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### 端到端测试

需要带 Python 支持的 GDB。使用 `tests/crash_test/` 中的崩溃测试程序：

```bash
# 编译测试程序
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# 生成 coredump
ulimit -c unlimited
./crash_test  # 会 SIGSEGV

# 找到 core 文件
ls /path/to/core_dumps/core-crash_test-*

# 运行 E2E 测试
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## 已知限制

- 不支持 `target remote`（可通过 SSH 远程调试，见下文）
- 不支持多 inferior 调试
- GDB 12.x 的 Guile pretty printer 非线程安全，已通过 `format_string(raw=True)` 绕过
- GDB 内嵌 Python 版本可能较低（如 3.6.8），代码已做兼容处理

## 通过 SSH 远程调试

远程机器可通过 SSH 一行命令安装并运行：

```bash
ssh user@remote-host "git clone https://github.com/Cerdore/gdb-cli.git && cd gdb-cli && pip install -e . && gdb-cli load --binary ./my_program --core ./core.12345"
```

或者本地安装后同步到远程：

```bash
# 本地安装，然后同步到远程
pip install -e .
rsync -av . user@remote-host:/path/to/gdb-cli/

# 在远程运行
ssh user@remote-host "cd /path/to/gdb-cli && gdb-cli load --binary ./my_program --core ./core.12345"
```

## 许可证

MIT License