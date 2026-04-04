"""
GDB CLI - 命令行入口

Usage:
    gdb-cli load --binary ./my_program --core ./core.1234
    gdb-cli attach --pid 9876
    gdb-cli eval-cmd --session <id> "lock_mgr->buckets[0]"
    gdb-cli threads --session <id> [--limit 20]
    gdb-cli bt --session <id> [--thread 12] [--limit 30]
    gdb-cli stop --session <id>
"""


import json
import os
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .client import GDBClient, GDBClientError, GDBCommandError
from .launcher import GDBLauncherError, launch_attach, launch_core
from .session import (
    cleanup_dead_sessions,
    find_session_by_core,
    find_session_by_pid,
    get_session,
    list_sessions,
)


def print_json(data: dict) -> None:
    """格式化输出 JSON"""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def print_error(message: str, details: Optional[str] = None) -> None:
    """输出错误信息"""
    error = {"error": message}
    if details:
        error["details"] = details
    click.echo(json.dumps(error, indent=2), err=True)


def get_client(session_id: str) -> GDBClient:
    """获取会话的客户端"""
    session = get_session(session_id)
    if session is None:
        raise click.ClickException(f"Session not found: {session_id}")

    if session.sock_path is None:
        raise click.ClickException(f"Session has no socket: {session_id}")

    return GDBClient(str(session.sock_path))


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """GDB CLI for AI - 瘦客户端 CLI + GDB 内置 Python RPC Server"""
    pass


@main.command()
@click.option("--binary", "-b", required=True, help="可执行文件路径")
@click.option("--core", "-c", required=True, help="Core dump 文件路径")
@click.option("--sysroot", help="sysroot 路径 (跨机器调试)")
@click.option("--solib-prefix", help="共享库前缀")
@click.option("--source-dir", help="源码目录")
@click.option("--timeout", default=600, help="心跳超时秒数 (默认 600)")
@click.option("--gdb-path", default="gdb", help="GDB 可执行文件路径")
def load(
    binary: str,
    core: str,
    sysroot: Optional[str],
    solib_prefix: Optional[str],
    source_dir: Optional[str],
    timeout: int,
    gdb_path: str
) -> None:
    """加载 core dump，启动 GDB 常驻进程"""
    # 检查是否已有相同 core 的会话
    existing = find_session_by_core(core)
    if existing:
        print_json({
            "session_id": existing.session_id,
            "mode": existing.mode,
            "binary": existing.binary,
            "core": existing.core,
            "status": "reused",
            "message": "Session already exists for this core file"
        })
        return

    try:
        gdb_process = launch_core(
            binary=binary,
            core=core,
            sysroot=sysroot,
            solib_prefix=solib_prefix,
            source_dir=source_dir,
            timeout=timeout,
            gdb_path=gdb_path
        )

        session = gdb_process.session

        print_json({
            "session_id": session.session_id,
            "mode": session.mode,
            "binary": session.binary,
            "core": session.core,
            "sock_path": session.sock_path,
            "gdb_pid": gdb_process.pid,
            "status": "loading"
        })

    except GDBLauncherError as e:
        print_error("Failed to start GDB", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--pid", "-p", required=True, type=int, help="目标进程 PID")
@click.option("--binary", "-b", help="可执行文件路径 (可选)")
@click.option("--scheduler-locking/--no-scheduler-locking", default=True, help="启用 scheduler-locking")
@click.option("--non-stop/--no-non-stop", default=True, help="启用 non-stop 模式")
@click.option("--timeout", default=600, help="心跳超时秒数 (默认 600)")
@click.option("--allow-write", is_flag=True, help="允许内存修改")
@click.option("--allow-call", is_flag=True, help="允许函数调用")
def attach(
    pid: int,
    binary: Optional[str],
    scheduler_locking: bool,
    non_stop: bool,
    timeout: int,
    allow_write: bool,
    allow_call: bool
) -> None:
    """Attach 到运行中进程"""
    # 检查是否已有相同 PID 的会话 (幂等性)
    existing = find_session_by_pid(pid)
    if existing:
        print_json({
            "session_id": existing.session_id,
            "mode": existing.mode,
            "pid": existing.pid,
            "status": "reused",
            "message": "Session already exists for this PID"
        })
        return

    try:
        gdb_process = launch_attach(
            pid=pid,
            binary=binary,
            scheduler_locking=scheduler_locking,
            non_stop=non_stop,
            timeout=timeout,
            allow_write=allow_write,
            allow_call=allow_call
        )

        session = gdb_process.session

        print_json({
            "session_id": session.session_id,
            "mode": session.mode,
            "pid": session.pid,
            "binary": session.binary,
            "sock_path": session.sock_path,
            "gdb_pid": gdb_process.pid,
            "safety_level": session.safety_level,
            "status": "started"
        })

    except GDBLauncherError as e:
        print_error("Failed to attach to process", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("expr")
@click.option("--max-depth", default=3, help="递归深度限制")
@click.option("--max-elements", default=50, help="数组元素限制")
def eval_cmd(session: str, expr: str, max_depth: int, max_elements: int) -> None:
    """求值 C/C++ 表达式"""
    try:
        with get_client(session) as client:
            result = client.eval(expr, max_depth=max_depth, max_elements=max_elements)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e), expr)
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.option("--range", "range_str", help="线程范围 (如 3-10)")
@click.option("--limit", default=20, help="最大返回数量")
@click.option("--filter-state", help="过滤状态 (running/stopped)")
def threads(session: str, range_str: Optional[str], limit: int, filter_state: Optional[str]) -> None:
    """列出线程"""
    try:
        with get_client(session) as client:
            result = client.threads(range_str=range_str, limit=limit, filter_state=filter_state)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.option("--thread", "-t", "thread_id", type=int, help="指定线程 ID")
