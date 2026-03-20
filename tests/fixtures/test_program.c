// 简单测试程序用于冒烟测试
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int id;
    char name[32];
    double value;
} Item;

int main() {
    Item items[3] = {
        {1, "first", 1.0},
        {2, "second", 2.0},
        {3, "third", 3.0}
    };

    int sum = 0;
    for (int i = 0; i < 3; i++) {
        sum += items[i].id;
        printf("Item %d: %s, value=%.2f\n",
               items[i].id, items[i].name, items[i].value);
    }

    // 触发 core dump (调试时使用)
    // raise(SIGABRT);

    printf("Sum: %d\n", sum);
    return 0;
}