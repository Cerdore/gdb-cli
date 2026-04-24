"""
GDB CLI - 命令行入口

Usage:
    gdb-cli load --binary ./my_program --core ./core.1234
    gdb-cli attach --pid 9876
    gdb-cli target --remote 192.168.0.21:3333
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
from .i18n import t
from .launcher import GDBLauncherError, launch_attach, launch_core, launch_target
from .session import (
    cleanup_dead_sessions,
    find_session_by_core,
    find_session_by_pid,
    find_session_by_remote,
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
    """GDB CLI for AI - Thin client CLI + GDB built-in Python RPC Server"""
    pass


@main.command()
@click.option("--binary", "-b", required=True, help=t("cli.load.binary_help"))
@click.option("--core", "-c", required=True, help=t("cli.load.core_help"))
@click.option("--sysroot", help=t("cli.load.sysroot_help"))
@click.option("--solib-prefix", help=t("cli.load.solib_prefix_help"))
@click.option("--source-dir", help=t("cli.load.source_dir_help"))
@click.option("--timeout", default=600, help=t("cli.load.timeout_help"))
@click.option("--gdb-path", default="gdb", help=t("cli.load.gdb_path_help"))
def load(
    binary: str,
    core: str,
    sysroot: Optional[str],
    solib_prefix: Optional[str],
    source_dir: Optional[str],
    timeout: int,
    gdb_path: str
) -> None:
    """Load core dump and start persistent GDB process"""
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
@click.option("--pid", "-p", required=True, type=int, help=t("cli.attach.pid_help"))
@click.option("--binary", "-b", help=t("cli.attach.binary_help"))
@click.option("--scheduler-locking/--no-scheduler-locking", default=True, help=t("cli.attach.scheduler_locking_help"))
@click.option("--non-stop/--no-non-stop", default=True, help=t("cli.attach.non_stop_help"))
@click.option("--timeout", default=600, help=t("cli.attach.timeout_help"))
@click.option("--allow-write", is_flag=True, help=t("cli.attach.allow_write_help"))
@click.option("--allow-call", is_flag=True, help=t("cli.attach.allow_call_help"))
def attach(
    pid: int,
    binary: Optional[str],
    scheduler_locking: bool,
    non_stop: bool,
    timeout: int,
    allow_write: bool,
    allow_call: bool
) -> None:
    """Attach to running process"""
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
@click.option("--remote", "-r", required=True, type=str, help=t("cli.target.remote_help"))
@click.option("--binary", "-b", help=t("cli.target.binary_help"))
@click.option("--scheduler-locking/--no-scheduler-locking", default=True, help=t("cli.target.scheduler_locking_help"))
@click.option("--non-stop/--no-non-stop", default=False, help=t("cli.target.non_stop_help"))
@click.option("--timeout", default=600, help=t("cli.target.timeout_help"))
@click.option("--allow-write", is_flag=True, help=t("cli.target.allow_write_help"))
@click.option("--allow-call", is_flag=True, help=t("cli.target.allow_call_help"))
@click.option("--gdb-path", default="gdb", help=t("cli.load.gdb_path_help"))
def target(
    remote: str,
    binary: Optional[str],
    scheduler_locking: bool,
    non_stop: bool,
    timeout: int,
    allow_write: bool,
    allow_call: bool,
    gdb_path: str,
) -> None:
    """Connect to remote GDB server"""
    existing = find_session_by_remote(remote)
    if existing:
        print_json({
            "session_id": existing.session_id,
            "mode": existing.mode,
            "remote": existing.remote,
            "status": "reused",
            "message": "Session already exists for this remote"
        })
        return

    try:
        gdb_process = launch_target(
            remote=remote,
            binary=binary,
            scheduler_locking=scheduler_locking,
            non_stop=non_stop,
            timeout=timeout,
            allow_write=allow_write,
            allow_call=allow_call,
            gdb_path=gdb_path
        )

        session = gdb_process.session

        print_json({
            "session_id": session.session_id,
            "mode": session.mode,
            "remote": session.remote,
            "binary": session.binary,
            "remote": session.remote,
            "sock_path": session.sock_path,
            "gdb_pid": gdb_process.pid,
            "safety_level": session.safety_level,
            "status": "started"
        })

    except GDBLauncherError as e:
        print_error("Failed to connect to target", str(e))
        raise click.exceptions.Exit(1)


@main.command()
@click.option("--session", "-s", required=True, help=t("cli.eval_cmd.session_help"))
@click.argument("expr")
@click.option("--max-depth", default=3, help=t("cli.eval_cmd.max_depth_help"))
@click.option("--max-elements", default=50, help=t("cli.eval_cmd.max_elements_help"))
def eval_cmd(session: str, expr: str, max_depth: int, max_elements: int) -> None:
    """Evaluate C/C++ expression"""
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
@click.option("--session", "-s", required=True, help=t("cli.threads.session_help"))
@click.option("--range", "range_str", help=t("cli.threads.range_help"))
@click.option("--limit", default=20, help=t("cli.threads.limit_help"))
@click.option("--filter-state", help=t("cli.threads.filter_state_help"))
def threads(session: str, range_str: Optional[str], limit: int, filter_state: Optional[str]) -> None:
    """List threads"""
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
@click.option("--session", "-s", required=True, help=t("cli.bt.session_help"))
@click.option("--thread", "-t", "thread_id", type=int, help=t("cli.bt.thread_help"))
@click.option("--limit", default=30, help=t("cli.bt.limit_help"))
@click.option("--full", is_flag=True, help=t("cli.bt.full_help"))
@click.option("--range", "range_str", help=t("cli.bt.range_help"))
def bt(session: str, thread_id: Optional[int], limit: int, full: bool, range_str: Optional[str]) -> None:
    """Get backtrace"""
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
@click.option("--session", "-s", required=True, help=t("cli.frame.session_help"))
@click.argument("number", type=int)
def frame_cmd(session: str, number: int) -> None:
    """Select stack frame"""
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
@click.option("--session", "-s", required=True, help=t("cli.locals_cmd.session_help"))
@click.option("--thread", "-t", "thread_id", type=int, help=t("cli.locals_cmd.thread_help"))
@click.option("--frame", "-f", default=0, help=t("cli.locals_cmd.frame_help"))
def locals_cmd(session: str, thread_id: Optional[int], frame: int) -> None:
    """Get local variables"""
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
@click.option("--session", "-s", required=True, help=t("cli.exec.session_help"))
@click.argument("command")
@click.option("--safety-level", default="readonly", help=t("cli.exec.safety_level_help"))
def exec_cmd(session: str, command: str, safety_level: str) -> None:
    """Execute raw GDB command"""
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
@click.option("--session", "-s", required=True, help=t("cli.stop.session_help"))
def stop(session: str) -> None:
    """Stop session and safely exit GDB"""
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
    """List all active sessions"""
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
                "remote": s.remote,
                "core": s.core,
                "gdb_pid": s.gdb_pid,
                "started_at": s.started_at,
            }
            for s in session_list
        ],
        "count": len(session_list)
    }

    print_json(result)


@main.command()
@click.option("--session", "-s", required=True, help=t("cli.status.session_help"))
def status(session: str) -> None:
    """Check session status"""
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
@click.option("--session", "-s", required=True, help=t("cli.eval_element.session_help"))
@click.argument("expr")
@click.option("--index", "-i", required=True, type=int, help=t("cli.eval_element.index_help"))
@click.option("--max-depth", default=3, help=t("cli.eval_element.max_depth_help"))
def eval_element_cmd(session: str, expr: str, index: int, max_depth: int) -> None:
    """Access array/container element"""
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
@click.option("--session", "-s", required=True, help=t("cli.thread_apply.session_help"))
@click.argument("command")
@click.option("--threads", help=t("cli.thread_apply.threads_help"))
@click.option("--all", "all_threads", is_flag=True, help=t("cli.thread_apply.all_help"))
def thread_apply_cmd(session: str, command: str, threads: Optional[str], all_threads: bool) -> None:
    """Batch thread operations"""
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
@click.option("--session", "-s", required=True, help=t("cli.args.session_help"))
@click.option("--thread", "-t", "thread_id", type=int, help=t("cli.args.thread_help"))
@click.option("--frame", "-f", default=0, help=t("cli.args.frame_help"))
def args(session: str, thread_id: Optional[int], frame: int) -> None:
    """Get function arguments"""
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
@click.option("--session", "-s", required=True, help=t("cli.registers.session_help"))
@click.option("--names", "-n", help=t("cli.registers.names_help"))
@click.option("--thread", "-t", "thread_id", type=int, help=t("cli.registers.thread_help"))
@click.option("--frame", "-f", default=0, help=t("cli.registers.frame_help"))
def registers(session: str, names: Optional[str], thread_id: Optional[int], frame: int) -> None:
    """View register values"""
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
@click.option("--session", "-s", required=True, help=t("cli.memory.session_help"))
@click.argument("address")
@click.option("--size", default=64, help=t("cli.memory.size_help"))
@click.option("--fmt", default="hex", type=click.Choice(["hex", "bytes", "string"]), help=t("cli.memory.fmt_help"))
def memory(session: str, address: str, size: int, fmt: str) -> None:
    """Inspect memory content"""
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
@click.option("--session", "-s", required=True, help=t("cli.ptype.session_help"))
@click.argument("expr")
def ptype(session: str, expr: str) -> None:
    """View type information for expression"""
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
@click.option("--session", "-s", required=True, help=t("cli.thread_switch.session_help"))
@click.argument("thread_id", type=int)
def thread_switch_cmd(session: str, thread_id: int) -> None:
    """Switch current thread"""
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
@click.option("--session", "-s", required=True, help=t("cli.up.session_help"))
@click.argument("count", type=int, default=1)
def frame_up_cmd(session: str, count: int) -> None:
    """Move toward caller in stack"""
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
@click.option("--session", "-s", required=True, help=t("cli.down.session_help"))
@click.argument("count", type=int, default=1)
def frame_down_cmd(session: str, count: int) -> None:
    """Move toward callee in stack"""
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
@click.option("--session", "-s", required=True, help=t("cli.sharedlibs.session_help"))
def sharedlibs(session: str) -> None:
    """View loaded shared libraries"""
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
@click.option("--session", "-s", required=True, help=t("cli.disasm.session_help"))
@click.option("--start", help=t("cli.disasm.start_help"))
@click.option("--count", default=20, help=t("cli.disasm.count_help"))
@click.option("--thread", "-t", "thread_id", type=int, help=t("cli.disasm.thread_help"))
@click.option("--frame", "-f", default=0, help=t("cli.disasm.frame_help"))
def disasm(session: str, start: Optional[str], count: int, thread_id: Optional[int], frame: int) -> None:
    """Disassemble"""
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
    """Environment check: GDB version, ptrace permissions, Python version"""
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
