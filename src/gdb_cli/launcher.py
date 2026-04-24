"""
GDB Launcher - 启动 GDB 进程

提供两种模式:
- Core 模式: 加载 core dump 文件
- Attach 模式: Attach 到运行中的进程
"""


import json
import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from .session import SessionMeta, create_session

# GDB Server 脚本路径
GDB_SERVER_SCRIPT = Path(__file__).parent / "gdb_server" / "gdb_rpc_server.py"


class GDBLauncherError(Exception):
    """启动器错误"""
    pass


class GDBProcess:
    """GDB 进程管理"""

    def __init__(self, session: SessionMeta):
        self.session = session
        self._process: Optional[subprocess.Popen] = None

    @property
    def pid(self) -> Optional[int]:
        """GDB 进程 PID"""
        return self._process.pid if self._process else None

    def is_running(self) -> bool:
        """检查 GDB 进程是否运行"""
        if self._process is None:
            return False
        return self._process.poll() is None

    def terminate(self, timeout: float = 5.0) -> None:
        """终止 GDB 进程"""
        if self._process is None:
            return

        if not self.is_running():
            return

        # 发送 SIGTERM
        try:
            self._process.terminate()
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # 强制 SIGKILL
            self._process.kill()
            self._process.wait(timeout=1.0)
        finally:
            self._process = None


def launch_core(
    binary: str,
    core: str,
    sysroot: Optional[str] = None,
    solib_prefix: Optional[str] = None,
    source_dir: Optional[str] = None,
    timeout: int = 600,
    gdb_path: str = "gdb"
) -> GDBProcess:
    """
    启动 Core 模式 GDB 进程

    Args:
        binary: 可执行文件路径
        core: Core dump 文件路径
        sysroot: sysroot 路径 (用于跨机器调试)
        solib_prefix: 共享库前缀
        source_dir: 源码目录
        timeout: 心跳超时秒数
        gdb_path: GDB 可执行文件路径

    Returns:
        GDBProcess 实例
    """
    # 创建 session
    session = create_session(
        mode="core",
        binary=binary,
        core=core,
        timeout=timeout
    )

    # 构建 GDB 启动命令
    gdb_commands = [
        "set pagination off",
        "set print elements 0",
        "set confirm off",
    ]

    # sysroot / solib-prefix
    if sysroot:
        gdb_commands.append(f"set sysroot {_escape_gdb_arg(sysroot)}")
    if solib_prefix:
        gdb_commands.append(f"set solib-absolute-prefix {_escape_gdb_arg(solib_prefix)}")

    # 源码目录
    if source_dir:
        gdb_commands.append(f"directory {_escape_gdb_arg(source_dir)}")

    # 启动 RPC Server
    gdb_commands.extend(_build_server_commands(session))

    # 加载 binary 和 core。Server 先启动，这样 load 可以异步返回。
    gdb_commands.append(f"file {_escape_gdb_arg(binary)}")
    gdb_commands.append(f"core-file {_escape_gdb_arg(core)}")
    gdb_commands.append("python _gdb_rpc_server.set_ready()")

    # 构建 GDB 参数
    gdb_args = [gdb_path, "-nx", "-q"]
    for cmd in gdb_commands:
        gdb_args.extend(["-ex", cmd])

    # 启动进程
    _start_gdb_process(gdb_args, session, timeout=float(timeout))
    gdb_process = GDBProcess(session)
    gdb_process._process = session._gdb_process
    return gdb_process