@click.option("--limit", default=30, help="最大帧数")
@click.option("--full", is_flag=True, help="包含局部变量")
@click.option("--range", "range_str", help="帧范围 (如 5-15)")
def bt(session: str, thread_id: Optional[int], limit: int, full: bool, range_str: Optional[str]) -> None:
    """获取 backtrace"""
    try:
        with get_client(session) as client:
            params = {"limit": limit, "full": full}
            if thread_id is not None:
                params["thread_id"] = thread_id
            if range_str:
                params["range_str"] = range_str
            result = client.call("bt", **params)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command("frame")
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("number", type=int)
def frame_cmd(session: str, number: int) -> None:
    """选择栈帧"""
    try:
        with get_client(session) as client:
            result = client.frame_select(number)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.option("--thread", "-t", "thread_id", type=int, help="线程 ID")
@click.option("--frame", "-f", default=0, help="栈帧编号")
def locals_cmd(session: str, thread_id: Optional[int], frame: int) -> None:
    """获取局部变量"""
    try:
        with get_client(session) as client:
            result = client.locals(thread_id=thread_id, frame=frame)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command("exec")
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("command")
@click.option("--safety-level", default="readonly", help="安全级别 (readonly/readwrite/full)")
def exec_cmd(session: str, command: str, safety_level: str) -> None:
    """执行原始 GDB 命令"""
    try:
        with get_client(session) as client:
            result = client.exec_cmd(command, safety_level=safety_level)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e), command)
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
def stop(session: str) -> None:
    """停止会话，安全退出 GDB"""
    try:
        # 发送停止命令
        with get_client(session) as client:
            client.call("stop")

        print_json({
            "session_id": session,
            "status": "stopped"
        })

    except GDBClientError:
        # 强制清理
        from .session import cleanup_session
        cleanup_session(session)
        print_json({
            "session_id": session,
            "status": "force_stopped"
        })


@main.command()
def sessions() -> None:
    """列出所有活跃会话"""
    # 清理僵尸会话
    cleanup_dead_sessions()

    session_list = list_sessions(alive_only=True)

    result = {
        "sessions": [
            {
                "session_id": s.session_id,
                "mode": s.mode,
                "binary": s.binary,
                "pid": s.pid,
                "core": s.core,
                "started_at": s.started_at,
            }
            for s in session_list
        ],
        "count": len(session_list)
    }

    print_json(result)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
def status(session: str) -> None:
    """查看会话状态"""
    try:
        with get_client(session) as client:
            result = client.status()
            result["session_id"] = session
            print_json(result)
    except GDBClientError as e:
        meta = get_session(session)
        if meta is None:
            print_error("Session not found", session)
            raise click.exceptions.Exit(1)

        if meta.gdb_pid:
            try:
                os.kill(meta.gdb_pid, 0)
                print_json({
                    "session_id": session,
                    "state": "loading",
                    "message": "GDB process alive, not yet responding"
                })
                return
            except OSError:
                print_error("Session dead", f"GDB process {meta.gdb_pid} no longer exists")
                raise click.exceptions.Exit(1)

        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command("eval-element")
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("expr")
@click.option("--index", "-i", required=True, type=int, help="元素索引")
@click.option("--max-depth", default=3, help="递归深度限制")
def eval_element_cmd(session: str, expr: str, index: int, max_depth: int) -> None:
    """访问数组/容器中的特定元素"""
    try:
        with get_client(session) as client:
            result = client.call("eval_element", expr=expr, index=index, max_depth=max_depth)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e), f"{expr}[{index}]")
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command("thread-apply")
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("command")
@click.option("--threads", help="线程 ID 列表 (如 1,3,5)")
@click.option("--all", "all_threads", is_flag=True, help="应用于所有线程")
def thread_apply_cmd(session: str, command: str, threads: Optional[str], all_threads: bool) -> None:
    """批量线程操作"""
    try:
        with get_client(session) as client:
            params = {"command": command}
            if all_threads:
                params["all_threads"] = True
            elif threads:
                params["thread_ids"] = threads
            else:
                print_error("必须指定 --all 或 --threads")
                raise click.exceptions.Exit(1)
            result = client.call("thread_apply", **params)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e), command)
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.option("--thread", "-t", "thread_id", type=int, help="线程 ID")
@click.option("--frame", "-f", default=0, help="栈帧编号")
def args(session: str, thread_id: Optional[int], frame: int) -> None:
    """获取函数参数"""
    try:
        with get_client(session) as client:
            params = {"frame": frame}
            if thread_id is not None:
                params["thread_id"] = thread_id
            result = client.call("args", **params)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.option("--names", "-n", help="寄存器名列表，逗号分隔 (如 rax,rbx,rip)")
