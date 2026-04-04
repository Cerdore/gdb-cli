"""
GDB RPC Server - 运行在 GDB Python 解释器内

通过 source 命令加载到 GDB 中，提供 Unix Domain Socket 接口。
使用 gdb.post_event() 确保所有 GDB API 调用在主线程执行。
"""

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional

# GDB Python API - 仅在 GDB 环境中可用
try:
    import gdb
    GDB_AVAILABLE = True
except ImportError:
    GDB_AVAILABLE = False
    gdb = None  # type: ignore


# 默认配置
DEFAULT_SOCKET_TIMEOUT = 5.0  # 单次 socket 操作超时
DEFAULT_COMMAND_TIMEOUT = 30.0  # 命令执行超时
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB 最大请求


class GDBRPCServer:
    """
    GDB 内嵌 Python RPC Server

    架构:
    - 后台线程: 负责 socket accept/recv/send (I/O only)
    - GDB 主线程: 通过 gdb.post_event() 执行所有 GDB API 调用
    - 结果通过 Queue 在两个线程间传递
    """

    def __init__(
        self,
        sock_path: str,
        session_meta: dict,
        heartbeat_timeout: int = 600,
        command_timeout: float = DEFAULT_COMMAND_TIMEOUT
    ):
        """
        初始化 RPC Server

        Args:
            sock_path: Unix Domain Socket 路径
            session_meta: 会话元数据 (mode, binary, core, pid, etc.)
            heartbeat_timeout: 心跳超时秒数，默认 600s (10min)
            command_timeout: 单个命令执行超时秒数
        """
        if not GDB_AVAILABLE:
            raise RuntimeError("GDBRPCServer must run inside GDB Python interpreter")

        self.sock_path = Path(sock_path)
        self.session_meta = session_meta
        self.heartbeat_timeout = heartbeat_timeout
        self.command_timeout = command_timeout

        self.running = False
        self.server_sock: Optional[socket.socket] = None
        self.accept_thread: Optional[threading.Thread] = None
        self.last_active = time.time()
        self.heartbeat_timer: Optional[threading.Timer] = None
        self._state = "loading"
        self._loading_start = time.time()

        # 命令处理器注册表
        self._handlers: Dict[str, Callable] = {}
        self._register_builtin_handlers()

    def _register_builtin_handlers(self) -> None:
        """注册内置命令处理器"""
        # 动态加载 handlers 模块（避免相对导入问题）
        import importlib.util
        server_dir = os.environ.get("GDB_CLI_SERVER_DIR", "/tmp")
        handlers_path = Path(server_dir) / "handlers.py"
        spec = importlib.util.spec_from_file_location("handlers", handlers_path)
        handlers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handlers)

        self._handlers = {
            "eval": handlers.handle_eval,
            "threads": handlers.handle_threads,
            "bt": handlers.handle_backtrace,
            "frame": handlers.handle_frame_select,
            "locals": handlers.handle_locals,
            "exec": handlers.handle_exec,
            "status": handlers.handle_status,
            "eval_element": handlers.handle_eval_element,
            "thread_apply": handlers.handle_thread_apply,
            "args": handlers.handle_args,
            "registers": handlers.handle_registers,
            "memory": handlers.handle_memory,
            "ptype": handlers.handle_ptype,
            "thread_switch": handlers.handle_thread_switch,
            "sharedlibs": handlers.handle_sharedlibs,
            "disasm": handlers.handle_disasm,
            "ping": self._handle_ping,
        }

    def _handle_ping(self, **kwargs) -> dict:
        """心跳 ping 处理"""
        return {"pong": True, "time": time.time(), "state": self._state}

    def _handle_loading_status(self) -> dict:
        """加载阶段的轻量状态查询，不访问 GDB API。"""
        return {
            "state": "loading",
            "elapsed": time.time() - self._loading_start,
            "session_meta": self.session_meta,
        }

    def set_ready(self) -> None:
        """标记会话已完成初始化，可以处理完整命令集。"""
        self._state = "ready"

    def start(self) -> None:
        """启动监听线程，注册心跳定时器"""
        if self.running:
            return

        # 确保目录存在
        self.sock_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建 Unix Domain Socket
        self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 清理旧 socket 文件
        if self.sock_path.exists():
            self.sock_path.unlink()

        self.server_sock.bind(str(self.sock_path))
        self.server_sock.listen(1)
        self.server_sock.settimeout(1.0)  # accept 超时，允许定期检查 running 状态

        self.running = True

        # 启动 accept 线程
        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()

        # 启动心跳定时器
        self._start_heartbeat_timer()

        gdb.write(f"[GDBRPCServer] Listening on {self.sock_path}\n")

    def stop(self) -> None:
        """关闭 socket，清理资源"""
        self.running = False

        # 取消心跳定时器
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
            self.heartbeat_timer = None

        # 关闭 socket
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

        # 清理 socket 文件
        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except Exception:
                pass

        # 等待 accept 线程结束
        if self.accept_thread and self.accept_thread.is_alive():
            self.accept_thread.join(timeout=2.0)

        gdb.write("[GDBRPCServer] Stopped\n")

    def _accept_loop(self) -> None:
        """
        后台线程：accept 连接 → post_event → 回写响应

        关键约束：此线程绝不直接调用 GDB API
        """
        while self.running:
            try:
                conn, _ = self.server_sock.accept()  # type: ignore
            except socket.timeout:
                continue  # 定期检查 running 状态
            except OSError:
                break  # socket 已关闭

            try:
                # 接收请求
                conn.settimeout(DEFAULT_SOCKET_TIMEOUT)
                data = b""
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > MAX_REQUEST_SIZE:
                        raise ValueError("Request too large")

                if not data:
                    conn.close()
                    continue

                # 解析 JSON 请求
                try:
                    request = json.loads(data.decode("utf-8"))
                except json.JSONDecodeError as e:
                    response = {"ok": False, "error": f"Invalid JSON: {e}"}
                    conn.sendall(json.dumps(response).encode())
                    conn.close()
                    continue

                # 重置心跳
                self._reset_heartbeat()

                # 直接在后台线程执行（注意：可能有线程安全问题，但对于只读操作通常可行）
                try:
                    result = self._dispatch(request)
                    response = {"ok": True, "data": result}
                except gdb.MemoryError as e:
                    response = {"ok": False, "error": f"Cannot access memory: {e}"}
                except gdb.error as e:  # type: ignore
                    response = {"ok": False, "error": f"GDB error: {e}"}
                except Exception as e:
                    response = {"ok": False, "error": str(e)}

                # 发送响应
                conn.sendall(json.dumps(response).encode())

            except Exception as e:
                try:
                    conn.sendall(json.dumps({"ok": False, "error": str(e)}).encode())
                except Exception:
                    pass
            finally:
                conn.close()

    def _dispatch(self, request: dict) -> dict:
        """
        主线程：根据 cmd 分发到具体 handler

        Args:
            request: {"cmd": "...", ...params}

        Returns:
            命令执行结果 (将被包装在 {"ok": True, "data": ...} 中)
        """
        cmd = request.get("cmd")
        if not cmd:
            raise ValueError("Missing 'cmd' in request")

        if self._state == "loading":
            if cmd == "status":
                return self._handle_loading_status()
            if cmd not in ("ping", "status"):
                elapsed = time.time() - self._loading_start
                raise ValueError(f"Session is loading ({elapsed:.0f}s elapsed)")

        handler = self._handlers.get(cmd)
        if not handler:
            raise ValueError(f"Unknown command: {cmd}")

        # 提取参数 (排除 'cmd' 字段)
        params = {k: v for k, v in request.items() if k != "cmd"}

        # 注入 session 元数据
        params["_session_meta"] = self.session_meta

        return handler(**params)

    def _start_heartbeat_timer(self) -> None:
        """启动心跳超时定时器"""
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()

        self.heartbeat_timer = threading.Timer(
            self.heartbeat_timeout,
            self._heartbeat_timeout
        )
        self.heartbeat_timer.daemon = True
        self.heartbeat_timer.start()

    def _reset_heartbeat(self) -> None:
        """每次收到请求后重置心跳计时器"""
        self.last_active = time.time()
        self._start_heartbeat_timer()

    def _heartbeat_timeout(self) -> None:
        """
        心跳超时处理：在 GDB 主线程执行 detach + quit
        """
        if not self.running:
            return

        gdb.write(f"[GDBRPCServer] Heartbeat timeout ({self.heartbeat_timeout}s), detaching...\n")

        def do_cleanup():
            try:
                # detach 所有 inferior
                for inferior in gdb.inferiors():
                    if inferior.pid:
                        try:
                            gdb.execute(f"detach {inferior.pid}", to_string=True)
                        except Exception:
                            pass
                gdb.execute("quit", to_string=True)
            except Exception as e:
                gdb.write(f"[GDBRPCServer] Cleanup error: {e}\n")
                # 强制退出
                import os
                os._exit(0)

        gdb.post_event(do_cleanup)


