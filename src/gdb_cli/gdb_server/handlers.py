"""
Command Handlers - GDB 命令处理器

实现 eval、threads、bt、frame、locals、exec、status 等核心命令。
所有处理器在 GDB 主线程中通过 gdb.post_event() 调用。
"""

import os
from pathlib import Path
from typing import Any, List, Optional, Tuple

# GDB Python API - 仅在 GDB 环境中可用
try:
    import gdb
    GDB_AVAILABLE = True
except ImportError:
    GDB_AVAILABLE = False
    gdb = None  # type: ignore

# 动态加载 value_formatter（避免相对导入问题）
import importlib.util

_server_dir = os.environ.get("GDB_CLI_SERVER_DIR", "/tmp")
_value_formatter_path = Path(_server_dir) / "value_formatter.py"
_spec = importlib.util.spec_from_file_location("value_formatter", _value_formatter_path)
_value_formatter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_value_formatter)

format_gdb_value = _value_formatter.format_gdb_value
format_value_for_display = _value_formatter.format_value_for_display
DEFAULT_MAX_DEPTH = _value_formatter.DEFAULT_MAX_DEPTH
DEFAULT_MAX_ELEMENTS = _value_formatter.DEFAULT_MAX_ELEMENTS


def handle_eval(
    expr: str,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
    **kwargs
) -> dict:
    """
    求值 C/C++ 表达式

    Args:
        expr: 要求值的表达式
        max_depth: 递归深度限制
        max_elements: 数组元素限制

    Returns:
        {
            "expression": "...",
            "value": <formatted_value>,
            "type": "...",
            "address": "0x..." (if any)
        }
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        val = gdb.parse_and_eval(expr)
        return {
            "expression": expr,
            **format_value_for_display(val, max_depth=max_depth, max_elements=max_elements)
        }
    except gdb.error as e:
        return {"expression": expr, "error": f"GDB error: {e}"}
    except Exception as e:
        return {"expression": expr, "error": str(e)}


def handle_threads(
    range_str: Optional[str] = None,
    limit: int = 20,
    filter_state: Optional[str] = None,
    **kwargs
) -> dict:
    """
    列出线程，支持分页和过滤

    Args:
        range_str: 线程范围，如 "3-10"
        limit: 最大返回数量
        filter_state: 过滤状态 ("running", "stopped", etc.)

    Returns:
        {
            "threads": [...],
            "total_count": N,
            "truncated": bool,
            "current_thread": {"id": N, "name": "..."}
        }
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        inferior = gdb.selected_inferior()
        all_threads = list(inferior.threads())
        total_count = len(all_threads)

        # 解析范围
        if range_str:
            start, end = _parse_range(range_str)
            selected_threads = all_threads[start:end]
        else:
            selected_threads = all_threads

        # 过滤状态
        if filter_state:
            selected_threads = [
                t for t in selected_threads
                if _get_thread_state(t) == filter_state
            ]

        # 应用 limit
        truncated = len(selected_threads) > limit
        display_threads = selected_threads[:limit]

        # 格式化线程信息
        threads_data = []
        for t in display_threads:
            thread_info = _format_thread(t)
            threads_data.append(thread_info)

        # 获取当前线程
        current = gdb.selected_thread()
        current_info = _format_thread(current) if current else None

        result: dict = {
            "threads": threads_data,
            "total_count": total_count,
            "truncated": truncated
        }

        if current_info:
            result["current_thread"] = current_info

        if truncated:
            result["hint"] = "use 'threads --range START-END' for specific threads"

        return result

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def _parse_range(range_str: str) -> Tuple[int, int]:
    """解析范围字符串 '3-10' -> (2, 10)"""
    try:
        if "-" in range_str:
            parts = range_str.split("-")
            start = int(parts[0]) - 1  # 转为 0-indexed
            end = int(parts[1])
            return (max(0, start), end)
        else:
            idx = int(range_str) - 1
            return (idx, idx + 1)
    except Exception:
        return (0, 20)  # 默认返回前 20 个


def _get_thread_state(thread: 'gdb.InferiorThread') -> str:
    """获取线程状态"""
    try:
        if thread.is_running():
            return "running"
        elif thread.is_stopped():
            return "stopped"
        elif thread.is_exited():
            return "exited"
        else:
            return "unknown"
    except Exception:
        return "unknown"


