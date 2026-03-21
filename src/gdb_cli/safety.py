"""
Safety Module - 命令安全过滤

实现命令白名单过滤，区分不同安全级别。
"""


from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set, Tuple


class SafetyLevel(Enum):
    """安全级别"""
    READONLY = "readonly"      # 只读模式，只允许读取命令
    READWRITE = "readwrite"    # 读写模式，允许内存修改
    FULL = "full"              # 完全模式，允许函数调用


@dataclass
class CommandCheckResult:
    """命令检查结果"""
    allowed: bool
    category: str
    reason: Optional[str] = None
    requires_confirmation: bool = False


# 读取类命令（所有模式都允许）
READONLY_COMMANDS: Set[str] = {
    "bt", "backtrace", "info", "thread", "threads",
    "print", "p", "x", "ptype", "whatis",
    "frame", "up", "down", "select-frame",
    "list", "disassemble", "source",
    "show", "help", "pwd", "directory",
}

# 导航类命令（所有模式都允许）
NAVIGATION_COMMANDS: Set[str] = {
    "frame", "up", "down", "thread",
}

# 执行控制类命令（需要确认）
EXECUTION_COMMANDS: Set[str] = {
    "continue", "c", "step", "s", "next", "n",
    "finish", "until", "advance", "run", "start",
}

# 写入类命令（需要 READWRITE 或 FULL 模式）
WRITE_COMMANDS: Set[str] = {
    "set", "assign",
}

# 函数调用类命令（需要 FULL 模式）
CALL_COMMANDS: Set[str] = {
    "call",
}

# 始终禁止的命令
FORBIDDEN_COMMANDS: Set[str] = {
    "quit", "kill", "shell", "python-interactive",
    "signal", "detach", "attach",
}

# 命令别名映射
COMMAND_ALIASES = {
    "p": "print",
    "bt": "backtrace",
    "c": "continue",
    "s": "step",
    "n": "next",
    "f": "finish",
    "i": "info",
}


class SafetyFilter:
    """命令安全过滤器"""

    def __init__(self, level: SafetyLevel = SafetyLevel.READONLY):
        self.level = level

    def check_command(self, command: str) -> CommandCheckResult:
        """
        检查命令是否允许执行

        Args:
            command: GDB 命令字符串

        Returns:
            CommandCheckResult 检查结果
        """
        # 提取命令动词
        cmd_verb = self._extract_command_verb(command)
        cmd_lower = cmd_verb.lower()

        # 处理别名
        cmd_normalized = COMMAND_ALIASES.get(cmd_lower, cmd_lower)

        # 检查禁止命令
        if cmd_normalized in FORBIDDEN_COMMANDS or cmd_lower in FORBIDDEN_COMMANDS:
            return CommandCheckResult(
                allowed=False,
                category="forbidden",
                reason=f"Command '{cmd_verb}' is not allowed for safety reasons"
            )

        # 检查函数调用命令
        if cmd_normalized in CALL_COMMANDS or cmd_lower in CALL_COMMANDS:
            if self.level == SafetyLevel.FULL:
                return CommandCheckResult(
                    allowed=True,
                    category="call",
                    requires_confirmation=True
                )
            return CommandCheckResult(
                allowed=False,
                category="call",
                reason=f"Command '{cmd_verb}' requires --allow-call flag"
            )

        # 检查写入命令
        if cmd_normalized in WRITE_COMMANDS or cmd_lower in WRITE_COMMANDS:
            if self.level in (SafetyLevel.READWRITE, SafetyLevel.FULL):
                return CommandCheckResult(
                    allowed=True,
                    category="write"
                )
            return CommandCheckResult(
                allowed=False,
                category="write",
                reason=f"Command '{cmd_verb}' requires --allow-write flag"
            )

        # 检查执行控制命令
        if cmd_normalized in EXECUTION_COMMANDS or cmd_lower in EXECUTION_COMMANDS:
            return CommandCheckResult(
                allowed=True,
                category="execution",
                requires_confirmation=True
            )

        # 读取和导航命令始终允许
        if cmd_normalized in READONLY_COMMANDS or cmd_lower in READONLY_COMMANDS:
            return CommandCheckResult(
                allowed=True,
                category="readonly"
            )

        if cmd_normalized in NAVIGATION_COMMANDS or cmd_lower in NAVIGATION_COMMANDS:
            return CommandCheckResult(
                allowed=True,
                category="navigation"
            )

        # 未知命令 - 根据安全级别决定
        if self.level == SafetyLevel.FULL:
            return CommandCheckResult(
                allowed=True,
                category="unknown"
            )

        return CommandCheckResult(
            allowed=False,
            category="unknown",
            reason=f"Unknown command '{cmd_verb}' is not allowed in {self.level.value} mode"
        )

    def _extract_command_verb(self, command: str) -> str:
        """提取命令动词"""
        command = command.strip()
        if not command:
            return ""

        # 处理带参数的命令
        parts = command.split()
        if not parts:
            return ""

        return parts[0]

    def filter_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        过滤命令

        Args:
            command: GDB 命令

        Returns:
            (allowed, error_message)
        """
        result = self.check_command(command)
        return result.allowed, result.reason


def is_command_allowed(command: str, level: str = "readonly") -> bool:
    """
    检查命令是否允许（便捷函数）

    Args:
        command: GDB 命令
        level: 安全级别

    Returns:
        是否允许
    """
    try:
        safety_level = SafetyLevel(level)
    except ValueError:
        safety_level = SafetyLevel.READONLY

    filter = SafetyFilter(safety_level)
    result = filter.check_command(command)
    return result.allowed


def classify_command(command: str) -> str:
    """
    分类命令

    Args:
        command: GDB 命令

    Returns:
        命令类别
    """
    filter = SafetyFilter(SafetyLevel.FULL)
    result = filter.check_command(command)
    return result.category
