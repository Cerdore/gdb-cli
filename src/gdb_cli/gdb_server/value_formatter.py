# -*- coding: utf-8 -*-
"""
Value Formatter - gdb.Value → JSON 递归序列化

将 GDB 的 gdb.Value 对象转换为 JSON-safe Python 对象，
支持基本类型、指针、结构体、数组，并提供截断和 hint 功能。
"""

from typing import Any, Optional

# GDB Python API - 仅在 GDB 环境中可用
try:
    import gdb
    GDB_AVAILABLE = True
except ImportError:
    GDB_AVAILABLE = False
    gdb = None  # type: ignore


def _safe_str(val: 'gdb.Value') -> str:
    """
    安全地将 gdb.Value 转为字符串，避免触发 pretty printer（非线程安全）。
    优先用 format_string(raw=True)，失败则返回占位文本。
    """
    try:
        return val.format_string(raw=True)
    except Exception:
        try:
            return hex(int(val))
        except Exception:
            return "<cannot format>"


# 默认截断配置
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_ELEMENTS = 50
DEFAULT_MAX_STRING_LEN = 1000
DEFAULT_MAX_FIELDS = 100


def format_gdb_value(
    val: 'gdb.Value',
    depth: int = 0,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
    max_string_len: int = DEFAULT_MAX_STRING_LEN,
    max_fields: int = DEFAULT_MAX_FIELDS
) -> Any:
    """
    递归将 gdb.Value 转为 JSON-safe Python 对象

    Args:
        val: GDB Value 对象
        depth: 当前递归深度
        max_depth: 最大递归深度
        max_elements: 数组/容器最大元素数
        max_string_len: 字符串最大长度
        max_fields: 结构体最大字段数

    Returns:
        JSON-safe Python 对象:
        - 基本类型 → int/float/str/bool/None
        - 指针 → {"type": "pointer", "address": "0x...", "deref": ...}
        - 结构体 → {"type": "struct", "name": "...", "fields": {...}}
        - 数组 → {"type": "array", "length": N, "elements": [...], "truncated": bool}
    """
    if not GDB_AVAILABLE:
        raise RuntimeError("format_gdb_value requires GDB Python API")

    # 达到最大深度，返回类型摘要
    if depth >= max_depth:
        return _format_type_summary(val)

    # 处理 None/void
    if val is None:
        return None

    try:
        val_type = val.type
    except Exception:
        return {"type": "error", "message": "Cannot determine type"}

    # 移除 typedef 和 cv-qualifier
    target_type = val_type.strip_typedefs()

    # 基本类型
    if target_type.code == gdb.TYPE_CODE_INT:
        return _format_int(val, target_type)
    elif target_type.code == gdb.TYPE_CODE_BOOL:
        return bool(val)
    elif target_type.code == gdb.TYPE_CODE_FLOAT:
        return float(val)
    elif target_type.code == gdb.TYPE_CODE_VOID:
        return None
    elif target_type.code == gdb.TYPE_CODE_ENUM:
        return _format_enum(val, target_type)

    # 字符串和字符
    elif target_type.code == gdb.TYPE_CODE_CHAR:
        return chr(int(val))
    elif target_type.code == gdb.TYPE_CODE_ARRAY:
        # 检查是否是 char[] (C 字符串)
        elem_type = target_type.target()
        if elem_type and elem_type.code == gdb.TYPE_CODE_CHAR:
            return _format_c_string(val, max_string_len)
        return _format_array(val, depth, max_depth, max_elements, max_string_len, max_fields)

    # 指针
    elif target_type.code == gdb.TYPE_CODE_PTR:
        return _format_pointer(val, depth, max_depth, max_elements, max_string_len, max_fields)

    # 引用
    elif target_type.code == gdb.TYPE_CODE_REF:
        try:
            return format_gdb_value(
                val.referenced_value(),
                depth=depth,
                max_depth=max_depth,
                max_elements=max_elements,
                max_string_len=max_string_len,
                max_fields=max_fields
            )
        except Exception:
            return {"type": "reference", "error": "Cannot dereference"}

    # 结构体/类
    elif target_type.code in (gdb.TYPE_CODE_STRUCT, gdb.TYPE_CODE_UNION):
        return _format_struct(val, target_type, depth, max_depth, max_elements, max_string_len, max_fields)

    # 函数指针
    elif target_type.code == gdb.TYPE_CODE_FUNC:
        return {"type": "function", "name": str(target_type)}

    # 数组类型 (未实例化)
    elif target_type.code == gdb.TYPE_CODE_TYPEDEF:
        return format_gdb_value(
            val.cast(target_type.strip_typedefs()),
            depth=depth,
            max_depth=max_depth,
            max_elements=max_elements,
            max_string_len=max_string_len,
            max_fields=max_fields
        )

    # 未知类型
    else:
        return {"type": "unknown", "type_code": str(target_type.code), "value": _safe_str(val)}


