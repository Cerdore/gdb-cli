---
name: db-core-debugging
description: 使用 gdb-cli 工具调试 Database core dump 文件时触发。当用户提到 core dump、coredump、崩溃分析、server 崩溃、段错误、SIGSEGV、SIGABRT、堆栈分析等关键词时使用。
---

# DB Core Debugging Skill

自动化分析 Database core dump 文件的工作流程。

## 核心工作流

### Step 0: 环境检查

```bash
gdb-cli env-check
```

- 若 `gdb-cli` 命令不存在 → 安装：`pip install git+http://gitlab.internal.example.com/tools/gdb_cli.git`
- 核对 GDB 版本：el7/el8 需要 9.0+，el9/Rocky 需要 15+
- 核对 GDB Python 支持：`gdb -batch -ex "python print('ok')"`

### Step 1: 加载 core dump（渐进式超时重试）

大型 DB binary（6.1G+）加载时间不可预测，采用渐进式超时：

```
第 1 次：gdb-cli load -b <binary> -c <core> --timeout 120  （2分钟）
若超时 → 第 2 次：gdb-cli load -b <binary> -c <core> --timeout 300  （5分钟）
若仍超时 → 第 3 次：gdb-cli load -b <binary> -c <core> --timeout 600  （10分钟）
仍失败 → 报错并提示可能原因
```

**加载失败排查：**
- 不要把 server.debug 当二进制用 → 正确用法：`gdb-cli load -b server -c core.xxx`
- debuginfo 缺失 → 把 server.debug 文件 copy 到 server 二进制同一目录下
- 二进制不匹配 → 确认 arm/x86 架构一致、版本完全匹配
- 跨机器动态库问题 → 使用 `--sysroot` 或 `--solib-prefix` 参数
- GDB 版本问题 → 使用 `--gdb-path` 指定正确版本
- core 文件不完整 → 检查磁盘空间，对比进程内存占用

### Step 2: 状态概览

```bash
gdb-cli status -s <session_id>
```

确认：模式（core）、binary 路径、线程数、当前帧信息。

### Step 3: 崩溃线程定位

```bash
gdb-cli threads -s <SID> --limit 50
```

找到信号线程（通常是 thread 1，收到 SIGSEGV/SIGABRT）。

### Step 4: 堆栈分析

```bash
gdb-cli bt -s <SID> --thread <crash_thread> --limit 30
```

从崩溃帧（frame 0）向上遍历调用链，识别关键函数。

### Step 4.5: 源码关联分析（可选）

如果 `bt` 输出包含源文件信息：
1. 尝试在本地工作目录查找对应源码文件
2. 使用 Read 工具读取崩溃位置前后 20 行代码
3. 结合代码逻辑理解崩溃上下文

### Step 5: 变量与上下文检查

```bash
# 崩溃帧的函数参数
gdb-cli args -s <SID> --thread <crash_thread> --frame 0

# 崩溃帧的局部变量
gdb-cli locals-cmd -s <SID> --thread <crash_thread> --frame 0

# 深入查看关键变量（需先切换上下文）
gdb-cli thread-switch -s <SID> <crash_thread>
gdb-cli frame -s <SID> 0
gdb-cli eval-cmd -s <SID> "this->member_name_"
gdb-cli eval-cmd -s <SID> "*ptr"
```

### Step 6: 深入诊断

根据崩溃类型选择诊断手段：

| 崩溃类型 | 诊断命令 |
|---------|---------|
| 空指针解引用 | `eval-cmd` 检查指针值，`ptype` 查看类型 |
| 内存越界 | `memory` 检查周边内存，`registers` 查看地址寄存器 |
| 非法指令 | `disasm` 查看崩溃点汇编，`registers` 查看 rip |
| 栈溢出 | `registers` 查看 rsp，`memory` 检查栈边界 |
| 断言失败 | `eval-cmd` 查看断言条件中的变量值 |

### Step 7: 根因推断 + 输出结论

输出结构化诊断报告：

```markdown
## Core Dump 诊断报告
- **崩溃信号**: SIGSEGV / SIGABRT / ...
- **崩溃线程**: Thread N
- **崩溃位置**: function() at file:line
- **调用链关键路径**: ...
- **关键变量值**: ...
- **根因推断**: ...
- **建议修复方向**: ...
```

### Step 8: 清理

```bash
gdb-cli stop -s <session_id>
```

## 关键约束（必须遵循）

1. **绝不使用 `gdb-cli exec`** — 在大型 binary 上 100% SEGFAULT，已废弃
2. **绝不使用 `gdb-cli thread-apply`** — 内部用 gdb.execute()，不稳定。用 `threads` + `bt --thread N` 组合替代
3. **Shell 转义** — `$` 符号用单引号包裹，寄存器查看用 `registers` 命令（无需转义）
4. **大文件耐心等待** — 渐进式超时重试（2min → 5min → 10min）
5. **Session 管理** — 调试完毕必须 `gdb-cli stop` 清理资源

## 命令详细用法

参考 `gdb-cli-reference.md` 获取完整 22 命令说明。