def _format_thread(thread: 'gdb.InferiorThread') -> dict:
    """格式化单个线程信息"""
    try:
        result = {
            "id": thread.num,
            "global_id": thread.global_num,
            "state": _get_thread_state(thread)
        }

        # 尝试获取线程名
        try:
            name = thread.name
            if name:
                result["name"] = name
        except Exception:
            pass

        # 获取当前帧信息
        try:
            # 切换到该线程获取帧信息
            orig_thread = gdb.selected_thread()
            thread.switch()

            frame = gdb.newest_frame()
            if frame:
                result["frame"] = {
                    "function": frame.name() or "??",
                    "file": frame.sal().symtab.filename if frame.sal().symtab else None,
                    "line": frame.sal().line if frame.sal() else None
                }

            # 切回原线程
            if orig_thread:
                orig_thread.switch()
        except Exception:
            pass

        return result

    except Exception as e:
        return {"id": thread.num if hasattr(thread, 'num') else -1, "error": str(e)}


def handle_backtrace(
    thread_id: Optional[int] = None,
    limit: int = 30,
    full: bool = False,
    range_str: Optional[str] = None,
    **kwargs
) -> dict:
    """
    获取 backtrace

    Args:
        thread_id: 指定线程 ID (None = 当前线程)
        limit: 最大帧数
        full: 是否包含局部变量
        range_str: 帧范围，如 "5-15"

    Returns:
        {
            "frames": [...],
            "total_count": N,
            "truncated": bool,
            "thread_id": ...
        }
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        orig_thread = gdb.selected_thread()
        orig_frame = gdb.selected_frame()

        # 切换到指定线程
        if thread_id is not None:
            try:
                target_thread = None
                for t in gdb.selected_inferior().threads():
                    if t.num == thread_id:
                        target_thread = t
                        break
                if target_thread:
                    target_thread.switch()
                else:
                    return {"error": f"Thread {thread_id} not found"}
            except Exception as e:
                return {"error": f"Cannot switch to thread {thread_id}: {e}"}

        # 收集所有帧
        all_frames = []
        frame = gdb.newest_frame()
        while frame:
            all_frames.append(frame)
            frame = frame.older()

        total_count = len(all_frames)

        # 解析范围或应用 limit
        if range_str:
            start, end = _parse_range(range_str)
            display_frames = all_frames[start:end]
            truncated = end < total_count
        else:
            truncated = total_count > limit
            display_frames = all_frames[:limit]

        # 格式化帧
        frames_data = []
        for _i, frame in enumerate(display_frames):
            frame_info = _format_frame(frame, include_locals=full)
            frame_info["number"] = all_frames.index(frame)
            frames_data.append(frame_info)

        # 恢复原线程和帧
        try:
            if orig_thread:
                orig_thread.switch()
            if orig_frame:
                orig_frame.select()
        except Exception:
            pass

        result: dict = {
            "frames": frames_data,
            "total_count": total_count,
            "truncated": truncated
        }

        if thread_id is not None:
            result["thread_id"] = thread_id

        if truncated:
            result["hint"] = "use 'bt --range START-END' for specific frames"

        return result

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def _format_frame(frame: 'gdb.Frame', include_locals: bool = False) -> dict:
    """格式化单个栈帧"""
    result: dict = {
        "number": 0,  # 将在外部计算
        "function": frame.name() or "??",
        "address": hex(frame.pc())
    }

    # 源文件位置
    try:
        sal = frame.sal()
        if sal and sal.symtab:
            result["file"] = sal.symtab.filename
            result["line"] = sal.line
    except Exception:
        pass

    # 函数参数
    try:
        block = frame.block()
        if block:
            args = []
            for sym in block:
                if sym.is_argument:
                    try:
                        val = sym.value(frame)
                        args.append({
                            "name": sym.name,
                            "value": format_gdb_value(val, max_depth=1, max_elements=5)
                        })
                    except Exception:
                        args.append({"name": sym.name, "value": "<error>"})
            if args:
                result["args"] = args
    except Exception:
        pass

    # 局部变量
    if include_locals:
        try:
            locals_data = handle_locals_internal(frame)
            if locals_data:
                result["locals"] = locals_data
        except Exception:
            pass

    return result


def _select_frame_by_number(number: int) -> Any:
    """
    通过帧链遍历选择第 N 帧（替代 gdb.execute("frame N")）

    使用纯 Python API，线程安全。
    """
    frame = gdb.newest_frame()
    for _i in range(number):
        older = frame.older()
        if older is None:
            raise gdb.error("No frame number %d." % number)
        frame = older
    frame.select()
    return frame


def handle_frame_select(number: int, direction: Optional[str] = None, **kwargs) -> dict:
    """
    选择栈帧，支持绝对编号和相对移动（up/down）

    Args:
        number: 栈帧编号（direction=None 时为绝对编号，direction="up"/"down" 时为移动步数）
        direction: "up"（向调用者方向）/ "down"（向被调用者方向）/ None（绝对编号）

    Returns:
        {"frame": <selected_frame_info>}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        if direction == "up":
            # 向调用者方向移动 number 帧
            current = gdb.selected_frame()
            frame = current
            for _i in range(number):
                older = frame.older()
                if older is None:
                    break
                frame = older
            frame.select()
        elif direction == "down":
            # 向被调用者方向移动 number 帧
            current = gdb.selected_frame()
            frame = current
            for _i in range(number):
                newer = frame.newer()
                if newer is None:
                    break
                frame = newer
            frame.select()
        else:
            # 绝对编号
            frame = _select_frame_by_number(number)

        frame = gdb.selected_frame()
        frame_info = _format_frame(frame)
        # 计算当前帧编号
        f = gdb.newest_frame()
        idx = 0
        while f and f != frame:
            f = f.older()
            idx += 1
        frame_info["number"] = idx

        return {"frame": frame_info}

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def handle_locals(
    thread_id: Optional[int] = None,
    frame: int = 0,
    **kwargs
) -> dict:
    """
    获取局部变量

    Args:
        thread_id: 线程 ID (None = 当前)
        frame: 栈帧编号

    Returns:
        {"locals": [...]}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        orig_thread = gdb.selected_thread()
        orig_frame = gdb.selected_frame()

        # 切换到指定线程
        if thread_id is not None:
            try:
                target_thread = None
                for t in gdb.selected_inferior().threads():
                    if t.num == thread_id:
                        target_thread = t
                        break
                if target_thread:
                    target_thread.switch()
            except Exception:
                pass

        # 选择指定帧（使用帧链遍历，线程安全）
        selected = _select_frame_by_number(frame)

        locals_data = handle_locals_internal(selected)

        # 恢复
        try:
            if orig_thread:
                orig_thread.switch()
            if orig_frame:
                orig_frame.select()
        except Exception:
            pass

        return {"locals": locals_data, "frame": frame}

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def handle_locals_internal(frame: 'gdb.Frame') -> List[dict]:
    """内部函数：获取帧的局部变量"""
    locals_data = []

    try:
        block = frame.block()
        while block:
            for sym in block:
                if sym.is_argument or sym.is_variable:
                    # 跳过参数 (已在 frame 中显示)
                    if sym.is_argument:
                        continue
                    try:
                        val = sym.value(frame)
                        locals_data.append({
                            "name": sym.name,
                            "type": str(sym.type) if sym.type else "unknown",
                            "value": format_gdb_value(val, max_depth=2, max_elements=10)
                        })
                    except Exception as e:
                        locals_data.append({
                            "name": sym.name,
                            "error": str(e)
                        })
            # 处理外层作用域 (可选)
            # block = block.superblock
            break  # 只处理当前块

    except Exception as e:
        locals_data.append({"error": f"Cannot read locals: {e}"})

    return locals_data


def handle_exec(
    command: str,
    safety_level: str = "readonly",
    **kwargs
) -> dict:
    """
    执行原始 GDB 命令（经过安全过滤）

    Args:
        command: GDB 命令
        safety_level: 安全级别 ("readonly", "readwrite", "full")

    Returns:
        {"output": "...", "command": "..."}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    # 安全检查 (详细实现在 safety.py)
    # 这里先做基本检查
    dangerous_commands = ["quit", "kill", "shell", "python-interactive"]
    cmd_lower = command.lower().strip()

    for dangerous in dangerous_commands:
        if cmd_lower.startswith(dangerous):
            return {"error": f"Command '{dangerous}' is not allowed", "command": command}

    # 写操作检查
    write_commands = ["set", "call", "return"]
    if safety_level == "readonly":
        for write_cmd in write_commands:
            if cmd_lower.startswith(write_cmd):
                return {
                    "error": f"Command '{write_cmd}' requires --allow-write",
                    "command": command
                }

    try:
        output = gdb.execute(command, to_string=True)
        return {
            "command": command,
            "output": output or "(no output)"
        }
    except gdb.error as e:
        return {"command": command, "error": f"GDB error: {e}"}
    except Exception as e:
        return {"command": command, "error": str(e)}