def _format_int(val: 'gdb.Value', val_type: 'gdb.Type') -> int:
    """格式化整数，处理 signed/unsigned"""
    try:
        # is_unsigned() 仅 GDB 14.1+ 可用，安全检查
        if hasattr(val_type, 'is_unsigned') and val_type.is_unsigned():
            int_val = int(val)
            if int_val > 2**63:
                return int_val  # Python 支持大整数
            return int_val
        return int(val)
    except Exception:
        return _safe_str(val)


def _format_enum(val: 'gdb.Value', val_type: 'gdb.Type') -> dict:
    """格式化枚举值"""
    try:
        # 尝试获取枚举名称
        int_val = int(val)
        for field in val_type.fields():
            if hasattr(field, 'enumval') and field.enumval == int_val:
                return {
                    "type": "enum",
                    "name": field.name,
                    "value": int_val
                }
        return {"type": "enum", "value": int_val}
    except Exception:
        return {"type": "enum", "value": int(val)}


def _format_c_string(val: 'gdb.Value', max_len: int) -> str:
    """格式化 C 字符串 (char[])"""
    try:
        # 使用 gdb.execute 获取字符串内容
        # 或者尝试直接转换为 Python string
        result = val.string(encoding="utf-8", errors="replace", length=max_len + 1)
        if len(result) > max_len:
            return result[:max_len] + "..."
        return result
    except Exception:
        # 回退到逐字节读取
        try:
            chars = []
            addr = int(val.address) if val.address else 0
            for i in range(min(max_len, 1000)):
                byte_val = gdb.parse_and_eval(f"((char*){addr})[{i}]")
                byte = int(byte_val) & 0xFF
                if byte == 0:
                    break
                chars.append(chr(byte) if 32 <= byte < 127 else f"\\x{byte:02x}")
            result = "".join(chars)
            if len(chars) >= max_len:
                return result + "..."
            return result
        except Exception:
            return _safe_str(val)


def _format_array(
    val: 'gdb.Value',
    depth: int,
    max_depth: int,
    max_elements: int,
    max_string_len: int,
    max_fields: int
) -> dict:
    """格式化数组"""
    try:
        array_type = val.type
        # 尝试获取数组长度
        try:
            length = array_type.sizeof // array_type.target().sizeof
        except Exception:
            length = max_elements  # 未知长度，使用限制

        truncated = length > max_elements
        actual_len = min(length, max_elements)

        elements = []
        for i in range(actual_len):
            try:
                elem = val[i]
                elements.append(format_gdb_value(
                    elem,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_elements=max_elements,
                    max_string_len=max_string_len,
                    max_fields=max_fields
                ))
            except Exception as e:
                elements.append({"index": i, "error": str(e)})

        result: dict = {
            "type": "array",
            "length": length,
            "elements": elements,
            "truncated": truncated
        }

        if truncated:
            result["hint"] = f"use 'eval-element --index N' to access specific element (0-{length-1})"

        return result

    except Exception as e:
        return {"type": "array", "error": str(e)}


