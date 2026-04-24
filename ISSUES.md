# GDB-CLI 项目缺陷报告

调查日期：2026-04-25
最后更新：2026-04-25（修复 9 个严重/高优先级问题）

---

## 已修复的严重问题

### 1. ~~通过 `exec` 命令实现远程代码执行（RCE）~~ ✅ 已修复

**文件：** `src/gdb_cli/safety.py:60`，`src/gdb_cli/gdb_server/handlers.py:35-45,567-576`

**修复内容：**
- `safety.py`: 将 `"python"` 加入 `FORBIDDEN_COMMANDS`
- `handlers.py`: 动态导入 `SafetyFilter` 和 `SafetyLevel`，替换内联的危险命令检查
- 修复了 `_safety_path` 路径错误（应为 `Path(_server_dir).parent / "safety.py"`）

### 2. ~~`handle_thread_apply` 零安全过滤~~ ✅ 已修复

**文件：** `src/gdb_cli/gdb_server/handlers.py:788-796`

**修复内容：**
- 在 `gdb.execute(command)` 之前添加 `SafetyFilter.check_command()` 调用

### 3. ~~客户端控制的安全级别绕过服务端会话配置~~ ✅ 已修复

**文件：** `src/gdb_cli/cli.py:345-359`，`src/gdb_cli/client.py:221-223`，`src/gdb_cli/gdb_server/gdb_rpc_server.py:279-280`

**修复内容：**
- `gdb_rpc_server.py`: 在 `_dispatch` 中强制使用 session 配置的 `safety_level`，忽略客户端传入的值
- `cli.py`: 移除 `--safety-level` 选项
- `client.py`: 移除 `exec_cmd()` 的 `safety_level` 参数

---

## 已修复的高优先级可靠性问题

### 4. ~~PID 复用检测缺陷~~ ✅ 已修复

**文件：** `src/gdb_cli/session.py:175-195`

**修复内容：**
- `_is_session_alive()` 在 `os.kill(pid, 0)` 之后使用 `psutil.Process(name)` 交叉验证进程名（psutil 不可用时优雅降级）

### 5. ~~未注册信号处理器~~ ✅ 已修复

**文件：** `src/gdb_cli/signal_handlers.py`（新建），`src/gdb_cli/cli.py:66`

**修复内容：**
- 创建 `signal_handlers.py` 模块，注册 SIGTERM/SIGINT 处理器
- 在 `cli.py` 的 `main()` 中调用 `setup_signal_handlers()`
- 支持通过 `register_cleanup()` 注册自定义清理回调

### 6. ~~启动器中异常路径下的 FIFO/文件描述符泄漏~~ ✅ 已修复

**文件：** `src/gdb_cli/launcher.py:329-333,385-394`

**修复内容：**
- 添加 `_cleanup_fifo_if_exists()` 辅助函数
- 在 `FileNotFoundError` 和通用 `Exception` 处理器中调用 FIFO/fd 清理

### 7. ~~`_wait_for_socket` 在 GDB 崩溃时阻塞整个超时时间~~ ✅ 已修复

**文件：** `src/gdb_cli/launcher.py:397-409,387`

**修复内容：**
- `_wait_for_socket()` 接收可选的 `process` 参数
- 每次轮询时检查 `process.poll()`，若 GDB 已退出则立即抛出 `GDBLauncherError`

### 8. ~~Accept 线程中调用了 15 个以上 GDB API 的处理器~~ ✅ 已修复

**文件：** `src/gdb_cli/gdb_server/gdb_rpc_server.py:248-298`

**修复内容：**
- 重构 `_dispatch()` 方法：所有 handler 调用通过 `gdb.post_event()` 路由到 GDB 主线程，使用 `queue.Queue` 同步获取结果
- 添加 `import queue` 到模块引用

### 9. ~~心跳超时使用 `os._exit(0)` 跳过清理~~ ✅ 已修复

**文件：** `src/gdb_cli/gdb_server/gdb_rpc_server.py:331-347`

**修复内容：**
- 在 `os._exit(0)` 之前添加 socket 文件清理（`self.sock_path.unlink()`）

---

## 测试改进

### 单元测试 ✅ 已实现

| 文件 | 状态 | 测试数量 |
|------|------|----------|
| `tests/test_safety.py` | 从 pass stub 重写 | 32 |
| `tests/test_handlers.py` | 从 pass stub 重写 | 20 |
| `tests/test_session.py` | 从 pass stub 重写 | 10 |
| `tests/test_client.py` | 从 pass stub 重写 | 11 |

### E2E 测试 ✅ 已创建

