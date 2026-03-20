/*
 * Crash Test Program for GDB-CLI E2E Testing
 *
 * 用于生成 coredump 的测试程序，验证 gdb-cli 的核心功能：
 * - threads: 多线程支持
 * - bt: 调用栈追踪
 * - eval: 表达式求值和数据结构遍历
 *
 * 编译: gcc -g -O0 -o crash_test crash_test.c -lpthread
 * 运行: ulimit -c unlimited && ./crash_test
 *
 * Author: architect
 * Date: 2026-03-19
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <signal.h>

/* ==================== 数据结构定义 ==================== */

/**
 * 列定义 - 模拟数据库表的列
 */
typedef struct Column {
    char name[32];
    int type;           /* 0=INT, 1=VARCHAR, 2=TEXT */
    int length;
    int is_nullable;
} Column;

/**
 * 表定义 - 模拟数据库表
 */
typedef struct Table {
    char name[32];
    int row_count;
    int column_count;
    Column* columns;    /* 动态分配的列数组 */
} Table;

/**
 * 配置结构 - 模拟数据库配置
 */
typedef struct Config {
    int max_connections;
    int timeout_ms;
    char log_path[128];
    int debug_level;
    int enable_ssl;
} Config;

/**
 * 数据库结构 - 模拟数据库实例
 */
typedef struct Database {
    char name[64];
    int table_count;
    Table* tables;      /* 动态分配的表数组 */
    Config config;
    int is_running;
    int connection_count;
} Database;

/**
 * 线程参数结构
 */
typedef struct ThreadArg {
    int thread_id;
    char name[16];
    int iterations;
    int delay_ms;
} ThreadArg;

/* ==================== 全局变量 ==================== */

/* 全局数据库实例 - 用于 eval 验证 */
Database g_database;

/* 线程控制 */
pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;
int g_should_stop = 0;

/* ==================== 辅助函数 ==================== */

/**
 * 初始化数据库结构
 */
void init_database(void) {
    strcpy(g_database.name, "test_db");
    g_database.table_count = 2;
    g_database.tables = (Table*)malloc(sizeof(Table) * 2);
    g_database.is_running = 1;
    g_database.connection_count = 0;

    if (!g_database.tables) {
        fprintf(stderr, "Failed to allocate tables\n");
        exit(1);
    }

    /* 初始化第一个表: users */
    Table* users = &g_database.tables[0];
    strcpy(users->name, "users");
    users->row_count = 1000;
    users->column_count = 3;
    users->columns = (Column*)malloc(sizeof(Column) * 3);

    if (!users->columns) {
        fprintf(stderr, "Failed to allocate columns for users\n");
        exit(1);
    }

    /* id 列 */
    strcpy(users->columns[0].name, "id");
    users->columns[0].type = 0;  /* INT */
    users->columns[0].length = 4;
    users->columns[0].is_nullable = 0;

    /* name 列 */
    strcpy(users->columns[1].name, "name");
    users->columns[1].type = 1;  /* VARCHAR */
    users->columns[1].length = 64;
    users->columns[1].is_nullable = 0;

    /* email 列 */
    strcpy(users->columns[2].name, "email");
    users->columns[2].type = 1;  /* VARCHAR */
    users->columns[2].length = 128;
    users->columns[2].is_nullable = 1;

    /* 初始化第二个表: orders */
    Table* orders = &g_database.tables[1];
    strcpy(orders->name, "orders");
    orders->row_count = 5000;
    orders->column_count = 4;
    orders->columns = (Column*)malloc(sizeof(Column) * 4);

    if (!orders->columns) {
        fprintf(stderr, "Failed to allocate columns for orders\n");
        exit(1);
    }

    /* order_id 列 */
    strcpy(orders->columns[0].name, "order_id");
    orders->columns[0].type = 0;  /* INT */
    orders->columns[0].length = 8;
    orders->columns[0].is_nullable = 0;

    /* user_id 列 */
    strcpy(orders->columns[1].name, "user_id");
    orders->columns[1].type = 0;  /* INT */
    orders->columns[1].length = 4;
    orders->columns[1].is_nullable = 0;

    /* amount 列 */
    strcpy(orders->columns[2].name, "amount");
    orders->columns[2].type = 0;  /* INT */
    orders->columns[2].length = 8;
    orders->columns[2].is_nullable = 0;

    /* created_at 列 */
    strcpy(orders->columns[3].name, "created_at");
    orders->columns[3].type = 0;  /* INT (timestamp) */
    orders->columns[3].length = 8;
    orders->columns[3].is_nullable = 0;

    /* 初始化配置 */
    g_database.config.max_connections = 100;
    g_database.config.timeout_ms = 30000;
    strcpy(g_database.config.log_path, "/var/log/test_db.log");
    g_database.config.debug_level = 2;
    g_database.config.enable_ssl = 1;
}

/**
 * 打印数据库信息
 */
void print_database_info(void) {
    printf("=== Database Info ===\n");
    printf("Name: %s\n", g_database.name);
    printf("Tables: %d\n", g_database.table_count);
    printf("Connections: %d\n", g_database.connection_count);
    printf("Config:\n");
    printf("  max_connections: %d\n", g_database.config.max_connections);
    printf("  timeout_ms: %d\n", g_database.config.timeout_ms);
    printf("  debug_level: %d\n", g_database.config.debug_level);
    printf("=====================\n\n");
}

/* ==================== 崩溃触发函数 ==================== */

/**
 * 空指针解引用 - 触发 SEGFAULT
 */
void access_null_pointer(int* ptr) {
    printf("[CRASH] Accessing null pointer...\n");
    fflush(stdout);

    /* 故意解引用空指针，触发 SIGSEGV */
    *ptr = 42;
}

