# gdb-cli 命令参考

完整 22 命令详细用法，按功能分类。

## 会话管理

### gdb-cli load

加载 core dump 文件并创建调试会话。

```bash
gdb-cli load -b <binary> -c <core> [--timeout <seconds>] [--sysroot <path>] [--solib-prefix <path>] [--gdb-path <path>] [--source-dir <path>]
```

**参数：**
- `-b, --binary` - 可执行文件路径
- `-c, --core` - Core dump 文件路径
- `--timeout` - 加载超时时间（秒），默认 120
- `--sysroot` - 动态库搜索根目录
- `--solib-prefix` - 共享库前缀路径
- `--gdb-path` - 指定 GDB 可执行文件路径
- `--source-dir` - 源码目录路径

**返回：**
```json
{
  "session_id": "abc123",
  "mode": "core",
  "binary": "/path/to/binary",
  "core": "/path/to/core"
}
```

### gdb-cli attach

Attach 到运行中的进程。

```bash
gdb-cli attach -p <pid> [--timeout <seconds>]
```

**参数：**
- `-p, --pid` - 进程 ID
- `--timeout` - Attach 超时时间（秒），默认 120

### gdb-cli sessions

列出所有活跃的调试会话。

```bash
gdb-cli sessions
```

**返回：**
```json
{
  "sessions": [
    {
      "session_id": "abc123",
      "mode": "core",
      "binary": "/path/to/binary",
      "pid": 12345,
      "started_at": 1648234567.89
    }
  ],
  "count": 1
}
```

### gdb-cli status

查看调试会话状态。

```bash
gdb-cli status -s <session_id>
```

**参数：**
- `-s, --session` - 会话 ID

**返回：**
```json
{
  "session_id": "abc123",
  "state": "ready",
  "mode": "core",
  "binary": "/path/to/binary",
  "threads_count": 125,
  "current_thread": 1,
  "current_frame": 0
}
```

### gdb-cli stop

停止并清理调试会话。

```bash
gdb-cli stop -s <session_id>
```

**参数：**
- `-s, --session` - 会话 ID

### gdb-cli env-check

环境检查：GDB 版本、ptrace 权限、Python 版本。

```bash
gdb-cli env-check [--gdb-path <path>]
```

**参数：**
- `--gdb-path` - 指定 GDB 可执行文件路径

**返回：**
```json
{
  "python_version": "3.9.5",
  "platform": "linux",
  "arch": "x86_64",
  "gdb_path": "/usr/bin/gdb",
  "gdb_version": "9.2",
  "gdb_supported": true,
  "ptrace_scope": 0,
  "ptrace_allowed": true,
  "ready": true
}
```

## 线程操作

### gdb-cli threads

列出所有线程。

```bash
gdb-cli threads -s <session_id> [--limit <n>] [--filter <pattern>]
```

**参数：**
- `-s, --session` - 会话 ID
- `--limit` - 返回线程数量限制，默认 20
- `--filter` - 线程名过滤模式

**返回：**
```json
{
  "threads": [
    {
      "id": 1,
      "name": "Thread 1",
      "state": "stopped",
      "frame": "signal_handler() at signal.c:42"
    }
  ],
  "count": 1,
  "total": 125,
  "hint": "Use --limit to see more threads"
}
```

### gdb-cli thread-switch

切换当前线程。

```bash
gdb-cli thread-switch -s <session_id> <thread_id>
```

**参数：**
- `-s, --session` - 会话 ID
- `thread_id` - 目标线程 ID

### gdb-cli thread-apply

对多个线程执行命令。

```bash
gdb-cli thread-apply -s <session_id> [--threads <id_list>] [--all] <command>
```

**参数：**
- `-s, --session` - 会话 ID
- `--threads` - 线程 ID 列表（逗号分隔）
- `--all` - 对所有线程执行
- `command` - 要执行的命令

