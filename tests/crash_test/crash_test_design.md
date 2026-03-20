# 崩溃测试程序设计文档

## 1. 设计目标

设计一个能产生 coredump 的 C/C++ 测试程序，用于验证 gdb-cli 的核心功能：
- `gdb-cli threads` — 多线程支持
- `gdb-cli bt` — 调用栈追踪
- `gdb-cli eval` — 表达式求值和数据结构遍历

## 2. 程序架构

```
┌─────────────────────────────────────────────────────────────┐
│  crash_test (main)                                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  全局数据结构 (便于 eval 验证)                        │   │
│  │                                                      │   │
│  │  struct Database {                                   │   │
│  │      char name[64];                                  │   │
│  │      int table_count;                                │   │
│  │      Table* tables;        // 动态数组指针            │   │
│  │      Config config;        // 嵌套结构体              │   │
│  │  };                                                  │   │
│  │                                                      │   │
│  │  struct Table {                                      │   │
│  │      char name[32];                                  │   │
│  │      int row_count;                                  │   │
│  │      Column* columns;      // 指针数组                │   │
│  │  };                                                  │   │
│  │                                                      │   │
│  │  struct Column {                                     │   │
│  │      char name[32];                                  │   │
│  │      int type;                                       │   │
│  │      int length;                                     │   │
│  │  };                                                  │   │
│  │                                                      │   │
│  │  struct Config {                                     │   │
│  │      int max_connections;                            │   │
│  │      int timeout_ms;                                 │   │
│  │      char log_path[128];                             │   │
│  │  };                                                  │   │
│  │                                                      │   │
│  │  全局实例: g_database                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  线程模型 (便于 threads 验证)                         │   │
│  │                                                      │   │
│  │  Thread 1 (main):        - 主线程，等待子线程         │   │
│  │  Thread 2 (worker_1):     - 工作线程，执行任务        │   │
│  │  Thread 3 (worker_2):     - 工作线程，执行任务        │   │
│  │  Thread 4 (crash_thread): - 触发崩溃的线程            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  调用栈设计 (便于 bt 验证)                            │   │
│  │                                                      │   │
│  │  main()                                              │   │
│  │    └─> run_test()                                    │   │
│  │          └─> start_workers()                         │   │
│  │                └─> worker_thread() [crash_thread]     │   │
│  │                      └─> process_data()               │   │
│  │                            └─> access_null_pointer()  │   │
│  │                                  └─> SEGFAULT         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 3. 核心代码框架

### 3.1 数据结构定义

```c
// crash_test.c

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>

// ==================== 数据结构定义 ====================

typedef struct Column {
    char name[32];
    int type;           // 0=INT, 1=VARCHAR, 2=TEXT
    int length;
} Column;

typedef struct Table {
    char name[32];
    int row_count;
    int column_count;
    Column* columns;    // 动态分配的列数组
} Table;

typedef struct Config {
    int max_connections;
    int timeout_ms;
    char log_path[128];
    int debug_level;
} Config;

typedef struct Database {
    char name[64];
    int table_count;
    Table* tables;      // 动态分配的表数组
    Config config;
    int is_running;
} Database;

// 全局数据库实例
Database g_database;

// 线程参数
typedef struct ThreadArg {
    int thread_id;
    char name[16];
    int iterations;
} ThreadArg;
```

### 3.2 线程函数

```c
// ==================== 辅助函数 ====================

