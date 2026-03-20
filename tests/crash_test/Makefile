# Makefile for Crash Test Program
# 用于 GDB-CLI E2E 测试的崩溃程序

CC = gcc
CFLAGS = -g -O0 -Wall -Wextra -pthread
LDFLAGS = -lpthread

TARGET = crash_test
SRC = crash_test.c

.PHONY: all clean run clean-core help

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC) $(LDFLAGS)
	@echo ""
	@echo "Build complete: $(TARGET)"
	@echo "Usage: ./$(TARGET) [crash_type]"
	@echo "  crash_type: 1=NULL pointer, 2=array OOB, 3=stack overflow, 4=abort"

clean:
	rm -f $(TARGET) core core.* vgcore.*

run: $(TARGET)
	ulimit -c unlimited && ./$(TARGET)

clean-core:
	rm -f core core.*

help:
	@echo "Crash Test Program for GDB-CLI E2E Testing"
	@echo ""
	@echo "Targets:"
	@echo "  all        - Build the crash test program (default)"
	@echo "  clean      - Remove built files"
	@echo "  run        - Build and run with coredump enabled"
	@echo "  clean-core - Remove coredump files"
	@echo "  help       - Show this help message"
	@echo ""
	@echo "Crash Types:"
	@echo "  1 - NULL pointer dereference (default)"
	@echo "  2 - Array out of bounds"
	@echo "  3 - Stack overflow"
	@echo "  4 - abort()"
	@echo ""
	@echo "Examples:"
	@echo "  make              # Build"
	@echo "  make run          # Run with default crash type"
	@echo "  ./crash_test 2    # Run with array OOB crash"