**警告：** `thread-apply` 内部使用 gdb.execute()，在大型 binary 上不稳定。建议使用 `threads` + 逐个 `bt --thread N` 组合替代。

**示例：**
```bash
# 不推荐：使用 thread-apply
gdb-cli thread-apply -s abc123 --all bt

# 推荐：使用 threads + 逐个 bt
gdb-cli threads -s abc123 --limit 200
# 然后对每个目标线程执行
gdb-cli bt -s abc123 --thread 5
```

## 栈帧导航

### gdb-cli bt

获取 backtrace。

```bash
gdb-cli bt -s <session_id> [--thread <id>] [--limit <n>]
```

**参数：**
- `-s, --session` - 会话 ID
- `--thread` - 指定线程 ID
- `--limit` - 返回栈帧数量限制，默认 20

**返回：**
```json
{
  "frames": [
    {
      "frame": 0,
      "func": "crash_function",
      "file": "crash.cpp",
      "line": 42,
      "args": [
        {"name": "ptr", "value": "0x0"}
      ]
    }
  ],
  "count": 1
}
```

### gdb-cli frame

选择栈帧。

```bash
gdb-cli frame -s <session_id> <frame_num>
```

**参数：**
- `-s, --session` - 会话 ID
- `frame_num` - 栈帧编号

### gdb-cli up

向上移动一个栈帧。

```bash
gdb-cli up -s <session_id>
```

**参数：**
- `-s, --session` - 会话 ID

### gdb-cli down

向下移动一个栈帧。

```bash
gdb-cli down -s <session_id>
```

**参数：**
- `-s, --session` - 会话 ID

## 变量与表达式

### gdb-cli eval-cmd

求值 C/C++ 表达式。

```bash
gdb-cli eval-cmd -s <session_id> <expression>
```

**参数：**
- `-s, --session` - 会话 ID
- `expression` - C/C++ 表达式

**示例：**
```bash
gdb-cli eval-cmd -s abc123 "this->member_"
gdb-cli eval-cmd -s abc123 "*ptr"
gdb-cli eval-cmd -s abc123 "array[5]"
```

**重要：** eval-cmd 在当前选中的线程/帧上下文中执行，需先用 `thread-switch` + `frame` 切换到目标位置。

### gdb-cli eval-element

访问数组元素。

```bash
gdb-cli eval-element -s <session_id> <var_name> <index>
```

**参数：**
- `-s, --session` - 会话 ID
- `var_name` - 数组变量名
- `index` - 元素索引

### gdb-cli locals-cmd

获取当前帧的局部变量。

```bash
gdb-cli locals-cmd -s <session_id> [--thread <id>] [--frame <n>]
```

**参数：**
- `-s, --session` - 会话 ID
- `--thread` - 指定线程 ID
- `--frame` - 指定栈帧编号

### gdb-cli args

获取当前帧的函数参数。

```bash
gdb-cli args -s <session_id> [--thread <id>] [--frame <n>]
```

**参数：**
- `-s, --session` - 会话 ID
- `--thread` - 指定线程 ID
- `--frame` - 指定栈帧编号

### gdb-cli ptype

查看类型定义。

```bash
gdb-cli ptype -s <session_id> <type_name>
```

**参数：**
- `-s, --session` - 会话 ID
- `type_name` - 类型名或变量名

**示例：**
```bash
gdb-cli ptype -s abc123 "MyClass"
gdb-cli ptype -s abc123 "this->member_"
```

## 寄存器与内存

### gdb-cli registers

查看寄存器值。

```bash
gdb-cli registers -s <session_id>
```

**参数：**
- `-s, --session` - 会话 ID

**返回：**
```json
{
  "registers": {
    "rax": "0x0",
    "rbx": "0x7fffffffe4c8",
    "rsp": "0x7fffffffe4a0",
    "rip": "0x401234",
    ...
  }
}
```

### gdb-cli memory

检查内存内容。