void init_database() {
    strcpy(g_database.name, "test_db");
    g_database.table_count = 2;
    g_database.tables = (Table*)malloc(sizeof(Table) * 2);
    g_database.is_running = 1;

    // 初始化第一个表
    strcpy(g_database.tables[0].name, "users");
    g_database.tables[0].row_count = 1000;
    g_database.tables[0].column_count = 3;
    g_database.tables[0].columns = (Column*)malloc(sizeof(Column) * 3);

    strcpy(g_database.tables[0].columns[0].name, "id");
    g_database.tables[0].columns[0].type = 0;  // INT
    g_database.tables[0].columns[0].length = 4;

    strcpy(g_database.tables[0].columns[1].name, "name");
    g_database.tables[0].columns[1].type = 1;  // VARCHAR
    g_database.tables[0].columns[1].length = 64;

    strcpy(g_database.tables[0].columns[2].name, "email");
    g_database.tables[0].columns[2].type = 1;  // VARCHAR
    g_database.tables[0].columns[2].length = 128;

    // 初始化第二个表
    strcpy(g_database.tables[1].name, "orders");
    g_database.tables[1].row_count = 5000;
    g_database.tables[1].column_count = 2;
    g_database.tables[1].columns = (Column*)malloc(sizeof(Column) * 2);

    strcpy(g_database.tables[1].columns[0].name, "order_id");
    g_database.tables[1].columns[0].type = 0;
    g_database.tables[1].columns[0].length = 8;

    strcpy(g_database.tables[1].columns[1].name, "amount");
    g_database.tables[1].columns[1].type = 0;
    g_database.tables[1].columns[1].length = 8;

    // 初始化配置
    g_database.config.max_connections = 100;
    g_database.config.timeout_ms = 30000;
    strcpy(g_database.config.log_path, "/var/log/test_db.log");
    g_database.config.debug_level = 2;
}

// ==================== 崩溃触发函数 ====================

// 触发 segmentation fault 的函数
void access_null_pointer(int* ptr) {
    // 故意解引用空指针
    printf("Accessing null pointer...\n");
    *ptr = 42;  // 如果 ptr == NULL，触发 SEGFAULT
}

void process_data(int crash_type) {
    printf("Processing data, crash_type=%d\n", crash_type);

    switch (crash_type) {
        case 1:  // 空指针解引用
            access_null_pointer(NULL);
            break;
        case 2:  // 数组越界写入（可选）
            {
                int arr[10];
                arr[100000] = 123;  // 越界访问
            }
            break;
        default:
            access_null_pointer(NULL);
            break;
    }
}

// ==================== 线程函数 ====================

void* worker_thread(void* arg) {
    ThreadArg* t_arg = (ThreadArg*)arg;
    printf("[Thread %d] %s started\n", t_arg->thread_id, t_arg->name);

    for (int i = 0; i < t_arg->iterations && g_database.is_running; i++) {
        printf("[Thread %d] iteration %d\n", t_arg->thread_id, i);
        sleep(1);
    }

    printf("[Thread %d] %s finished\n", t_arg->thread_id, t_arg->name);
    return NULL;
}

void* crash_thread_func(void* arg) {
    ThreadArg* t_arg = (ThreadArg*)arg;
    printf("[Thread %d] CRASH_THREAD started\n", t_arg->thread_id);

    sleep(1);  // 等待其他线程启动

    // 触发崩溃
    process_data(1);  // 1 = 空指针解引用

    return NULL;
}

// ==================== 主函数 ====================

void start_workers(int crash_type) {
    pthread_t threads[4];
    ThreadArg args[4];

    // 创建工作线程
    for (int i = 0; i < 3; i++) {
        args[i].thread_id = i + 1;
        snprintf(args[i].name, sizeof(args[i].name), "worker_%d", i);
        args[i].iterations = 10;
        pthread_create(&threads[i], NULL, worker_thread, &args[i]);
    }

    // 创建崩溃线程
    args[3].thread_id = 4;
    strcpy(args[3].name, "crash_thread");
    args[3].iterations = 1;
    pthread_create(&threads[3], NULL, crash_thread_func, &args[3]);

    // 等待线程（实际上会因崩溃而中断）
    for (int i = 0; i < 4; i++) {
        pthread_join(threads[i], NULL);
    }
}

void run_test(int crash_type) {
    printf("=== Crash Test Program ===\n");
    printf("Database: %s\n", g_database.name);
    printf("Tables: %d\n", g_database.table_count);
    printf("Crash type: %d\n", crash_type);
    printf("==========================\n\n");

    start_workers(crash_type);
}