def handle_status(**kwargs) -> dict:
    """
    返回 session 状态

    Returns:
        {
            "mode": "core" | "attach" | "target",
            "binary": "...",
            "threads_count": N,
            "current_thread": {...},
            "current_frame": {...}
        }
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    session_meta = kwargs.get("_session_meta", {})

    result: dict = {
        "state": "ready",
        "mode": session_meta.get("mode", "unknown"),
        "binary": session_meta.get("binary"),
        "gdb_pid": session_meta.get("gdb_pid"),
    }

    # 线程信息
    try:
        inferior = gdb.selected_inferior()
        threads = list(inferior.threads())
        result["threads_count"] = len(threads)
    except Exception:
        result["threads_count"] = 0

    # 当前线程
    try:
        current = gdb.selected_thread()
        if current:
            result["current_thread"] = {
                "id": current.num,
                "global_id": current.global_num
            }
    except Exception:
        pass

    # 当前帧
    try:
        frame = gdb.selected_frame()
        if frame:
            result["current_frame"] = {
                "function": frame.name(),
                "address": hex(frame.pc())
            }
    except Exception:
        pass

    # 进程信息 (attach 模式)
    if session_meta.get("mode") == "attach":
        result["pid"] = session_meta.get("pid")

    if session_meta.get("mode") == "target":
        result["remote"] = session_meta.get("remote")

    return result


def handle_eval_element(
    expr: str,
    index: int,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
    **kwargs
) -> dict:
    """
    访问数组/容器中的特定元素

    Args:
        expr: 数组/容器表达式
        index: 元素索引
        max_depth: 递归深度限制
        max_elements: 数组元素限制

    Returns:
        {"expression": "...", "index": N, "value": ...}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        # 先求值获取容器
        container = gdb.parse_and_eval(expr)

        # 尝试通过索引访问
        try:
            element = container[index]
            value = format_value_for_display(element, max_depth=max_depth, max_elements=max_elements)
            return {
                "expression": expr,
                "index": index,
                **value
            }
        except Exception:
            # 尝试其他访问方式 (如指针算术)
            try:
                # 假设是指针或数组
                addr = int(container)
                elem_type = container.type.target()
                elem_size = elem_type.sizeof
                target_addr = addr + index * elem_size

                # 创建指针并解引用
                ptr_type = elem_type.pointer()
                ptr = gdb.Value(target_addr).cast(ptr_type)
                element = ptr.dereference()

                value = format_value_for_display(element, max_depth=max_depth, max_elements=max_elements)
                return {
                    "expression": expr,
                    "index": index,
                    "address": hex(target_addr),
                    **value
                }
            except Exception as e:
                return {
                    "expression": expr,
                    "index": index,
                    "error": f"Cannot access element {index}: {e}"
                }

    except gdb.error as e:
        return {"expression": expr, "error": f"GDB error: {e}"}
    except Exception as e:
        return {"expression": expr, "error": str(e)}