```bash
gdb-cli memory -s <session_id> <address> [--count <n>] [--format <fmt>]
```

**参数：**
- `-s, --session` - 会话 ID
- `address` - 内存地址（支持十六进制和表达式）
- `--count` - 元素数量，默认 10
- `--format` - 显示格式：x(hex), d(decimal), u(unsigned), o(octal), t(binary)

**示例：**
```bash
gdb-cli memory -s abc123 "0x7fffffffe4a0" --count 20
gdb-cli memory -s abc123 "ptr" --format d
```

## 共享库与反汇编

### gdb-cli sharedlibs

列出加载的共享库。

```bash
gdb-cli sharedlibs -s <session_id>
```

**参数：**
- `-s, --session` - 会话 ID

**返回：**
```json
{
  "libraries": [
    {
      "name": "libpthread.so.0",
      "path": "/lib64/libpthread.so.0",
      "address_range": "0x7f0000-0x7f1000"
    }
  ]
}
```

### gdb-cli disasm

反汇编代码。

```bash
gdb-cli disasm -s <session_id> [--start <addr>] [--end <addr>] [--count <n>]
```

**参数：**
- `-s, --session` - 会话 ID
- `--start` - 起始地址
- `--end` - 结束地址
- `--count` - 指令数量，默认 20

## exec 命令替代速查表

| 使用场景 | 旧方法（已废弃） | 新方法 |
|---------|---------------|--------|
| 查看所有线程堆栈 | `gdb-cli exec "thread apply all bt"` | `gdb-cli threads --limit 200` + 逐个 `gdb-cli bt --thread N` |
| 执行任意 GDB 命令 | `gdb-cli exec "info registers"` | `gdb-cli registers` |
| 查看内存 | `gdb-cli exec "x/10x 0x1234"` | `gdb-cli memory 0x1234 --count 10` |
| 反汇编 | `gdb-cli exec "disassemble"` | `gdb-cli disasm` |

**重要：** `gdb-cli exec` 命令在大型 binary 上会导致 SEGFAULT，已废弃。使用以上对应命令替代。

## 最佳实践

### 1. 会话生命周期管理

```bash
# 加载
gdb-cli load -b /path/to/binary -c /path/to/core
# 获取 session_id
# ...调试工作...
# 清理
gdb-cli stop -s <session_id>
```

### 2. 大型 binary 加载策略

```bash
# 渐进式超时重试
gdb-cli load -b binary -c core --timeout 120   # 2分钟
# 若超时，重试
gdb-cli load -b binary -c core --timeout 300   # 5分钟
# 仍超时，最后尝试
gdb-cli load -b binary -c core --timeout 600   # 10分钟
```

### 3. 多线程调试模式

```bash
# 1. 列出线程，找到目标线程
gdb-cli threads -s <SID> --filter "worker"

# 2. 查看目标线程堆栈
gdb-cli bt -s <SID> --thread 5

# 3. 切换到目标线程
gdb-cli thread-switch -s <SID> 5

# 4. 选择栈帧
gdb-cli frame -s <SID> 0

# 5. 查看变量
gdb-cli locals-cmd -s <SID>
gdb-cli eval-cmd -s <SID> "ptr->member"
```

### 4. Shell 转义技巧

```bash
# 错误：$ 符号会被 shell 解释
gdb-cli eval-cmd -s abc123 "obj->member$"

# 正确：用单引号包裹
gdb-cli eval-cmd -s abc123 'obj->member$'

# 更好：使用寄存器命令
gdb-cli registers -s abc123  # 直接查看寄存器值，无需转义
```

### 5. 复杂类型查看

```bash
# 先查看类型定义
gdb-cli ptype -s abc123 "MyClass"

# 再查看实例
gdb-cli eval-cmd -s abc123 "obj"

# 深入查看成员
gdb-cli eval-cmd -s abc123 "obj->nested_->value_"
```
