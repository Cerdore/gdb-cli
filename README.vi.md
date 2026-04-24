# GDB CLI cho AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | Tiếng Việt | [Português](README.pt.md) | [Русский](README.ru.md) | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Italiano](README.it.md)

Một công cụ gỡ lỗi GDB được thiết kế cho các Agent AI (Claude Code, v.v.). Sử dụng kiến trúc "CLI client mỏng + GDB embedded Python RPC Server", cho phép gỡ lỗi GDB có trạng thái thông qua Bash.

## Tính năng

- **Phân tích Core Dump**: Tải core dump với symbols nằm trong bộ nhớ để phản hồi trong mili-giây
- **Gỡ lỗi Live Attach**: Attach vào tiến trình đang chạy với chế độ non-stop
- **Đầu ra JSON có cấu trúc**: Tất cả lệnh đều xuất JSON với tự động cắt / phân trang và gợi ý thao tác
- **Cơ chế bảo mật**: Danh sách trắng lệnh, tự động dọn dẹp timeout heartbeat, đảm bảo tính bất khả biến (idempotency)
- **Tối ưu cho cơ sở dữ liệu**: scheduler-locking, pagination cho đối tượng lớn, cắt đa luồng

## Yêu cầu

- **Python**: 3.6.8+
- **GDB**: 9.0+ với **Python support enabled**
- **Hệ điều hành**: Linux

### Kiểm tra Python Support của GDB

```bash
# Kiểm tra xem GDB có hỗ trợ Python không
gdb -nx -q -batch -ex "python print('OK')"

# Nếu GDB hệ thống thiếu Python, kiểm tra GCC Toolset (RHEL/CentOS)
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Cài đặt

```bash
# Cài đặt từ PyPI
pip install gdb-cli

# Hoặc cài đặt từ GitHub
pip install git+https://github.com/Cerdore/gdb-cli.git

# Hoặc clone và cài đặt locally
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# Kiểm tra môi trường
gdb-cli env-check
```

## Bắt đầu nhanh

### 1. Tải Core Dump

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Đầu ra:
```json
{
  "session_id": "f465d650",
  "mode": "core",
  "binary": "./my_program",
  "core": "./core.12345",
  "gdb_pid": 12345,
  "status": "loading"
}
```

Khi tải hoặc tệp nhị phân hoặc core lớn, poll cho đến khi phiên sẵn sàng:

```bash
gdb-cli status -s f465d650
```

```json
{
  "session_id": "f465d650",
  "state": "ready",
  "mode": "core",
  "binary": "./my_program"
}
```

> Nếu GDB mặc định của hệ thống không có hỗ trợ Python, hãy chỉ định bằng `--gdb-path`:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Thao tác gỡ lỗi

Tất cả thao tác đều sử dụng `--session` / `-s` để chỉ định ID phiên:

```bash
SESSION="f465d650"

# Liệt kê các luồng
gdb-cli threads -s $SESSION

# Lấy backtrace (mặc định: luồng hiện tại)
gdb-cli bt -s $SESSION

# Lấy backtrace cho luồng cụ thể
gdb-cli bt -s $SESSION --thread 3

# Đánh giá biểu thức C/C++
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Truy cập phần tử mảng
gdb-cli eval-element -s $SESSION "my_array" --index 5

# Xem biến cục bộ
gdb-cli locals-cmd -s $SESSION

# Thực thi lệnh GDB thô
gdb-cli exec -s $SESSION "info registers"

# Kiểm tra trạng thái phiên
gdb-cli status -s $SESSION
```

### 3. Quản lý phiên

```bash
# Liệt kê tất cả phiên đang hoạt động
gdb-cli sessions

# Dừng phiên
gdb-cli stop -s $SESSION
```

### 4. Gỡ lỗi Live Attach

```bash
# Attach vào tiến trình đang chạy (mặc định: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Attach với tệp symbol
gdb-cli attach --pid 9876 --binary ./my_program

# Cho phép sửa đổi bộ nhớ và gọi hàm
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Tham chiếu đầy đủ các lệnh

### load — Tải Core Dump

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      Đường dẫn tệp thực thi (bắt buộc)
  --core, -c        Đường dẫn tệp core dump (bắt buộc)
  --sysroot         Đường dẫn sysroot (cho gỡ lỗi giữa máy)
  --solib-prefix    Tiền tố thư viện chia sẻ
  --source-dir      Thư mục mã nguồn
  --timeout         Timeout heartbeat tính bằng giây (mặc định: 600)
  --gdb-path        Đường dẫn thực thi GDB (mặc định: "gdb")
```

`load` trả về ngay lập tức với `"status": "loading"` sau khi RPC server có thể tiếp cận. Sử dụng `gdb-cli status -s <session>` và đợi cho `"state": "ready"` trước khi thực hiện lệnh kiểm tra nặng.

### attach — Attach vào Tiến trình

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               PID tiến trình (bắt buộc)
  --binary                Đường dẫn tệp thực thi (tùy chọn)
  --scheduler-locking     Bật scheduler-locking (mặc định: true)
  --non-stop              Bật chế độ non-stop (mặc định: true)
  --timeout               Timeout heartbeat tính bằng giây (mặc định: 600)
  --allow-write           Cho phép sửa đổi bộ nhớ
  --allow-call            Cho phép gọi hàm
```

### threads — Liệt kê Luồng

```
gdb-cli threads -s <session> [options]

  --range           Phạm vi luồng, ví dụ: "3-10"
  --limit           Số lượng trả về tối đa (mặc định: 20)
  --filter-state    Lọc theo trạng thái ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      Chỉ định ID luồng
  --limit           Số khung tối đa (mặc định: 30)
  --full            Bao gồm biến cục bộ
  --range           Phạm vi khung, ví dụ: "5-15"
```