@click.option("--thread", "-t", "thread_id", type=int, help="线程 ID")
@click.option("--frame", "-f", default=0, help="栈帧编号")
def registers(session: str, names: Optional[str], thread_id: Optional[int], frame: int) -> None:
    """查看寄存器值"""
    try:
        with get_client(session) as client:
            params = {"frame": frame}
            if names:
                params["names"] = names
            if thread_id is not None:
                params["thread_id"] = thread_id
            result = client.call("registers", **params)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("address")
@click.option("--size", default=64, help="读取字节数 (默认 64, 最大 4096)")
@click.option("--fmt", default="hex", type=click.Choice(["hex", "bytes", "string"]), help="输出格式")
def memory(session: str, address: str, size: int, fmt: str) -> None:
    """检查内存内容"""
    try:
        with get_client(session) as client:
            result = client.call("memory", address=address, size=size, fmt=fmt)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e), address)
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("expr")
def ptype(session: str, expr: str) -> None:
    """查看表达式的类型信息"""
    try:
        with get_client(session) as client:
            result = client.call("ptype", expr=expr)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e), expr)
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command("thread-switch")
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("thread_id", type=int)
def thread_switch_cmd(session: str, thread_id: int) -> None:
    """切换当前线程"""
    try:
        with get_client(session) as client:
            result = client.call("thread_switch", thread_id=thread_id)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command("up")
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("count", type=int, default=1)
def frame_up_cmd(session: str, count: int) -> None:
    """向调用者方向移动栈帧"""
    try:
        with get_client(session) as client:
            result = client.call("frame", number=count, direction="up")
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command("down")
@click.option("--session", "-s", required=True, help="会话 ID")
@click.argument("count", type=int, default=1)
def frame_down_cmd(session: str, count: int) -> None:
    """向被调用者方向移动栈帧"""
    try:
        with get_client(session) as client:
            result = client.call("frame", number=count, direction="down")
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
def sharedlibs(session: str) -> None:
    """查看加载的共享库"""
    try:
        with get_client(session) as client:
            result = client.call("sharedlibs")
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help="会话 ID")
@click.option("--start", help="起始地址或函数名 (默认当前 PC)")
@click.option("--count", default=20, help="指令数量 (默认 20)")
@click.option("--thread", "-t", "thread_id", type=int, help="线程 ID")
@click.option("--frame", "-f", default=0, help="栈帧编号")
def disasm(session: str, start: Optional[str], count: int, thread_id: Optional[int], frame: int) -> None:
    """反汇编"""
    try:
        with get_client(session) as client:
            params = {"count": count, "frame": frame}
            if start:
                params["start"] = start
            if thread_id is not None:
                params["thread_id"] = thread_id
            result = client.call("disasm", **params)
            print_json(result)
    except GDBCommandError as e:
        print_error(str(e))
    except GDBClientError as e:
        print_error("Connection error", str(e))
        raise click.exceptions.Exit(1)


@main.command()
def env_check() -> None:
    """环境自检：gdb版本、ptrace权限、Python版本"""
    import platform
    import shutil

    results = {
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "arch": platform.machine(),
    }

    # 检查 GDB
    gdb_path = shutil.which("gdb")
    if gdb_path:
        results["gdb_path"] = gdb_path
        # 尝试获取版本
        import subprocess
        try:
            output = subprocess.check_output([gdb_path, "--version"], text=True)
            # 提取版本号
            import re
            match = re.search(r"GNU gdb.*?(\d+\.\d+)", output)
            if match:
                results["gdb_version"] = match.group(1)
        except Exception:
            results["gdb_version"] = "unknown"
    else:
        results["gdb_path"] = None
        results["gdb_error"] = "gdb not found in PATH"

    # 检查 ptrace 权限 (Linux only)
    if platform.system() == "Linux":
        ptrace_scope_path = Path("/proc/sys/kernel/yama/ptrace_scope")
        if ptrace_scope_path.exists():
            try:
                scope = ptrace_scope_path.read_text().strip()
                results["ptrace_scope"] = int(scope)
                if int(scope) > 0:
                    results["ptrace_warning"] = "ptrace is restricted. Run 'echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope' to allow attach."
            except Exception:
                results["ptrace_scope"] = "unknown"

    print_json(results)


if __name__ == "__main__":
    main()
