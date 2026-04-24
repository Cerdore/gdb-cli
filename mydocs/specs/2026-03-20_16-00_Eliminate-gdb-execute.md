# SDD Spec: 消除 gdb.execute() — 纯 Python API 替代方案

## 0. Open Questions
- [x] Q1: exec 命令是否完全移除？→ **保留但标记 DEPRECATED，新增命令覆盖所有场景**
- [x] Q2: thread-apply 如何处理？→ **标记 UNSTABLE，建议用 threads + bt --thread N 组合**

## 1. Requirements (Context)

- **Goal**: 消除所有 handler 中的 `gdb.execute()` 调用，用纯 GDB Python API 替代，确保在大型 binary（779 线程, 6.1G）上稳定运行
- **In-Scope**:
  - 修复 `handle_frame_select()` 和 `handle_locals()` 中的 `gdb.execute("frame N")`
  - 新增 7 个结构化命令替代 `exec` 的常见使用场景
  - 更新 Claude Code 使用文档
- **Out-of-Scope**:
  - 完全移除 exec 命令（保留向后兼容，标记 DEPRECATED）
  - 修复 thread-apply（需要 `gdb.execute()`，无法用 Python API 替代 arbitrary command）

## 1.1 Context Sources
- E2E Testing Spec: `mydocs/specs/2026-03-19_21-00_E2E-Testing-Team.md` §8.5 根因分析
- Project Spec: `mydocs/specs/2026-03-19_17-30_GDB-CLI-for-AI.md`

## 2. Research Findings

### 2.1 根因回顾

`gdb.execute()` 从后台线程调用时走 GDB CLI 解释器完整路径（命令解析 → 输出重定向 → 全局状态修改），与主线程竞争导致 SEGFAULT。小程序碰巧能用（竞争窗口小），大型 binary 100% 复现。

### 2.2 安全 API 边界（已验证）

| 安全 | 不安全 |
|------|--------|
| `frame.select()` | `gdb.execute()` |
| `frame.read_register(name)` | `str(gdb.Value)` |
| `frame.architecture().disassemble()` | |
| `inferior.read_memory(addr, size)` | |
| `gdb.parse_and_eval(expr).type` | |
| `gdb.objfiles()` | |

### 2.3 受影响代码

| handler | 问题 | 修复方案 |
|---------|------|---------|
| `handle_frame_select()` L386 | `gdb.execute("frame N")` | 帧链遍历 + `frame.select()` |
| `handle_locals()` L436 | `gdb.execute("frame N")` | 同上 |
| `handle_exec()` L530 | `gdb.execute(command)` | 标记 DEPRECATED |
| `handle_thread_apply()` L710 | `gdb.execute(command)` | 标记 UNSTABLE |

## 3. Innovate (Skipped)
- 跳过原因：方案明确——用已验证安全的 Python API 一一替代

## 4. Plan (Contract)

### 4.1 修复项

| # | 文件 | 改动 |
|---|------|------|
| 1 | `handlers.py` | `handle_frame_select()`: 新增 `_select_frame_by_number()` 帧链遍历，支持 up/down 相对移动 |
| 2 | `handlers.py` | `handle_locals()`: 帧选择改用 `_select_frame_by_number()` |

### 4.2 新增 Handler

| # | handler | Python API | CLI 命令 |
|---|---------|-----------|---------|
| 3 | `handle_args()` | `frame.block()` + `sym.is_argument` | `gdb-cli args` |
| 4 | `handle_registers()` | `frame.read_register(name)` | `gdb-cli registers` |
| 5 | `handle_memory()` | `inferior.read_memory(addr, size)` | `gdb-cli memory` |
| 6 | `handle_ptype()` | `val.type` + `type.fields()` + `strip_typedefs()` | `gdb-cli ptype` |
| 7 | `handle_thread_switch()` | `thread.switch()` | `gdb-cli thread-switch` |
| 8 | `handle_sharedlibs()` | `gdb.objfiles()` | `gdb-cli sharedlibs` |
| 9 | `handle_disasm()` | `arch.disassemble()` | `gdb-cli disasm` |