### eval-cmd — Đánh giá Biểu thức

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Giới hạn độ sâu đệ quy (mặc định: 3)
  --max-elements    Giới hạn phần tử mảng (mặc định: 50)
```

### eval-element — Truy cập Phần tử Mảng/Container

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Thực thi Lệnh GDB Thô

```
gdb-cli exec -s <session> <command>

  --safety-level    Mức độ an toàn (readonly / readwrite / full)
```

### thread-apply — Thao tác Luồng Hàng loạt

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Ví dụ đầu ra

### threads

```json
{
  "threads": [
    {"id": 1, "global_id": 1, "state": "stopped"},
    {"id": 2, "global_id": 2, "state": "stopped"}
  ],
  "total_count": 5,
  "truncated": true,
  "current_thread": {"id": 1, "global_id": 1, "state": "stopped"},
  "hint": "use 'threads --range START-END' for specific threads"
}
```

### eval-cmd

```json
{
  "expression": "(int)5+3",
  "value": 8,
  "type": "int",
  "size": 4
}
```

### bt

```json
{
  "frames": [
    {"number": 0, "function": "crash_thread", "address": "0x400a1c", "file": "test.c", "line": 42},
    {"number": 1, "function": "start_thread", "address": "0x7f3fa2e13fa"}
  ],
  "total_count": 2,
  "truncated": false
}
```

## Cơ chế bảo mật

### Danh sách trắng lệnh (Chế độ Attach)

| Mức độ an toàn | Lệnh được phép |
|--------------|------------------|
| `readonly` (mặc định) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` luôn bị chặn.

### Timeout Heartbeat

Tự động detach và thoát sau 10 phút không hoạt động theo mặc định. Có thể cấu hình qua `--timeout`.

### Tính bất khả biến (Idempotency)

Chỉ cho phép một phiên cho mỗi PID / Tệp Core. Tải/attach lặp lại trả về `session_id` hiện có.

## Gỡ lỗi Core Dump giữa các máy

Khi phân tích core dump từ các máy khác, đường dẫn thư viện chia sẻ có thể khác nhau:

```bash
# Đặt sysroot (thay thế tiền tố đường dẫn)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Đặt thư mục mã nguồn (cho gỡ lỗi ở mức nguồn)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Phát triển

### Cấu trúc dự án

```
src/gdb_cli/
├── cli.py              # Điểm vào CLI (Click)
├── client.py           # Client Unix Socket
├── launcher.py         # Khởi chạy tiến trình GDB
├── session.py          # Quản lý metadata phiên
├── safety.py           # Bộ lọc danh sách trắng lệnh
├── formatters.py       # Định dạng đầu ra JSON
├── env_check.py        # Kiểm tra môi trường
├── errors.py           # Phân loại lỗi
└── gdb_server/
    ├── gdb_rpc_server.py   # Lõi RPC Server
    ├── handlers.py         # Bộ xử lý lệnh
    ├── value_formatter.py  # Serialization gdb.Value
    └── heartbeat.py         # Quản lý timeout heartbeat

skills/
└── gdb-cli/               # Kỹ năng Claude Code cho gỡ lỗi thông minh
    ├── SKILL.md            # Định nghĩa kỹ năng
    └── evals/              # Các trường hợp thử cho đánh giá kỹ năng
```

### Chạy thử

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Kết thúc đến kết thúc (End-to-End Testing)

Yêu cầu GDB có hỗ trợ Python. Sử dụng chương trình kiểm tra lỗi trong `tests/crash_test/`:

```bash
# Biên dịch chương trình kiểm tra
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Tạo coredump
ulimit -c unlimited
./crash_test  # Sẽ SIGSEGV

# Tìm tệp core
ls /path/to/core_dumps/core-crash_test-*

# Chạy kiểm tra E2E
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Hạn chế đã biết

- Không hỗ trợ `target remote` (sử dụng SSH cho gỡ lỗi từ xa, xem bên dưới)
- Không hỗ trợ gỡ lỗi đa superior
- Pretty printers Guile của GDB 12.x không an toàn cho đa luồng, giải pháp thông qua `format_string(raw=True)`
- Phiên bản Python nhúng của GDB có thể cũ hơn (ví dụ: 3.6.8), mã có xử lý tương thích

## Gỡ lỗi từ xa qua SSH

Cài đặt và chạy trên máy từ xa trong một lệnh:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

Hoặc cài đặt trước, sau đó gỡ lỗi:

```bash
# Cài đặt trên máy từ xa
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Chạy gỡ lỗi
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Kỹ năng Claude Code

Dự án này bao gồm một kỹ năng **gdb-cli** cho Claude Code cung cấp hỗ trợ gỡ lỗi thông minh bằng cách kết hợp phân tích mã nguồn với kiểm tra trạng thái thời gian chạy.

### Cài đặt Kỹ năng

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Sử dụng trong Claude Code

```
/gdb-cli

# Hoặc mô tả nhu cầu gỡ lỗi của bạn:
Tôi có một core dump tại ./core.1234 và binary tại ./myapp. Hãy giúp tôi gỡ lỗi nó.
```

### Tính năng

- **Tương quan Mã nguồn**: Tự động đọc các tệp mã nguồn xung quanh điểm lỗi
- **Phát hiện Deadlock**: Xác định các mẫu chờ đợi vòng tròn trong chương trình đa luồng
- **Cảnh báo An toàn**: Thông báo về rủi ro môi trường sản xuất khi attach vào tiến trình đang chạy
- **Báo cáo có cấu trúc**: Tạo phân tích với giả thuyết nguyên nhân gốc rễ và các bước tiếp theo

Xem [skills/README.md](skills/README.md) để biết thêm chi tiết.

## Giấy phép

Apache License 2.0