def handle_thread_apply(
    command: str,
    thread_ids: Optional[str] = None,
    all_threads: bool = False,
    **kwargs
) -> dict:
    """
    批量线程操作

    Args:
        command: 要执行的命令 (如 "bt", "info registers")
        thread_ids: 线程 ID 列表 (如 "1,3,5" 或 "all")
        all_threads: 是否应用于所有线程

    Returns:
        {"results": [...], "thread_count": N}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        inferior = gdb.selected_inferior()
        all_threads_list = list(inferior.threads())

        # 确定目标线程
        if all_threads or thread_ids == "all":
            target_threads = all_threads_list
        elif thread_ids:
            # 解析线程 ID 列表
            ids = [int(x.strip()) for x in thread_ids.split(",")]
            target_threads = [t for t in all_threads_list if t.num in ids]
        else:
            return {"error": "Specify --all or --threads list"}

        results = []
        orig_thread = gdb.selected_thread()

        for thread in target_threads:
            try:
                thread.switch()
                output = gdb.execute(command, to_string=True)
                results.append({
                    "thread_id": thread.num,
                    "command": command,
                    "output": output or "(no output)"
                })
            except Exception as e:
                results.append({
                    "thread_id": thread.num,
                    "command": command,
                    "error": str(e)
                })

        # 恢复原线程
        if orig_thread:
            try:
                orig_thread.switch()
            except Exception:
                pass

        return {
            "results": results,
            "thread_count": len(target_threads),
            "command": command
        }

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def handle_args(
    thread_id: Optional[int] = None,
    frame: int = 0,
    **kwargs
) -> dict:
    """
    获取函数参数

    Args:
        thread_id: 线程 ID (None = 当前)
        frame: 栈帧编号

    Returns:
        {"args": [...], "function": "...", "frame": N}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        orig_thread = gdb.selected_thread()
        orig_frame = gdb.selected_frame()

        # 切换到指定线程
        if thread_id is not None:
            target_thread = None
            for t in gdb.selected_inferior().threads():
                if t.num == thread_id:
                    target_thread = t
                    break
            if target_thread:
                target_thread.switch()
            else:
                return {"error": "Thread %d not found" % thread_id}

        # 选择指定帧
        selected = _select_frame_by_number(frame)

        func_name = selected.name() or "??"
        args_data = []

        try:
            block = selected.block()
            if block:
                for sym in block:
                    if sym.is_argument:
                        try:
                            val = sym.value(selected)
                            args_data.append({
                                "name": sym.name,
                                "type": str(sym.type) if sym.type else "unknown",
                                "value": format_gdb_value(val, max_depth=2, max_elements=10)
                            })
                        except Exception as e:
                            args_data.append({"name": sym.name, "error": str(e)})
        except Exception as e:
            args_data.append({"error": f"Cannot read args: {e}"})

        # 恢复
        try:
            if orig_thread:
                orig_thread.switch()
            if orig_frame:
                orig_frame.select()
        except Exception:
            pass

        return {"args": args_data, "function": func_name, "frame": frame}

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def handle_registers(
    names: Optional[str] = None,
    thread_id: Optional[int] = None,
    frame: int = 0,
    **kwargs
) -> dict:
    """
    查看寄存器值

    Args:
        names: 寄存器名列表（逗号分隔），None 则返回常用寄存器
        thread_id: 线程 ID
        frame: 栈帧编号

    Returns:
        {"registers": [...], "frame": N}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    # 常用 x86_64 寄存器
    DEFAULT_REGS = [
        "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "rip",
        "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "eflags"
    ]

    try:
        orig_thread = gdb.selected_thread()
        orig_frame = gdb.selected_frame()

        # 切换线程
        if thread_id is not None:
            target_thread = None
            for t in gdb.selected_inferior().threads():
                if t.num == thread_id:
                    target_thread = t
                    break
            if target_thread:
                target_thread.switch()
            else:
                return {"error": "Thread %d not found" % thread_id}

        # 选择帧
        selected = _select_frame_by_number(frame)

        # 确定要读取的寄存器列表
        if names:
            reg_names = [n.strip() for n in names.split(",")]
        else:
            reg_names = DEFAULT_REGS

        regs_data = []
        for name in reg_names:
            try:
                val = selected.read_register(name)
                regs_data.append({
                    "name": name,
                    "value": hex(int(val)),
                    "decimal": int(val)
                })
            except Exception as e:
                regs_data.append({"name": name, "error": str(e)})

        # 恢复
        try:
            if orig_thread:
                orig_thread.switch()
            if orig_frame:
                orig_frame.select()
        except Exception:
            pass

        return {"registers": regs_data, "frame": frame}

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def handle_memory(
    address: str,
    size: int = 64,
    fmt: str = "hex",
    **kwargs
) -> dict:
    """
    检查内存内容（替代 x/Nxb ADDR）

    Args:
        address: 内存地址（十六进制字符串或表达式）
        size: 读取字节数（默认 64）
        fmt: 输出格式 "hex" / "bytes" / "string"

    Returns:
        {"address": "0x...", "size": N, "data": ...}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    addr = 0
    try:
        # 解析地址
        try:
            if address.startswith("0x") or address.startswith("0X"):
                addr = int(address, 16)
            else:
                val = gdb.parse_and_eval(address)
                addr = int(val)
        except Exception as e:
            return {"error": f"Cannot parse address '{address}': {e}"}

        # 限制大小
        max_size = 4096
        if size > max_size:
            size = max_size

        inferior = gdb.selected_inferior()
        mem = inferior.read_memory(addr, size)
        mem_bytes = bytes(mem)

        if fmt == "string":
            null_pos = mem_bytes.find(b'\x00')
            if null_pos >= 0:
                text = mem_bytes[:null_pos].decode("utf-8", errors="replace")
            else:
                text = mem_bytes.decode("utf-8", errors="replace")
            return {
                "address": f"0x{addr:x}",
                "size": len(text),
                "data": text,
                "format": "string"
            }
        elif fmt == "bytes":
            data = list(mem_bytes)
            return {
                "address": f"0x{addr:x}",
                "size": size,
                "data": data,
                "format": "bytes"
            }
        else:
            # 默认 hex，类似 xxd
            lines = []
            for offset in range(0, size, 16):
                chunk = mem_bytes[offset:offset + 16]
                hex_part = " ".join(f"{b:02x}" for b in chunk)
                ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                lines.append({
                    "offset": "0x%x" % (addr + offset),
                    "hex": hex_part,
                    "ascii": ascii_part
                })
            return {
                "address": f"0x{addr:x}",
                "size": size,
                "data": lines,
                "format": "hex"
            }

    except gdb.MemoryError as e:
        return {"error": f"Cannot access memory at 0x{addr:x}: {e}"}
    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def handle_ptype(
    expr: str,
    **kwargs
) -> dict:
    """
    查看表达式的类型信息（替代 ptype EXPR）

    Args:
        expr: C/C++ 表达式

    Returns:
        {"expression": "...", "type": "...", "sizeof": N, ...}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        val = gdb.parse_and_eval(expr)
        val_type = val.type

        result = {
            "expression": expr,
            "type": str(val_type),
            "code": str(val_type.code),
            "sizeof": val_type.sizeof,
        }

        # 剥离 typedef
        stripped = val_type.strip_typedefs()
        if str(stripped) != str(val_type):
            result["underlying_type"] = str(stripped)

        # 指针目标类型
        if val_type.code == gdb.TYPE_CODE_PTR:
            result["target_type"] = str(val_type.target())

        # 结构体/类字段列表
        if val_type.code in (gdb.TYPE_CODE_STRUCT, gdb.TYPE_CODE_UNION):
            fields = []
            try:
                for f in val_type.fields():
                    field_info = {
                        "name": f.name if f.name else "(anonymous)",
                        "type": str(f.type),
                        "offset": f.bitpos // 8 if hasattr(f, 'bitpos') and f.bitpos is not None else None,
                        "sizeof": f.type.sizeof
                    }
                    fields.append(field_info)
                result["fields"] = fields
                result["field_count"] = len(fields)
            except Exception:
                pass

        # 数组长度
        if val_type.code == gdb.TYPE_CODE_ARRAY:
            try:
                range_type = val_type.range()
                result["array_length"] = range_type[1] - range_type[0] + 1
                result["element_type"] = str(val_type.target())
            except Exception:
                pass

        # 枚举值
        if val_type.code == gdb.TYPE_CODE_ENUM:
            try:
                enumerators = []
                for f in val_type.fields():
                    enumerators.append({"name": f.name, "value": f.enumval})
                result["enumerators"] = enumerators
            except Exception:
                pass

        return result

    except gdb.error as e:
        return {"expression": expr, "error": f"GDB error: {e}"}
    except Exception as e:
        return {"expression": expr, "error": str(e)}


def handle_thread_switch(
    thread_id: int,
    **kwargs
) -> dict:
    """
    切换当前线程（替代 thread N）

    Args:
        thread_id: 目标线程 ID

    Returns:
        {"thread": {...}, "frame": {...}}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        target_thread = None
        for t in gdb.selected_inferior().threads():
            if t.num == thread_id:
                target_thread = t
                break

        if target_thread is None:
            return {"error": "Thread %d not found" % thread_id}

        target_thread.switch()

        # 返回切换后的线程和帧信息
        thread_info = _format_thread(target_thread)
        frame = gdb.selected_frame()
        frame_info = _format_frame(frame) if frame else None

        result = {"thread": thread_info}
        if frame_info:
            result["frame"] = frame_info

        return result

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def handle_sharedlibs(**kwargs) -> dict:
    """
    查看加载的共享库（替代 info sharedlibrary）

    Returns:
        {"libraries": [...], "count": N}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        libs = []
        for objfile in gdb.objfiles():
            lib_info = {
                "filename": objfile.filename,
            }
            try:
                lib_info["is_valid"] = objfile.is_valid()
            except Exception:
                pass
            try:
                if hasattr(objfile, 'build_id') and objfile.build_id:
                    lib_info["build_id"] = objfile.build_id
            except Exception:
                pass
            libs.append(lib_info)

        return {"libraries": libs, "count": len(libs)}

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def handle_disasm(
    start: Optional[str] = None,
    count: int = 20,
    thread_id: Optional[int] = None,
    frame: int = 0,
    **kwargs
) -> dict:
    """
    反汇编（替代 disassemble）

    Args:
        start: 起始地址或函数名（None = 当前 PC）
        count: 指令数量（默认 20）
        thread_id: 线程 ID
        frame: 栈帧编号

    Returns:
        {"instructions": [...], "function": "...", "count": N}
    """
    if not GDB_AVAILABLE:
        return {"error": "GDB not available"}

    try:
        orig_thread = gdb.selected_thread()
        orig_frame = gdb.selected_frame()

        # 切换线程
        if thread_id is not None:
            target_thread = None
            for t in gdb.selected_inferior().threads():
                if t.num == thread_id:
                    target_thread = t
                    break
            if target_thread:
                target_thread.switch()
            else:
                return {"error": "Thread %d not found" % thread_id}

        # 选择帧
        selected = _select_frame_by_number(frame)
        arch = selected.architecture()

        # 确定起始地址
        if start:
            try:
                if start.startswith("0x") or start.startswith("0X"):
                    start_pc = int(start, 16)
                else:
                    val = gdb.parse_and_eval(start)
                    start_pc = int(val)
            except Exception:
                try:
                    val = gdb.parse_and_eval(f"(void*){start}")
                    start_pc = int(val)
                except Exception as e:
                    return {"error": f"Cannot resolve address '{start}': {e}"}
        else:
            start_pc = selected.pc()

        func_name = selected.name() or "??"

        # 限制数量
        if count > 200:
            count = 200

        # 反汇编
        instructions = arch.disassemble(start_pc, count=count)

        insn_data = []
        for insn in instructions:
            insn_data.append({
                "address": "0x{:x}".format(insn["addr"]),
                "asm": insn["asm"],
                "length": insn.get("length", 0)
            })

        # 恢复
        try:
            if orig_thread:
                orig_thread.switch()
            if orig_frame:
                orig_frame.select()
        except Exception:
            pass

        result = {
            "instructions": insn_data,
            "function": func_name,
            "start_address": f"0x{start_pc:x}",
            "count": len(insn_data)
        }

        if len(insn_data) >= count:
            last_addr = instructions[-1]["addr"]
            result["hint"] = "use 'disasm --start 0x%x' to continue" % (last_addr + 1)

        return result

    except gdb.error as e:
        return {"error": f"GDB error: {e}"}
    except Exception as e:
        return {"error": str(e)}