/**
 * 数组越界写入 - 触发 SEGFAULT
 */
void array_out_of_bounds(void) {
    printf("[CRASH] Array out of bounds access...\n");
    fflush(stdout);

    int small_array[10];
    /* 故意越界访问 */
    small_array[1000000] = 123;
}

/**
 * 递归栈溢出 - 触发 SIGSEGV
 */
void stack_overflow(int depth) {
    char buffer[1024];
    memset(buffer, 'A', sizeof(buffer));

    if (depth > 0) {
        stack_overflow(depth + 1);
    }
}

/**
 * 处理数据并触发崩溃
 */
void process_data(int crash_type) {
    printf("[CRASH] Processing data, crash_type=%d\n", crash_type);
    fflush(stdout);

    switch (crash_type) {
        case 1:  /* 空指针解引用 */
            access_null_pointer(NULL);
            break;
        case 2:  /* 数组越界 */
            array_out_of_bounds();
            break;
        case 3:  /* 栈溢出 */
            stack_overflow(1);
            break;
        case 4:  /* abort */
            printf("[CRASH] Calling abort()...\n");
            fflush(stdout);
            abort();
            break;
        default:
            access_null_pointer(NULL);
            break;
    }
}

/* ==================== 线程函数 ==================== */

/**
 * 工作线程函数
 */
void* worker_thread(void* arg) {
    ThreadArg* t_arg = (ThreadArg*)arg;

    printf("[Thread %d] %s started\n", t_arg->thread_id, t_arg->name);
    fflush(stdout);

    for (int i = 0; i < t_arg->iterations && !g_should_stop; i++) {
        pthread_mutex_lock(&g_mutex);
        g_database.connection_count++;
        pthread_mutex_unlock(&g_mutex);

        printf("[Thread %d] iteration %d, connections=%d\n",
               t_arg->thread_id, i, g_database.connection_count);
        fflush(stdout);

        usleep(t_arg->delay_ms * 1000);
    }

    printf("[Thread %d] %s finished\n", t_arg->thread_id, t_arg->name);
    fflush(stdout);

    return NULL;
}

/**
 * 崩溃线程函数
 */
void* crash_thread_func(void* arg) {
    ThreadArg* t_arg = (ThreadArg*)arg;

    printf("[Thread %d] crash_thread started, will crash in 1 second...\n",
           t_arg->thread_id);
    fflush(stdout);

    sleep(1);

    /* 触发崩溃 */
    process_data(t_arg->thread_id);

    return NULL;
}

/* ==================== 主流程函数 ==================== */

/**
 * 启动工作线程
 */
void start_workers(int crash_type) {
    pthread_t threads[4];
    ThreadArg args[4];

    printf("[MAIN] Starting worker threads...\n");
    fflush(stdout);

    /* 创建工作线程 1 */
    args[0].thread_id = 1;
    strcpy(args[0].name, "worker_1");
    args[0].iterations = 20;
    args[0].delay_ms = 500;
    pthread_create(&threads[0], NULL, worker_thread, &args[0]);

    /* 创建工作线程 2 */
    args[1].thread_id = 2;
    strcpy(args[1].name, "worker_2");
    args[1].iterations = 20;
    args[1].delay_ms = 700;
    pthread_create(&threads[1], NULL, worker_thread, &args[1]);

    /* 创建工作线程 3 */
    args[2].thread_id = 3;
    strcpy(args[2].name, "worker_3");
    args[2].iterations = 20;
    args[2].delay_ms = 600;
    pthread_create(&threads[2], NULL, worker_thread, &args[2]);

    /* 创建崩溃线程 */
    args[3].thread_id = crash_type;  /* 使用 crash_type 作为标识 */
    strcpy(args[3].name, "crash_thread");
    args[3].iterations = 1;
    args[3].delay_ms = 0;
    pthread_create(&threads[3], NULL, crash_thread_func, &args[3]);

    printf("[MAIN] All threads started, waiting...\n");
    fflush(stdout);

    /* 等待线程（实际上会因崩溃而中断） */
    for (int i = 0; i < 4; i++) {
        pthread_join(threads[i], NULL);
    }
}

/**
 * 运行测试
 */
void run_test(int crash_type) {
    printf("\n");
    printf("========================================\n");
    printf("  Crash Test Program for GDB-CLI E2E\n");
    printf("========================================\n");
    printf("Database: %s\n", g_database.name);
    printf("Tables: %d\n", g_database.table_count);
    printf("Crash type: %d\n", crash_type);
    printf("  1 = NULL pointer dereference\n");
    printf("  2 = Array out of bounds\n");
    printf("  3 = Stack overflow\n");
    printf("  4 = abort()\n");
    printf("========================================\n\n");
    fflush(stdout);

    print_database_info();
    start_workers(crash_type);
}

/**
 * 清理资源
 */
void cleanup(void) {
    if (g_database.tables) {
        for (int i = 0; i < g_database.table_count; i++) {
            if (g_database.tables[i].columns) {
                free(g_database.tables[i].columns);
            }
        }
        free(g_database.tables);
    }
}

/* ==================== 主函数 ==================== */

int main(int argc, char* argv[]) {
    int crash_type = 1;  /* 默认空指针解引用 */

    if (argc > 1) {
        crash_type = atoi(argv[1]);
        if (crash_type < 1 || crash_type > 4) {
            crash_type = 1;
        }
    }

    /* 初始化数据库 */
    init_database();

    /* 运行测试 */
    run_test(crash_type);

    /* 清理（正常情况下不会执行到这里） */
    cleanup();

    return 0;
}