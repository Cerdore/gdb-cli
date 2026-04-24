"""
Unix Socket Client - 与 GDB RPC Server 通信

提供简洁的客户端接口，封装 socket 连接、请求发送、响应接收。
"""


import io
import json
import socket
from pathlib import Path
from typing import Optional

# 默认配置
DEFAULT_TIMEOUT = 30.0  # 默认命令超时
CONNECT_TIMEOUT = 5.0  # 连接超时
MAX_RESPONSE_SIZE = 50 * 1024 * 1024  # 50MB 最大响应


class GDBClientError(Exception):
    """GDB 客户端错误"""
    pass


class GDBConnectionError(GDBClientError):
    """连接错误"""
    pass


class GDBCommandError(GDBClientError):
    """命令执行错误"""
    def __init__(self, message: str, command: Optional[str] = None):
        super().__init__(message)
        self.command = command


class GDBClient:
    """
    GDB RPC Server 客户端

    通过 Unix Domain Socket 与 GDB 内嵌的 RPC Server 通信。

    Usage:
        client = GDBClient("/path/to/gdb.sock")
        result = client.call("eval", expr="lock_mgr->buckets[0]")
        print(result)
        client.close()
    """

    def __init__(
        self,
        sock_path: str,
        timeout: float = DEFAULT_TIMEOUT
    ):
        """
        初始化客户端

        Args:
            sock_path: Unix Domain Socket 路径
            timeout: 命令超时秒数
        """
        self.sock_path = Path(sock_path)
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """建立连接"""
        if self._sock is not None:
            return

        if not self.sock_path.exists():
            raise GDBConnectionError(f"Socket not found: {self.sock_path}")

        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.settimeout(CONNECT_TIMEOUT)
            self._sock.connect(str(self.sock_path))
            self._sock.settimeout(self.timeout)
        except OSError as e:
            self._sock = None
            raise GDBConnectionError(f"Cannot connect to {self.sock_path}: {e}")

    def close(self) -> None:
        """关闭连接"""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._sock is not None

    def call(
        self,
        cmd: str,
        timeout: Optional[float] = None,
        **params
    ) -> dict:
        """
        发送命令并获取响应

        Args:
            cmd: 命令名称
            timeout: 本次命令超时 (None 使用默认值)
            **params: 命令参数

        Returns:
            响应数据 {"ok": True, "data": ...} 或 {"ok": False, "error": "..."}

        Raises:
            GDBConnectionError: 连接错误
            GDBCommandError: 命令执行错误
        """
        # 确保连接
        if not self.is_connected():
            self.connect()

        # 构建请求
        request = {"cmd": cmd, **params}
        request_data = json.dumps(request).encode("utf-8")

        # 设置本次超时
        if timeout is not None:
            self._sock.settimeout(timeout)  # type: ignore
        else:
            self._sock.settimeout(self.timeout)  # type: ignore

        try:
            # 发送请求
            self._sock.sendall(request_data)  # type: ignore

            # 关闭写端，通知 Server 请求发送完毕
            self._sock.shutdown(socket.SHUT_WR)  # type: ignore

            # 接收响应
            response_buffer = io.BytesIO()
            while True:
                chunk = self._sock.recv(65536)  # type: ignore
                if not chunk:
                    break
                response_buffer.write(chunk)
                if response_buffer.tell() > MAX_RESPONSE_SIZE:
                    raise GDBClientError("Response too large")

            if response_buffer.tell() == 0:
                raise GDBConnectionError("Empty response from server")

            response_data = response_buffer.getvalue()

            # 解析响应
            response = json.loads(response_data.decode("utf-8"))

            if not response.get("ok"):
                error_msg = response.get("error", "Unknown error")
                raise GDBCommandError(error_msg, cmd)

            return response.get("data", {})

        except socket.timeout:
            raise GDBCommandError(f"Command '{cmd}' timed out", cmd)
        except OSError as e:
            self.close()
            raise GDBConnectionError(f"Socket error: {e}")
        except json.JSONDecodeError as e:
            raise GDBClientError(f"Invalid JSON response: {e}")
        finally:
            # shutdown(SHUT_WR) 后 socket 不可复用，关闭以便下次 call 重连
            self.close()

    def ping(self) -> bool:
        """检查服务器是否响应"""
        try:
            result = self.call("ping", timeout=5.0)
            return result.get("pong", False)
        except GDBClientError:
            return False

    # ============ 便捷方法 ============

    def eval(self, expr: str, max_depth: int = 3, max_elements: int = 50) -> dict:
        """求值表达式"""
        return self.call("eval", expr=expr, max_depth=max_depth, max_elements=max_elements)

    def threads(
        self,
        range_str: Optional[str] = None,
        limit: int = 20,
        filter_state: Optional[str] = None
    ) -> dict:
        """列出线程"""
        params = {"limit": limit}
        if range_str:
            params["range_str"] = range_str
        if filter_state:
            params["filter_state"] = filter_state
        return self.call("threads", **params)

    def backtrace(
        self,
        thread_id: Optional[int] = None,
        limit: int = 30,
        full: bool = False
    ) -> dict:
        """获取 backtrace"""
        params = {"limit": limit, "full": full}
        if thread_id is not None:
            params["thread_id"] = thread_id
        return self.call("bt", **params)

    def frame_select(self, number: int) -> dict:
        """选择栈帧"""
        return self.call("frame", number=number)

    def locals(self, thread_id: Optional[int] = None, frame: int = 0) -> dict:
        """获取局部变量"""
        params = {"frame": frame}
        if thread_id is not None:
            params["thread_id"] = thread_id
        return self.call("locals", **params)

    def exec_cmd(self, command: str) -> dict:
        """执行 GDB 命令"""
        return self.call("exec", command=command)

    def status(self) -> dict:
        """获取状态"""
        return self.call("status")

    def __enter__(self) -> 'GDBClient':
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def send_command(sock_path: str, cmd: str, timeout: float = DEFAULT_TIMEOUT, **params) -> dict:
    """
    发送单次命令的便捷函数

    Usage:
        result = send_command("/tmp/gdb.sock", "eval", expr="x")
    """
    with GDBClient(sock_path, timeout=timeout) as client:
        return client.call(cmd, **params)