def _format_pointer(
    val: 'gdb.Value',
    depth: int,
    max_depth: int,
    max_elements: int,
    max_string_len: int,
    max_fields: int
) -> dict:
    """格式化指针"""
    try:
        addr = int(val)
        target_type = val.type.target()

        result: dict = {
            "type": "pointer",
            "address": hex(addr),
            "target_type": str(target_type)
        }

        # 空指针
        if addr == 0:
            result["value"] = "NULL"
            return result

        # void* 只显示地址
        if target_type.code == gdb.TYPE_CODE_VOID:
            result["value"] = "void*"
            return result

        # char* 作为字符串处理
        if target_type.code == gdb.TYPE_CODE_CHAR:
            try:
                str_val = val.string(encoding="utf-8", errors="replace", length=max_string_len)
                if len(str_val) >= max_string_len:
                    str_val = str_val[:max_string_len] + "..."
                result["string"] = str_val
            except Exception:
                pass
            return result

        # 尝试解引用
        if depth + 1 < max_depth:
            try:
                deref = val.dereference()
                result["deref"] = format_gdb_value(
                    deref,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_elements=max_elements,
                    max_string_len=max_string_len,
                    max_fields=max_fields
                )
            except gdb.MemoryError:
                result["deref_error"] = "Cannot access memory"
            except Exception as e:
                result["deref_error"] = str(e)

        return result

    except Exception as e:
        return {"type": "pointer", "error": str(e)}


def _format_struct(
    val: 'gdb.Value',
    val_type: 'gdb.Type',
    depth: int,
    max_depth: int,
    max_elements: int,
    max_string_len: int,
    max_fields: int
) -> dict:
    """格式化结构体/类"""
    try:
        type_name = val_type.name or str(val_type.tag) if val_type.tag else "<anonymous>"
        result: dict = {
            "type": "struct",
            "name": type_name
        }

        # 收集字段
        fields = {}
        try:
            for i, field in enumerate(val_type.fields()):
                if i >= max_fields:
                    result["truncated"] = True
                    result["hint"] = f"showing first {max_fields} fields, use specific field access for more"
                    break

                field_name = field.name
                if not field_name:
                    # 匿名字段/基类
                    field_name = f"<anon_{i}>"

                try:
                    field_val = val[field_name]
                    fields[field_name] = format_gdb_value(
                        field_val,
                        depth=depth + 1,
                        max_depth=max_depth,
                        max_elements=max_elements,
                        max_string_len=max_string_len,
                        max_fields=max_fields
                    )
                except Exception as e:
                    fields[field_name] = {"error": str(e)}

        except Exception as e:
            result["fields_error"] = str(e)

        result["fields"] = fields
        return result

    except Exception as e:
        return {"type": "struct", "error": str(e)}


def _format_type_summary(val: 'gdb.Value') -> dict:
    """当达到最大深度时，返回类型摘要"""
    try:
        val_type = val.type.strip_typedefs()
        return {
            "type": "truncated",
            "type_name": str(val_type),
            "summary": f"<{val_type}, max depth reached>"
        }
    except Exception:
        return {"type": "truncated", "summary": _safe_str(val)}


def format_value_for_display(
    val: 'gdb.Value',
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_elements: int = DEFAULT_MAX_ELEMENTS
) -> dict:
    """
    格式化值用于显示，包装为标准响应格式

    Returns:
        {
            "value": <formatted_value>,
            "type": <原始类型字符串>,
            "size": <字节大小>,
            "address": <地址或 null>
        }
    """
    result: dict = {
        "value": format_gdb_value(val, max_depth=max_depth, max_elements=max_elements),
        "type": str(val.type) if val.type else "unknown"
    }

    try:
        result["size"] = val.type.sizeof
    except Exception:
        pass

    try:
        if val.address:
            result["address"] = hex(int(val.address))
    except Exception:
        pass

    return result