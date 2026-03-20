# Crash Test Program

用于 GDB-CLI E2E 测试的崩溃程序。

## 快速开始

```bash
# 编译
make

# 启用 coredump 并运行
ulimit -c unlimited
./crash_test

# 使用 gdb-cli 加载 coredump
gdb-cli load --binary ./crash_test --core ./core.<pid>
```

## 崩溃类型

| 类型 | 说明 | 命令 |
|------|------|------|
| 1 | NULL 指针解引用（默认） | `./crash_test 1` |
| 2 | 数组越界访问 | `./crash_test 2` |
| 3 | 栈溢出 | `./crash_test 3` |
| 4 | abort() 调用 | `./crash_test 4` |

## 验证 GDB-CLI 功能

### 1. 验证 threads 命令

```bash
gdb-cli threads
```

预期看到 4-5 个线程：
- main 线程
- worker_1, worker_2, worker_3 工作线程
- crash_thread 崩溃线程

### 2. 验证 bt 命令

```bash
gdb-cli bt
```

预期调用栈：
```
#0 access_null_pointer
#1 process_data
#2 crash_thread_func
#3 start_thread
...
```

### 3. 验证 eval 命令

```bash
# 查看全局数据库结构
gdb-cli eval "g_database"

# 查看表信息
gdb-cli eval "g_database.tables[0]"

# 查看列信息
gdb-cli eval "g_database.tables[0].columns[0]"

# 查看配置
gdb-cli eval "g_database.config"
```

## 数据结构

程序模拟了一个简单的数据库结构：

```
Database
├── name: "test_db"
├── table_count: 2
├── tables[] (指针数组)
│   ├── Table[0] "users"
│   │   ├── columns[]
│   │   │   ├── Column "id" (INT)
│   │   │   ├── Column "name" (VARCHAR)
│   │   │   └── Column "email" (VARCHAR)
│   │   └── row_count: 1000
│   └── Table[1] "orders"
│       ├── columns[]
│       │   ├── Column "order_id" (INT)
│       │   ├── Column "user_id" (INT)
│       │   ├── Column "amount" (INT)
│       │   └── Column "created_at" (INT)
│       └── row_count: 5000
└── config
    ├── max_connections: 100
    ├── timeout_ms: 30000
    └── debug_level: 2
```

## 文件结构

```
tests/crash_test/
├── crash_test.c          # 源代码
├── crash_test_design.md  # 设计文档
├── Makefile              # 编译脚本
└── README.md             # 本文件
```

## 注意事项

1. 确保 `ulimit -c unlimited` 已设置，否则不会生成 coredump
2. coredump 文件位置取决于系统配置：
   - 通常在当前目录 `./core` 或 `./core.<pid>`
   - 或在 `/var/crash/` (需要 root)
   - macOS 在 `/cores/`
3. 编译时使用 `-g` 保留调试符号，`-O0` 禁用优化