def launch_attach(
    pid: int,
    binary: Optional[str] = None,
    scheduler_locking: bool = True,
    non_stop: bool = True,
    timeout: int = 600,
    allow_write: bool = False,
    allow_call: bool = False,
    gdb_path: str = "gdb"
) -> GDBProcess:
    """
    启动 Attach 模式 GDB 进程

    Args:
        pid: 目标进程 PID
        binary: 可执行文件路径 (可选)
        scheduler_locking: 是否启用 scheduler-locking
        non_stop: 是否启用 non-stop 模式
        timeout: 心跳超时秒数
        allow_write: 是否允许内存修改
        allow_call: 是否允许函数调用
        gdb_path: GDB 可执行文件路径

    Returns:
        GDBProcess 实例
    """
    # 检查进程是否存在
    if not _check_process_exists(pid):
        raise GDBLauncherError(f"Process {pid} does not exist")

    # 创建 session
    safety_level = "full" if (allow_write or allow_call) else "readonly"
    if allow_write and not allow_call:
        safety_level = "readwrite"

    session = create_session(
        mode="attach",
        pid=pid,
        binary=binary,
        timeout=timeout,
        safety_level=safety_level
    )

    # 构建 GDB 启动命令
    gdb_commands = [
        "set pagination off",
        "set print elements 0",
        "set confirm off",
    ]

    # non-stop 模式
    if non_stop:
        gdb_commands.append("set non-stop on")
        gdb_commands.append("set mi-async on")
    else:
        gdb_commands.append("set non-stop off")
        gdb_commands.append("set mi-async off")

    # 加载 binary (可选)
    if binary:
        gdb_commands.append(f"file {_escape_gdb_arg(binary)}")

    # Attach
    gdb_commands.append(f"attach {pid}")

    # scheduler-locking
    if scheduler_locking:
        gdb_commands.append("set scheduler-locking on")

    # 启动 RPC Server
    gdb_commands.extend(_build_server_commands(session))
    gdb_commands.append("python _gdb_rpc_server.set_ready()")

    # 构建 GDB 参数
    gdb_args = [gdb_path, "-nx", "-q"]
    for cmd in gdb_commands:
        gdb_args.extend(["-ex", cmd])

    # 启动进程
    _start_gdb_process(gdb_args, session, timeout=float(timeout))
    gdb_process = GDBProcess(session)
    gdb_process._process = session._gdb_process
    return gdb_process


def launch_target(
    remote: str,
    binary: Optional[str] = None,
    scheduler_locking: bool = True,
    non_stop: bool = False,
    timeout: int = 600,
    allow_write: bool = False,
    allow_call: bool = False,
    gdb_path: str = "gdb"
) -> GDBProcess:
    """
    Args:
        remote: host:port
        binary: 可执行文件路径 (可选)
        scheduler_locking: 是否启用 scheduler-locking
        non_stop: 是否启用 non-stop 模式
        timeout: 心跳超时秒数
        allow_write: 是否允许内存修改
        allow_call: 是否允许函数调用
        gdb_path: GDB 可执行文件路径

    Returns:
        GDBProcess 实例
    """
    # 创建 session
    safety_level = "full" if (allow_write or allow_call) else "readonly"
    if allow_write and not allow_call:
        safety_level = "readwrite"

    session = create_session(
        mode="target",
        remote=remote,
        binary=binary,
        timeout=timeout,
        safety_level=safety_level
    )

    # 构建 GDB 启动命令
    gdb_commands = [
        "set pagination off",
        "set print elements 0",
        "set confirm off",
    ]

    # non-stop 模式
    if non_stop:
        gdb_commands.append("set non-stop on")
        gdb_commands.append("set target-async on")
        gdb_commands.append("set mi-async on")

    # 加载 binary (可选)
    if binary:
        gdb_commands.append(f"file {_escape_gdb_arg(binary)}")

    # Target
    gdb_commands.append(f"target extended-remote {_escape_gdb_arg(remote)}")

    # scheduler-locking
    if scheduler_locking:
        gdb_commands.append("set scheduler-locking on")

    # 启动 RPC Server
    gdb_commands.extend(_build_server_commands(session))
    gdb_commands.append("python _gdb_rpc_server.set_ready()")

    # 构建 GDB 参数
    gdb_args = [gdb_path, "-nx", "-q"]
    for cmd in gdb_commands:
        gdb_args.extend(["-ex", cmd])

    # 启动进程
    _start_gdb_process(gdb_args, session, timeout=float(timeout))
    gdb_process = GDBProcess(session)
    gdb_process._process = session._gdb_process
    return gdb_process


def _build_server_commands(session: SessionMeta) -> List[str]:
    """构建 RPC Server 启动命令"""
    session_meta = {
        "session_id": session.session_id,
        "mode": session.mode,
        "binary": session.binary,
        "core": session.core,
        "pid": session.pid,
        "remote": session.remote,
        "sock_path": str(session.sock_path),
        "started_at": session.started_at,
    }

    # 序列化 session 元数据
    meta_json = json.dumps(session_meta)

    # 需要转义 JSON 中的引号
    meta_escaped = meta_json.replace('"', '\\"')

    return [
        # 设置环境变量
        f"python import os; os.environ['GDB_CLI_SOCK_PATH'] = {_escape_gdb_arg(str(session.sock_path))}",
        f"python os.environ['GDB_CLI_SESSION_META'] = \"{meta_escaped}\"",
        f"python os.environ['GDB_CLI_HEARTBEAT'] = '{session.heartbeat_timeout}'",
        f"python os.environ['GDB_CLI_SERVER_DIR'] = {_escape_gdb_arg(str(GDB_SERVER_SCRIPT.parent))}",
        # 加载 Server 脚本 (source 会将定义加载到全局命名空间)
        f"source {_escape_gdb_arg(str(GDB_SERVER_SCRIPT))}",
        # 启动 Server (直接调用全局命名空间中的 start_server)
        f"python start_server({_escape_gdb_arg(str(session.sock_path))}, {session_meta}, {session.heartbeat_timeout})",
    ]


