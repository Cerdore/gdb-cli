"""
Error Classification - 错误分类和处理

区分 user_error / gdb_error / internal_error，给 AI 可操作建议。
统一错误响应格式。
"""


from enum import Enum
from typing import Any, Optional, Tuple

from .i18n import t


class ErrorType(Enum):
    """错误类型枚举"""
    USER_ERROR = "user_error"        # 用户输入错误（表达式语法错误、变量不存在等）
    GDB_ERROR = "gdb_error"          # GDB 内部错误（内存访问失败、进程不存在等）
    INTERNAL_ERROR = "internal_error" # 程序内部错误（代码 bug、未预期异常）
    PERMISSION_ERROR = "permission_error"  # 权限错误（ptrace、命令白名单等）
    TIMEOUT_ERROR = "timeout_error"  # 超时错误
    CONNECTION_ERROR = "connection_error"  # 连接错误


class GDBCLIError(Exception):
    """GDB CLI 基础错误类"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.INTERNAL_ERROR,
        suggestion: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.message = message
        self.error_type = error_type
        self.suggestion = suggestion
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {
            "error": self.message,
            "error_type": self.error_type.value,
        }
        if self.suggestion:
            result["suggestion"] = self.suggestion
        if self.details:
            result["details"] = self.details
        return result


class UserError(GDBCLIError):
    """用户输入错误"""

    def __init__(self, message: str, suggestion: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.USER_ERROR,
            suggestion=suggestion,
            details=details
        )


class GDBError(GDBCLIError):
    """GDB 内部错误"""

    def __init__(self, message: str, suggestion: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.GDB_ERROR,
            suggestion=suggestion,
            details=details
        )


class PermissionError(GDBCLIError):
    """权限错误"""

    def __init__(self, message: str, suggestion: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.PERMISSION_ERROR,
            suggestion=suggestion,
            details=details
        )


class TimeoutError(GDBCLIError):
    """超时错误"""

    def __init__(self, message: str, suggestion: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.TIMEOUT_ERROR,
            suggestion=suggestion,
            details=details
        )


class ConnectionError(GDBCLIError):
    """连接错误"""

    def __init__(self, message: str, suggestion: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_type=ErrorType.CONNECTION_ERROR,
            suggestion=suggestion,
            details=details
        )



def classify_gdb_error(error_message: str) -> Tuple[ErrorType, Optional[str]]:
    """
    根据错误消息分类错误类型

    Args:
        error_message: GDB 错误消息

    Returns:
        (error_type, suggestion)
    """
    error_lower = error_message.lower()

    # 用户错误
    if any(x in error_lower for x in ["no symbol", "not found", "undefined"]):
        return ErrorType.USER_ERROR, t("errors.variable_not_found.suggestion")
    if "syntax error" in error_lower:
        return ErrorType.USER_ERROR, t("errors.syntax_error.suggestion")
    if "invalid thread" in error_lower:
        return ErrorType.USER_ERROR, t("errors.invalid_thread.suggestion")
    if "invalid frame" in error_lower:
        return ErrorType.USER_ERROR, t("errors.invalid_frame.suggestion")

    # GDB 错误
    if any(x in error_lower for x in ["cannot access memory", "memory not accessible"]):
        return ErrorType.GDB_ERROR, t("errors.memory_access_failed.suggestion")
    if "no debugging symbols" in error_lower:
        return ErrorType.GDB_ERROR, t("errors.no_debug_info.suggestion")
    if "process" in error_lower and ("not found" in error_lower or "does not exist" in error_lower):
        return ErrorType.GDB_ERROR, t("errors.process_not_found.suggestion")

    # 默认内部错误
    return ErrorType.INTERNAL_ERROR, None


def format_error_response(
    error: Exception,
    command: Optional[str] = None,
    context: Optional[dict] = None
) -> dict:
    """
    格式化错误响应

    Args:
        error: 异常对象
        command: 相关命令
        context: 额外上下文

    Returns:
        标准错误响应字典
    """
    if isinstance(error, GDBCLIError):
        result = error.to_dict()
    else:
        # 分类未知错误
        error_type, suggestion = classify_gdb_error(str(error))
        result = {
            "error": str(error),
            "error_type": error_type.value,
        }
        if suggestion:
            result["suggestion"] = suggestion

    if command:
        result["command"] = command

    if context:
        result["context"] = context

    return result


def format_success_response(
    data: Any,
    truncated: bool = False,
    hint: Optional[str] = None
) -> dict:
    """
    格式化成功响应

    Args:
        data: 响应数据
        truncated: 是否被截断
        hint: 提示信息

    Returns:
        标准成功响应字典
    """
    result = {"ok": True, "data": data}
    if truncated:
        result["truncated"] = True
    if hint:
        result["hint"] = hint
    return result