### 4.3 CLI 命令新增

| # | 命令 | 说明 |
|---|------|------|
| 10 | `gdb-cli up [count]` | 向调用者方向移动帧 |
| 11 | `gdb-cli down [count]` | 向被调用者方向移动帧 |

### 4.4 其他改动

| # | 文件 | 改动 |
|---|------|------|
| 12 | `gdb_rpc_server.py` | 注册 7 个新 handler |
| 13 | `cli.py` | 新增 9 个 CLI 命令（7 新 handler + up + down） |
| 14 | 使用文档 | 更新 `mydocs/gdb-cli-usage-for-claude-code.md` |

## 5. Execute Log

### 5.1 代码修改

**修改文件**:

1. `src/gdb_cli/gdb_server/handlers.py`:
   - 新增 `_select_frame_by_number()` — 帧链遍历替代 `gdb.execute("frame N")`
   - 修复 `handle_frame_select()` — 支持绝对编号 + up/down 相对移动
   - 修复 `handle_locals()` — 帧选择改用 `_select_frame_by_number()`
   - 新增 `handle_args()` — 函数参数读取
   - 新增 `handle_registers()` — 寄存器读取（默认 x86_64 常用寄存器）
   - 新增 `handle_memory()` — 内存检查（hex/bytes/string 三种格式）
   - 新增 `handle_ptype()` — 类型信息（含字段列表、typedef 剥离、枚举值）
   - 新增 `handle_thread_switch()` — 线程切换
   - 新增 `handle_sharedlibs()` — 共享库列表
   - 新增 `handle_disasm()` — 反汇编

2. `src/gdb_cli/gdb_server/gdb_rpc_server.py`:
   - 注册 7 个新 handler: args, registers, memory, ptype, thread_switch, sharedlibs, disasm

3. `src/gdb_cli/cli.py`:
   - 新增 9 个 CLI 命令: args, registers, memory, ptype, thread-switch, up, down, sharedlibs, disasm

4. `mydocs/gdb-cli-usage-for-claude-code.md`:
   - 完整更新，覆盖全部 22 个命令
   - exec 替代速查表
   - 3 个典型调试工作流

### 5.2 测试结果

- 单元测试: 167 passed (0.38s) — 无回归
- CLI 命令注册: 22 个命令全部注册成功

## 6. Review Verdict

### 6.1 改动统计

| 指标 | 数值 |
|------|------|
| 修复的 gdb.execute() 调用 | 2 处 (frame_select, locals) |
| 新增 handler | 7 个 |
| 新增 CLI 命令 | 9 个 (含 up/down) |
| 总命令数 | 22 个 |
| 测试回归 | 0 |

### 6.2 gdb.execute() 消除状态

| handler | 修复前 | 修复后 |
|---------|--------|--------|
| `handle_frame_select()` | `gdb.execute("frame N")` | `_select_frame_by_number()` + `frame.select()` |
| `handle_locals()` | `gdb.execute("frame N")` | `_select_frame_by_number()` |
| `handle_exec()` | `gdb.execute(command)` | **保留**，标记 DEPRECATED |
| `handle_thread_apply()` | `gdb.execute(command)` | **保留**，标记 UNSTABLE |

### 6.3 exec 替代覆盖率

| 原 GDB 命令 | 替代命令 | 状态 |
|---|---|---|
| `info threads` | `threads` | 已有 |
| `thread N` | `thread-switch` | **新增** |
| `bt` | `bt` | 已有 |
| `frame N` | `frame` | **修复** |
| `up` / `down` | `up` / `down` | **新增** |
| `info locals` | `locals` | **修复** |
| `info args` | `args` | **新增** |
| `print EXPR` | `eval-cmd` | 已有 |
| `ptype EXPR` | `ptype` | **新增** |
| `info registers` | `registers` | **新增** |
| `x/Nxb ADDR` | `memory` | **新增** |
| `info sharedlibrary` | `sharedlibs` | **新增** |
| `disassemble` | `disasm` | **新增** |

**结论**: exec 的所有常见使用场景均已被结构化命令覆盖。

---

*最后更新: 2026-03-20 16:00*