| 文件 | 测试类型 | 测试数量 |
|------|---------|----------|
| `tests/test_e2e_core_analysis.py` | Core dump 分析 | 4 |
| `tests/test_e2e_multithread.py` | 多线程分析 | 3 |
| `tests/test_e2e_memory.py` | 内存检查 | 4 |

### 测试基础设施 ✅ 已创建

| 文件 | 用途 |
|------|------|
| `tests/conftest.py` | pytest fixtures, GDB 可用性检查, crash binary 编译 |
| `tests/helpers.py` | 辅助函数（编译、等待就绪、清理会话） |

---

## 中优先级问题

| # | 问题 | 文件 | 状态 |
|---|-------|------|------|
| 10 | `GDB_CLI_SERVER_DIR` 默认值为 `/tmp`（全局可写，存在代码注入风险） | `handlers.py`、`gdb_rpc_server.py` | 待修复 |
| 11 | 启动器 f-string 中的文件路径未清理（可注入 GDB 命令） | `launcher.py` | 待修复 |
| 12 | Unix socket 无身份验证（任何本地进程均可连接） | `gdb_rpc_server.py` | 待修复 |
| 13 | `handle_exec` 中的动态模块加载未进行空值检查 | `handlers.py`、`gdb_rpc_server.py` | 待修复 |
| 14 | Backtrace 截断标志在范围超过帧数时计算错误 | `handlers.py` | 待修复 |
| 15 | 通过 `all_frames.index(frame)` 实现的 O(n²) 帧号计算 | `handlers.py` | 待修复 |
| 16 | `signal` 模块在首次使用之后才导入 | `session.py` | 待修复 |
| 17 | `cleanup_session()` 发送 SIGTERM 后未执行 `waitpid` | `session.py` | 待修复 |
| 18 | 服务器若从未调用 `set_ready()` 将永久卡在 `loading` 状态 | `gdb_rpc_server.py` | 待修复 |
| 19 | 写入 `meta.json` 存在 TOCTOU 竞态条件（可能将 `gdb_pid` 置零） | `session.py` | 待修复 |
| 20 | ~~`safety.py` 模块在运行时从未被调用~~ | `handlers.py` | ✅ 已修复 |
| 21 | `_gdb_process` 动态属性在磁盘往返后丢失 | `launcher.py` | 待修复 |
| 22 | 接收循环中的 O(n²) 字节拼接（10-50 MB） | `gdb_rpc_server.py`、`client.py` | 待修复 |

---

## 低优先级/边界情况问题

| # | 问题 | 文件 |
|---|-------|------|
| 23 | `client.py` connect() 中的 TOCTOU socket 竞态 | `client.py:70-76` |
| 24 | 截断的 8 字符会话 ID（32 位熵） | `session.py:73` |
| 25 | 自定义异常类覆盖内建异常（`PermissionError`、`TimeoutError`、`ConnectionError`） | `errors.py:76-109` |
| 26 | 内存读取大小限制静默截断（无用户提示） | `handlers.py:1004-1010` |
| 27 | value_formatter 中未处理 NaN/Infinity | `value_formatter.py:86-93` |
| 28 | 大整数 JSON 精度丢失（> 2⁵³） | `value_formatter.py:153-160` |
| 29 | `handle_registers` 中硬编码了 x86_64 寄存器名称 | `handlers.py:913-916` |
| 30 | 弱远程地址验证正则表达式 | `cli.py:207-209` |
| 31 | 内存/限制/帧号无负数验证 | `cli.py`（多处） |
| 32 | 二进制文件/core 文件无文件存在性验证 | `cli.py:73-76` |
| 33 | ~~测试文件为占位符（256 个测试定义中约 200 个仅包含 `pass`）~~ ✅ 已修复 |
| 34 | ~~无实际 GDB 交互的端到端测试~~ ✅ 已修复 |
| 35 | `env_check.py` 中 i18n 未完成（TODO 注释） | `env_check.py:10-12` |
| 36 | `formatters.py` 和 `heartbeat.py` 为空占位模块 | `formatters.py`、`heartbeat.py` |
| 37 | ruff 目标版本 `py37` 与 `requires-python >=3.6.8` 不匹配 | `pyproject.toml` |

---

## 统计

| 严重程度 | 数量 | 已修复 | 待修复 |
|----------|------|--------|--------|
| **严重** | 3 | 3 | 0 |
| **高** | 6 | 6 | 0 |
| **中** | 13 | 1 (#20) | 12 |
| **低** | 15 | 2 (#33, #34) | 13 |

**已修复 12 个问题，共计 37 个已识别问题。**
