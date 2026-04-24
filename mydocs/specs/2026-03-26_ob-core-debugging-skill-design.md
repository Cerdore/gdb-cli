# DB Core Debugging Skill 设计文档

> 日期：2026-03-26
> 状态：Draft

## 1. 概述

创建一个 Claude Code Skill（`db-core-debugging`），指导 AI Agent 使用 `gdb-cli` 工具自动化分析 Database core dump 文件。Skill 采用工作流驱动模式，定义严格的分步调试流程，包含异常处理分支和 DB 特有诊断技巧。

### 目标
- AI Agent 自用：Claude Code 在调试 DB core dump 时自动遵循最佳实践
- 覆盖核心场景：崩溃定位（SIGSEGV/SIGABRT）为主
- 结合源码分析：从堆栈信息关联到本地源码，推断根因

### 非目标
- 不覆盖 Live Attach 调试（后续迭代）
- 不做 DB 全量诊断（如 sql audit 导出、内存使用量导出等高级功能）
- 不替代 gdb-cli 工具本身的文档

## 2. 目标仓库与目录结构

Skill 将上传到 `database-skills` 仓库：

```
packages/
  database-core-debugging/
    SKILL.md                  # 主文件：工作流 + 异常处理 + 关键命令速查
    gdb-cli-reference.md      # 补充参考：完整 22 命令详细用法
```

- `SKILL.md`：保持精简（< 800 词），专注于工作流指导
- `gdb-cli-reference.md`：heavy reference 模式，包含完整命令参考（来自 `gdb-cli-usage-for-claude-code.md`）

## 3. Skill 元信息

```yaml
---
name: db-core-debugging
description: 使用 gdb-cli 工具调试 Database core dump 文件时触发。当用户提到 core dump、coredump、崩溃分析、server 崩溃、段错误、SIGSEGV、SIGABRT、堆栈分析等关键词时使用。
---
```

### 触发场景
- 用户提供 core 文件和 server 二进制，要求分析崩溃原因
- 用户提到 "core dump"、"coredump"、"server 崩溃"、"段错误" 等关键词
- 用户在 Database 项目中遇到进程异常退出

## 4. 核心工作流

### 4.1 流程总览

```
Step 0: 环境检查
  ↓
Step 1: 加载 core dump（含重试策略）
  ↓ 异常分支 → 排查 debuginfo/二进制匹配/动态库
Step 2: 状态概览
  ↓
Step 3: 崩溃线程定位
  ↓
Step 4: 堆栈分析
  ↓
Step 4.5: 源码关联分析（可选）
  ↓
Step 5: 变量与上下文检查
  ↓
Step 6: 深入诊断（按崩溃类型选择）
  ↓
Step 7: 根因推断 + 输出结论
  ↓
Step 8: 清理
```

### 4.2 各步骤详细设计

#### Step 0: 环境检查

```bash
# 检查 gdb-cli 是否安装
gdb-cli env-check
```

- 若 `gdb-cli` 命令不存在 → 提示安装：`pip install git+http://gitlab.internal.example.com/tools/gdb_cli.git`
- 检查 GDB 版本：el7/el8 需要 9.0+，el9/Rocky 需要 15+
- 检查 GDB Python 支持：`gdb -batch -ex "python print('ok')"` 输出 `ok`

#### Step 1: 加载 core dump（重试策略）

大型 DB binary（6.1G+）加载时间不可预测，采用渐进式超时重试：

```
第 1 次：gdb-cli load -b <binary> -c <core> --timeout 120  （2分钟）
若超时 → 第 2 次：gdb-cli load -b <binary> -c <core> --timeout 300  （5分钟）
若仍超时 → 第 3 次：gdb-cli load -b <binary> -c <core> --timeout 600  （10分钟）
仍失败 → 报错并提示可能原因
```

> **注意**：`--timeout` 参数同时控制 socket 等待超时（即加载等待时间）和 session 心跳超时。增大 timeout 既给更多加载时间，也延长 session 空闲存活时间。

gdb-cli 幂等性保证：相同 core 文件不会重复加载，重试安全。

**加载失败排查分支：**
- **不要把 server.debug 当二进制用** → 正确用法：`gdb-cli load -b server -c core.xxx`（不是 server.debug）
- debuginfo 缺失 → 先执行 `readelf -S server | grep -E 'symtab|debug_info'`；最实用的解决方案：把 server.debug 文件 copy 到跟 server 二进制同一目录下，然后在该目录执行加载
- 二进制不匹配 → 确认 arm/x86 架构一致、版本完全匹配（不能用重新编译的，也不能用新 bin 去诊断老 core）
- 跨机器动态库问题 → 使用 `--sysroot` 或 `--solib-prefix` 参数；需将原机器 `/usr/lib64` 下的 so 文件（注意软链要替换为真实文件）一并拷贝
- GDB 版本问题 → 使用 `--gdb-path` 指定正确版本
- core 文件不完整 → 检查磁盘空间，对比进程内存占用（如有量级差距肯定不完整）

#### Step 2: 状态概览

```bash
gdb-cli status -s <session_id>
```

确认：模式（core）、binary 路径、线程数、当前帧信息。

> **约定**：后续命令中 `<SID>` 表示 `gdb-cli load` 返回的 JSON 中的 `session_id` 字段值。

#### Step 3: 崩溃线程定位

```bash
gdb-cli threads -s <SID> --limit 50
```

- 找到信号线程（通常是 thread 1，收到 SIGSEGV/SIGABRT）
- 对于 DB 的 coredump_cb 回调，注意实际崩溃位置可能在信号处理函数的调用者帧中

