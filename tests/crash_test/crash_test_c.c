/*
 * crash_test.c - 纯 C 版本崩溃测试程序
 * 用于 GDB CLI 端到端测试
 *
 * 编译: gcc -g -O0 -o crash_test crash_test.c -lpthread
 * 运行: ulimit -c unlimited && ./crash_test
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>

/* 数据结构定义 - 用于验证 gdb-cli eval 功能 */

struct Column {
    char name[64];
    char type[32];
    int length;
};

struct Table {
    char name[64];
    int row_count;
    struct Column columns[10];
    int column_count;
};

struct Config {
    int max_connections;
    int timeout_ms;
    int buffer_size;
    int log_level;
};

struct Database {
    char name[64];
    struct Table tables[5];
    int table_count;
    struct Config config;
};

/* 全局数据库实例 */
struct Database g_database;

/* 初始化测试数据 */
void init_test_data(void) {
    strcpy(g_database.name, "test_db");
    g_database.table_count = 2;

    /* 表 1: users */
    strcpy(g_database.tables[0].name, "users");
    g_database.tables[0].row_count = 1000;
    g_database.tables[0].column_count = 3;

    strcpy(g_database.tables[0].columns[0].name, "id");
    strcpy(g_database.tables[0].columns[0].type, "INT");
    g_database.tables[0].columns[0].length = 4;

    strcpy(g_database.tables[0].columns[1].name, "name");
    strcpy(g_database.tables[0].columns[1].type, "VARCHAR");
    g_database.tables[0].columns[1].length = 255;

    strcpy(g_database.tables[0].columns[2].name, "email");
    strcpy(g_database.tables[0].columns[2].type, "VARCHAR");
    g_database.tables[0].columns[2].length = 128;

    /* 表 2: orders */
    strcpy(g_database.tables[1].name, "orders");
    g_database.tables[1].row_count = 5000;
    g_database.tables[1].column_count = 2;

    strcpy(g_database.tables[1].columns[0].name, "order_id");
    strcpy(g_database.tables[1].columns[0].type, "BIGINT");
    g_database.tables[1].columns[0].length = 8;

    strcpy(g_database.tables[1].columns[1].name, "user_id");
    strcpy(g_database.tables[1].columns[1].type, "INT");
    g_database.tables[1].columns[1].length = 4;

    /* 配置 */
    g_database.config.max_connections = 100;
    g_database.config.timeout_ms = 30000;
    g_database.config.buffer_size = 4096;
    g_database.config.log_level = 2;
}

/* 线程函数 */
void* worker_thread(void* arg) {
    int id = *(int*)arg;
    printf("Worker thread %d started\n", id);
    while (1) {
        sleep(1);
    }
    return NULL;
}

/* 崩溃函数 - NULL 指针解引用 */
void access_null_pointer(void) {
    int* ptr = NULL;
    printf("About to access NULL pointer...\n");
    *ptr = 42;  /* 这里会触发 SIGSEGV */
}

/* 处理数据函数 */
void process_data(int value) {
    printf("Processing data: %d\n", value);
    access_null_pointer();
}

/* 崩溃线程函数 */
void* crash_thread(void* arg) {
    printf("Crash thread started\n");
    sleep(1);
    process_data(12345);
    return NULL;
}

int main(int argc, char* argv[]) {
    pthread_t workers[3];
    pthread_t crash_thr;
    int worker_ids[3] = {1, 2, 3};
    int i;

    printf("=== GDB CLI E2E Test Program ===\n");
    printf("PID: %d\n", getpid());

    /* 初始化测试数据 */
    init_test_data();
    printf("Database: %s\n", g_database.name);
    printf("Tables: %d\n", g_database.table_count);

    /* 创建工作线程 */
    for (i = 0; i < 3; i++) {
        pthread_create(&workers[i], NULL, worker_thread, &worker_ids[i]);
    }

    /* 创建崩溃线程 */
    pthread_create(&crash_thr, NULL, crash_thread, NULL);

    printf("Waiting for crash...\n");

    /* 等待崩溃线程 */
    pthread_join(crash_thr, NULL);

    /* 不会执行到这里 */
    for (i = 0; i < 3; i++) {
        pthread_join(workers[i], NULL);
    }

    return 0;
}