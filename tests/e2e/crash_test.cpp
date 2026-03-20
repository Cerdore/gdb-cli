// Crash test program for E2E testing of GDB CLI
// Generates a coredump with various data structures for testing

#include <iostream>
#include <vector>
#include <string>
#include <thread>
#include <unistd.h>
#include <cstring>

// Simple data structure for testing eval command
struct Config {
    int id;
    char name[64];
    double value;
    bool enabled;
};

// Nested structure for testing deep inspection
struct Node {
    int data;
    Node* next;
};

// Global variables for testing global symbol access
int g_counter = 42;
std::string g_version = "1.0.0-test";
Config g_config = {100, "test_config", 3.14159, true};

// Function that causes segmentation fault
void cause_segfault() {
    int* ptr = nullptr;
    *ptr = 123;  // Crash here
}

// Function with local variables for testing locals command
void function_with_locals(int arg1, const char* arg2) {
    int local_int = 999;
    char local_buf[128];
    std::string local_str = "hello from crash_test";

    strncpy(local_buf, arg2, sizeof(local_buf) - 1);
    local_buf[sizeof(local_buf) - 1] = '\0';

    std::cout << "Before crash: local_int=" << local_int
              << ", local_str=" << local_str << std::endl;

    // Trigger the crash
    cause_segfault();
}

// Worker thread function
void worker_thread(int thread_id) {
    std::vector<int> thread_data;
    for (int i = 0; i < 10; i++) {
        thread_data.push_back(thread_id * 100 + i);
    }

    std::cout << "Thread " << thread_id << " started" << std::endl;

    // Thread 0 will trigger the crash
    if (thread_id == 0) {
        function_with_locals(thread_id, "crash_trigger");
    }

    // Other threads sleep
    sleep(10);
}

int main(int argc, char* argv[]) {
    std::cout << "Crash Test Program Started" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;

    // Create a linked list for testing pointer inspection
    Node* head = new Node{1, nullptr};
    head->next = new Node{2, nullptr};
    head->next->next = new Node{3, nullptr};

    // Spawn multiple threads to test thread listing
    std::vector<std::thread> threads;
    for (int i = 0; i < 3; i++) {
        threads.emplace_back(worker_thread, i);
    }

    // Wait for threads (won't reach here due to crash)
    for (auto& t : threads) {
        t.join();
    }

    // Cleanup (won't reach here)
    Node* current = head;
    while (current) {
        Node* next = current->next;
        delete current;
        current = next;
    }

    return 0;
}