def _cleanup_fifo_if_exists(fifo_path):
    """安全清理 FIFO 文件"""
    if fifo_path is not None and fifo_path.exists():
        try:
            fifo_path.unlink()
        except Exception:
            pass


def _escape_gdb_arg(arg: str) -> str:
    """将参数转义为 GDB 安全的单引号字符串"""
    escaped = arg.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _start_gdb_process(
    gdb_args: List[str],
    session: SessionMeta,
    timeout: float = 300.0
) -> subprocess.Popen:
    """启动 GDB 进程"""
    try:
        # 创建 named FIFO 作为 GDB stdin，使 GDB 阻塞在读而不退出
        # FIFO 持久化在 session 目录中，不依赖父进程的 fd 生命周期
        session_dir = Path(session.sock_path).parent
        fifo_path = session_dir / "gdb.stdin"
        if fifo_path.exists():
            fifo_path.unlink()
        os.mkfifo(str(fifo_path))

        # 以非阻塞方式打开 FIFO 写端（防止 open 阻塞）
        # 然后立即关闭不用——GDB 阻塞在读端等待数据即可保持存活
        # 注意：必须先启动 GDB（读端），再打开写端，否则 open 会阻塞
        # 所以用 O_RDWR 打开 FIFO，这样不会阻塞也不会产生 EOF
        fifo_fd = os.open(str(fifo_path), os.O_RDWR | os.O_NONBLOCK)

        log_path = session_dir / "gdb.log"
        with open(log_path, "w") as log_fd:
            process = subprocess.Popen(
                gdb_args,
                stdin=fifo_fd,
                stdout=subprocess.DEVNULL,
                stderr=log_fd,
                start_new_session=True,  # 创建新的进程组
            )

        # 关闭父进程持有的 fd（子进程已继承）
        os.close(fifo_fd)

        # 更新 session 中的 GDB PID 并持久化
        session.gdb_pid = process.pid
        from .session import _write_meta
        _write_meta(session)

        # _gdb_process 是运行时属性，不持久化到 meta.json。
        # 从磁盘恢复的 session 不会拥有该属性 —— 可通过 gdb_pid 查询进程状态。
        session._gdb_process = process

        # 等待 socket 文件创建
        _wait_for_socket(Path(session.sock_path), timeout=timeout, process=process)

        return process

    except FileNotFoundError:
        _cleanup_fifo_if_exists(fifo_path)
        raise GDBLauncherError(f"GDB not found: {gdb_args[0]}")
    except Exception as e:
        _cleanup_fifo_if_exists(fifo_path)
        if 'fifo_fd' in locals():
            try:
                os.close(fifo_fd)
            except Exception:
                pass
        raise GDBLauncherError(f"Failed to start GDB: {e}")


def _wait_for_socket(sock_path: Path, timeout: float = 30.0,
                      process: Optional[subprocess.Popen] = None) -> None:
    """等待 socket 文件创建，同时检查 GDB 进程是否崩溃"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if process is not None and process.poll() is not None:
            raise GDBLauncherError(
                f"GDB exited prematurely with code {process.returncode}"
            )
        if sock_path.exists():
            return
        time.sleep(0.1)
    raise GDBLauncherError(f"Timeout waiting for socket: {sock_path}")


def _check_process_exists(pid: int) -> bool:
    """检查进程是否存在"""
    try:
        os.kill(pid, 0)  # 发送信号 0 (不实际发送，只检查进程是否存在)
        return True
    except OSError:
        return False


def stop_gdb(session_id: str) -> bool:
    """
    停止 GDB 进程

    Args:
        session_id: 会话 ID

    Returns:
        是否成功停止
    """
    from .session import cleanup_session, get_session

    session = get_session(session_id)
    if session is None:
        return False

    # 发送停止命令
    try:
        from .client import GDBClient, GDBClientError
        with GDBClient(str(session.sock_path), timeout=5.0) as client:
            client.call("stop")
    except GDBClientError:
        pass  # 可能已经停止

    # 清理 session
    cleanup_session(session_id)

    return True