#### Step 4: 堆栈分析

```bash
gdb-cli bt -s <SID> --thread <crash_thread> --limit 30
```

- 从崩溃帧（frame 0）向上遍历调用链
- 识别关键函数：信号处理函数（coredump_cb）、DB 框架函数、业务逻辑函数
- 记录崩溃点的文件名和行号

#### Step 4.5: 源码关联分析（可选）

如果 `bt` 输出包含源文件信息（file:line）：
1. 尝试在本地工作目录查找对应源码文件
2. 使用 Read 工具读取崩溃位置前后 20 行代码
3. 结合代码逻辑理解崩溃上下文

> **提示**：如果有源码目录，可以在 `gdb-cli load` 时通过 `--source-dir` 参数指定，帮助 GDB 自动关联源文件路径。

如果本地无源码：
- 提示用户提供源码路径
- 或跳过此步，仅基于堆栈信息分析

#### Step 5: 变量与上下文检查

```bash
# 崩溃帧的函数参数（args 支持 --thread 和 --frame）
gdb-cli args -s <SID> --thread <crash_thread> --frame 0

# 崩溃帧的局部变量（注意实际命令名是 locals-cmd）
gdb-cli locals-cmd -s <SID> --thread <crash_thread> --frame 0

# 深入查看关键变量
# 注意：eval-cmd 不支持 --thread/--frame 参数，需要先切换上下文
gdb-cli thread-switch -s <SID> <crash_thread>
gdb-cli frame -s <SID> 0
gdb-cli eval-cmd -s <SID> "this->member_name_"
gdb-cli eval-cmd -s <SID> "*ptr"
```

- 检查空指针、越界值、异常状态
- 对结构体用 `ptype` 查看类型定义
- **重要**：`eval-cmd` 和 `ptype` 在当前选中的线程/帧上下文中执行，务必先用 `thread-switch` + `frame` 切换到目标位置

#### Step 6: 深入诊断

根据崩溃类型选择诊断手段：

| 崩溃类型 | 诊断命令 |
|---------|---------|
| 空指针解引用 | `eval-cmd` 检查指针值，`ptype` 查看类型 |
| 内存越界 | `memory` 检查周边内存，`registers` 查看地址寄存器 |
| 非法指令 | `disasm` 查看崩溃点汇编，`registers` 查看 rip |
| 栈溢出 | `registers` 查看 rsp，`memory` 检查栈边界 |
| 断言失败 | `eval-cmd` 查看断言条件中的变量值 |
| 堆栈残缺/unwind 失败 | `registers` 检查 rbp/rsp，`disasm` 尝试手动追踪帧链 |

**DB 特有诊断（按需）：**
```bash
# 查看 Server 版本
gdb-cli eval-cmd -s $SID "Logger::get_logger().get_log_dir()"

# 查看 server IP
gdb-cli eval-cmd -s $SID "((Addr*)&'server::Server::get_instance().self_')"

# 遍历多租户
gdb-cli eval-cmd -s $SID "GCTX.omt_->tenant_ids_map_"

# 遍历 session
gdb-cli eval-cmd -s $SID "GCTX.session_mgr_"
```

#### Step 7: 根因推断 + 输出结论

输出结构化诊断报告，模板如下：

```markdown
## Core Dump 诊断报告
- **崩溃信号**: SIGSEGV / SIGABRT / ...
- **崩溃线程**: Thread N
- **崩溃位置**: function() at file:line
- **调用链关键路径**:
  - #0 crash_function()
  - #1 caller_function()
  - ...
- **关键变量值**:
  - var_name = value
  - ptr = 0x0 (空指针)
  - ...
- **源码分析**（如有）: 对应代码逻辑说明
- **根因推断**: ...
- **建议修复方向**: ...
```

#### Step 8: 清理

```bash
gdb-cli stop -s <session_id>
```

## 5. 关键约束（必须在 Skill 中强调）

1. **绝不使用 `gdb-cli exec`** — 在大型 binary 上 100% SEGFAULT，已废弃
2. **绝不使用 `gdb-cli thread-apply`** — 内部用 gdb.execute()，不稳定。用 `threads` + `bt --thread N` 组合替代
3. **Shell 转义** — `$` 符号用单引号包裹，寄存器查看用 `registers` 命令（无需转义）
4. **大文件耐心等待** — 渐进式超时重试（2min → 5min → 10min）
5. **Session 管理** — 调试完毕必须 `gdb-cli stop` 清理资源
6. **gdb-cli 命令详细用法** — 参考 `gdb-cli-reference.md`

## 6. 补充参考文件

`gdb-cli-reference.md` 将包含完整的 22 命令参考，内容来源于 `gdb-cli-usage-for-claude-code.md`，按以下分类组织：

- 会话管理（load, attach, sessions, status, stop, env-check）
- 线程操作（threads, thread-switch）
- 栈帧导航（bt, frame, up, down）
- 变量与表达式（eval-cmd, eval-element, locals-cmd, args, ptype）
- 寄存器与内存（registers, memory）
- 共享库与反汇编（sharedlibs, disasm）
- exec 命令替代速查表

## 7. 文档语言

中文，与 DB 团队内部文档习惯一致。

## 8. 工具依赖

- 通过 `pip install` 安装 gdb-cli，不在 Skill 目录内嵌脚本
- Skill 第一步（Step 0）检测 gdb-cli 是否已安装，未安装时给出安装指令

## 9. 后续迭代方向（非本次范围）

- Live Attach 调试工作流
- DB 高级诊断：sql audit 导出、内存使用量分析、内存布局推导
- 多 core 文件批量分析
- 与 db_gdb 工具集成