int main(int argc, char* argv[]) {
    int crash_type = 1;  // 默认空指针解引用

    if (argc > 1) {
        crash_type = atoi(argv[1]);
    }

    // 初始化数据库
    init_database();

    // 运行测试
    run_test(crash_type);

    // 清理（不会执行到）
    free(g_database.tables[0].columns);
    free(g_database.tables[1].columns);
    free(g_database.tables);

    return 0;
}
```

## 4. 编译与运行

### 4.1 编译命令

```bash
# 编译带调试符号的程序
gcc -g -O0 -o crash_test crash_test.c -lpthread

# 或者使用 g++
g++ -g -O0 -o crash_test crash_test.c -lpthread
```

### 4.2 生成 Coredump

```bash
# 启用 coredump
ulimit -c unlimited

# 运行程序（将崩溃）
./crash_test

# coredump 文件通常生成在：
# - ./core 或 ./core.<pid>
# - /var/crash/ 或 /cores/ (macOS)
```

### 4.3 验证 Coredump

```bash
# 使用 gdb 加载 coredump
gdb ./crash_test core.<pid>

# 在 gdb 中执行：
(gdb) bt              # 查看 backtrace
(gdb) info threads    # 查看线程
(gdb) print g_database # 查看全局变量
```

## 5. E2E 测试验证点

### 5.1 threads 命令验证

```bash
gdb-cli load --binary ./crash_test --core ./core.<pid>
gdb-cli threads
```

**预期输出**:
```json
{
  "threads": [
    {"id": 1, "name": "main", "state": "stopped", "frame": {...}},
    {"id": 2, "name": "worker_1", "state": "stopped", "frame": {...}},
    {"id": 3, "name": "worker_2", "state": "stopped", "frame": {...}},
    {"id": 4, "name": "crash_thread", "state": "stopped", "frame": {...}}
  ],
  "total_count": 4,
  "current_thread": {"id": 4, "name": "crash_thread"}
}
```

### 5.2 bt 命令验证

```bash
gdb-cli bt
```

**预期输出**:
```json
{
  "frames": [
    {"number": 0, "function": "access_null_pointer", "file": "crash_test.c", "line": 80},
    {"number": 1, "function": "process_data", "file": "crash_test.c", "line": 92},
    {"number": 2, "function": "crash_thread_func", "file": "crash_test.c", "line": 115},
    {"number": 3, "function": "start_thread", "file": "pthread_create.c", ...},
    ...
  ],
  "total_count": 6,
  "truncated": false
}
```

### 5.3 eval 命令验证

```bash
# 验证全局变量
gdb-cli eval "g_database"

# 验证数组访问
gdb-cli eval "g_database.tables[0]"

# 验证指针解引用
gdb-cli eval "g_database.tables[0].columns[1]"

# 验证嵌套结构
gdb-cli eval "g_database.config"
```

**预期输出**:
```json
{
  "expression": "g_database",
  "type": "Database",
  "value": {
    "name": "test_db",
    "table_count": 2,
    "tables": {"type": "pointer", "address": "0x..."},
    "config": {
      "max_connections": 100,
      "timeout_ms": 30000,
      "log_path": "/var/log/test_db.log",
      "debug_level": 2
    },
    "is_running": 1
  }
}
```

## 6. 扩展设计（可选）

### 6.1 多种崩溃类型

可通过命令行参数选择不同的崩溃方式：
- `./crash_test 1` — 空指针解引用（默认）
- `./crash_test 2` — 数组越界
- `./crash_test 3` — 栈溢出
- `./crash_test 4` — abort()

### 6.2 更复杂的数据结构

可扩展为模拟数据库场景：
- 哈希表
- B+ 树节点
- 缓冲池
- 锁管理器

## 7. 文件位置

建议将源代码放置于：
```
gdb_cli/
└── tests/
    └── crash_test/
        ├── crash_test.c      # 源代码
        ├── Makefile          # 编译脚本
        └── README.md         # 使用说明
```

---

**设计者**: architect
**日期**: 2026-03-19
**版本**: 1.0