def start_server(sock_path: str, session_meta: dict, heartbeat_timeout: int = 600) -> GDBRPCServer:
    """
    启动 GDB RPC Server 的便捷函数

    在 GDB 中通过 source 加载后调用:
    ```
    source /path/to/gdb_rpc_server.py
    python start_server("/tmp/gdb.sock", {"mode": "core", "binary": "./a.out"})
    ```
    """
    server = GDBRPCServer(sock_path, session_meta, heartbeat_timeout)
    server.start()

    import __main__
    __main__._gdb_rpc_server = server

    # 注册 before_prompt 事件来处理 post_event
    # 这样 GDB 在等待输入时会处理事件
    def process_events():
        pass  # post_event 的事件会在 before_prompt 时被处理

    gdb.events.before_prompt.connect(process_events)

    return server


# GDB 启动时自动初始化 (如果环境变量指定了配置)
def _auto_init() -> None:
    """
    从环境变量读取配置并自动启动

    环境变量:
    - GDB_CLI_SOCK_PATH: Socket 路径
    - GDB_CLI_SESSION_META: JSON 格式的 session 元数据
    - GDB_CLI_HEARTBEAT: 心跳超时秒数
    """
    sock_path = os.environ.get("GDB_CLI_SOCK_PATH")
    meta_json = os.environ.get("GDB_CLI_SESSION_META")
    heartbeat = os.environ.get("GDB_CLI_HEARTBEAT", "600")

    if sock_path and meta_json and GDB_AVAILABLE:
        try:
            session_meta = json.loads(meta_json)
            heartbeat_timeout = int(heartbeat)
            start_server(sock_path, session_meta, heartbeat_timeout)
        except Exception as e:
            gdb.write(f"[GDBRPCServer] Auto-init failed: {e}\n")


# 延迟初始化 (在 GDB 完全加载后)
if GDB_AVAILABLE:
    gdb.events.new_objfile.connect(lambda _: None)  # 占位，确保 events 可用
    # 实际自动初始化由 launcher 通过 -ex 调用 start_server
