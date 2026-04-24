"""
Environment Check - 环境自检模块

检测：
- ptrace 权限
- GDB 版本
- debuginfo 状态
- 符号路径辅助

TODO(i18n): ~15 hardcoded English strings in this module are not yet wired to t().
Catalog keys (env_check.*) are defined and ready. See issue #1.
"""


import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# 版本要求
MIN_GDB_VERSION = (9, 0)
RECOMMENDED_GDB_VERSION = (15, 0)


@dataclass
class EnvironmentReport:
    """环境检查报告"""
    ready: bool = True
    python_version: str = ""
    platform: str = ""
    gdb_path: Optional[str] = None
    gdb_version: Optional[str] = None
    gdb_supported: bool = False
    gdb_recommended: bool = False
    ptrace_scope: Optional[int] = None
    ptrace_allowed: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class DebuginfoReport:
    """Debuginfo 检查报告"""
    binary_path: str
    has_debuginfo: bool = False
    stripped: bool = False
    partial: bool = False
    debug_sections: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


def check_environment(gdb_path=None) -> EnvironmentReport:
    """
    执行完整的环境检查

    Returns:
        EnvironmentReport 环境报告
    """
    report = EnvironmentReport(
        python_version=platform.python_version(),
        platform=f"{platform.system()} {platform.release()}"
    )

    # 检查 GDB
    _check_gdb(report, gdb_path=gdb_path)

    # 检查 ptrace (Linux only)
    if platform.system() == "Linux":
        _check_ptrace(report)

    # 判断是否就绪
    report.ready = (
        report.gdb_supported and
        report.ptrace_allowed and
        len(report.errors) == 0
    )

    return report


def _check_gdb(report: EnvironmentReport, gdb_path=None) -> None:
    """检查 GDB 版本"""
    if gdb_path is None:
        gdb_path = shutil.which("gdb")

    if not gdb_path:
        report.gdb_path = None
        report.errors.append("GDB not found in PATH")
        report.suggestions.append("Install GDB: 'brew install gdb' (macOS) or 'yum install gdb' (Linux)")
        report.gdb_supported = False
        return

    report.gdb_path = gdb_path

    try:
        result = subprocess.run(
            [gdb_path, "--version"],
            capture_output=True, text=True,
            timeout=10
        )
        version_str = result.stdout

        # 提取版本号
        match = re.search(r"GNU gdb.*?(\d+)\.(\d+)", version_str)
        if match:
            major, minor = int(match.group(1)), int(match.group(2))
            report.gdb_version = f"{major}.{minor}"

            # 检查版本是否满足要求
            report.gdb_supported = (major, minor) >= MIN_GDB_VERSION
            report.gdb_recommended = (major, minor) >= RECOMMENDED_GDB_VERSION

            if not report.gdb_supported:
                report.errors.append(
                    f"GDB version {major}.{minor} is below minimum {MIN_GDB_VERSION[0]}.{MIN_GDB_VERSION[1]}"
                )
                report.suggestions.append("Upgrade GDB to version 9.0 or later")
            elif not report.gdb_recommended:
                report.warnings.append(
                    f"GDB version {major}.{minor} is supported but {RECOMMENDED_GDB_VERSION[0]}.{RECOMMENDED_GDB_VERSION[1]}+ is recommended"
                )
                report.suggestions.append("Consider upgrading to GDB 15+ for best compatibility with rockylinux/el9")
        else:
            report.gdb_version = "unknown"
            report.warnings.append("Could not parse GDB version")

    except subprocess.TimeoutExpired:
        report.errors.append("GDB version check timed out")
    except Exception as e:
        report.errors.append(f"Error checking GDB: {e}")


def _check_ptrace(report: EnvironmentReport) -> None:
    """检查 ptrace 权限"""
    ptrace_path = Path("/proc/sys/kernel/yama/ptrace_scope")

    if not ptrace_path.exists():
        # 文件不存在可能意味着系统不支持 YAMA，通常允许 ptrace
        report.ptrace_scope = None
        report.ptrace_allowed = True
        return

    try:
        scope_str = ptrace_path.read_text().strip()
        scope = int(scope_str)
        report.ptrace_scope = scope

        if scope == 0:
            report.ptrace_allowed = True
        elif scope == 1:
            report.ptrace_allowed = True  # 可以 attach 子进程
            report.warnings.append("ptrace is restricted (scope=1). Can only attach to child processes.")
        else:
            report.ptrace_allowed = False
            report.errors.append(f"ptrace is heavily restricted (scope={scope})")
            report.suggestions.append(
                "Run: echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope"
            )
            report.suggestions.append(
                "Or run: sysctl kernel.yama.ptrace_scope=0"
            )

    except PermissionError:
        report.warnings.append("Cannot read ptrace_scope (permission denied)")
        report.ptrace_allowed = True  # 假设允许
    except Exception as e:
        report.warnings.append(f"Error checking ptrace: {e}")
        report.ptrace_allowed = True  # 假设允许


def check_debuginfo(binary_path: str) -> DebuginfoReport:
    """
    检查二进制文件的 debuginfo 状态

    Args:
        binary_path: 二进制文件路径

    Returns:
        DebuginfoReport 检查报告
    """
    report = DebuginfoReport(binary_path=binary_path)

    binary = Path(binary_path)
    if not binary.exists():
        report.suggestions.append(f"Binary not found: {binary_path}")
        return report

    # 检查 readelf 是否可用
    readelf = shutil.which("readelf")
    if not readelf:
        # 尝试使用 objdump
        objdump = shutil.which("objdump")
        if objdump:
            return _check_debuginfo_objdump(binary_path, report)
        report.suggestions.append("readelf or objdump not found, cannot check debuginfo")
        return report

    try:
        result = subprocess.run(
            [readelf, "-S", binary_path],
            capture_output=True, text=True,
            timeout=30
        )

        output = result.stdout
        debug_sections = []

        # 查找 debug sections
        for line in output.split("\n"):
            if ".debug" in line or ".zdebug" in line:
                # 提取 section 名称
                match = re.search(r'\.z?debug[_-]?(\w+)', line)
                if match:
                    debug_sections.append(f".debug_{match.group(1)}")

        if debug_sections:
            report.has_debuginfo = True
            report.debug_sections = debug_sections

            # 检查是否完整（至少有 .debug_info 和 .debug_line）
            required = {".debug_info", ".debug_line"}
            found = set(debug_sections)
            if not required.issubset(found):
                report.partial = True
                report.warnings = getattr(report, 'warnings', [])
                report.warnings.append(f"Partial debug info: missing {required - found}")
        else:
            report.stripped = True
            _suggest_debuginfo_sources(binary_path, report)

    except subprocess.TimeoutExpired:
        report.suggestions.append("readelf timed out")
    except Exception as e:
        report.suggestions.append(f"Error checking debuginfo: {e}")

    return report


def _check_debuginfo_objdump(binary_path: str, report: DebuginfoReport) -> DebuginfoReport:
    """使用 objdump 检查 debuginfo"""
    objdump = shutil.which("objdump")

    try:
        result = subprocess.run(
            [objdump, "-h", binary_path],
            capture_output=True, text=True,
            timeout=30
        )

        output = result.stdout
        if ".debug" in output:
            report.has_debuginfo = True
        else:
            report.stripped = True
            _suggest_debuginfo_sources(binary_path, report)

    except Exception as e:
        report.suggestions.append(f"Error checking debuginfo with objdump: {e}")

    return report


def _suggest_debuginfo_sources(binary_path: str, report: DebuginfoReport) -> None:
    """建议 debuginfo 来源"""
    binary = Path(binary_path)
    binary_name = binary.name

    # 检查常见的 debuginfo 位置
    possible_debug_paths = [
        f"/usr/lib/debug{binary.parent}/.debug/{binary_name}.debug",
        f"/usr/lib/debug{binary.parent}/{binary_name}.debug",
        f"{binary.parent}/.debug/{binary_name}.debug",
        f"{binary_name}.debug",
    ]

    for debug_path in possible_debug_paths:
        if Path(debug_path).exists():
            report.suggestions.append(f"Found separate debug file: {debug_path}")
            report.suggestions.append(f"Use: add-symbol-file {debug_path}")
            return

    # 通用建议
    report.suggestions.extend([
        "Binary appears to be stripped (no debug info)",
        "Install debuginfo package:",
        f"  RHEL/CentOS: dnf debuginfo-install {binary_name}",
        f"  Ubuntu/Debian: apt-get install {binary_name}-dbgsym",
        f"  Fedora: dnf install {binary_name}-debuginfo",
        "Or use separate .debug file:",
        f"  add-symbol-file /path/to/{binary_name}.debug",
    ])


def suggest_solib_paths(binary_path: str, core_path: Optional[str] = None) -> List[str]:
    """
    建议共享库搜索路径

    Args:
        binary_path: 二进制文件路径
        core_path: core 文件路径（可选）

    Returns:
        建议的路径列表
    """
    suggestions = []
    binary = Path(binary_path)

    # 常见的库路径

    # 检查二进制目录
    if binary.parent.exists():
        lib_dir = binary.parent / "lib"
        if lib_dir.exists():
            suggestions.append(str(lib_dir))

    # 如果有 core 文件，尝试从 core 中提取路径
    if core_path:
        suggestions.append("Use 'info sharedlibrary' in GDB to see loaded libraries")
        suggestions.append("Use 'set solib-search-path /path1:/path2' to specify library paths")

    return suggestions


def get_env_check_cli_output(gdb_path=None) -> dict:
    """
    获取环境检查的 CLI 输出

    Returns:
        JSON 格式的环境报告
    """
    report = check_environment(gdb_path=gdb_path)

    result = {
        "python_version": report.python_version,
        "platform": report.platform,
        "arch": platform.machine(),
        "gdb_path": report.gdb_path,
        "gdb_version": report.gdb_version,
        "gdb_supported": report.gdb_supported,
        "gdb_recommended": report.gdb_recommended,
        "ptrace_scope": report.ptrace_scope,
        "ptrace_allowed": report.ptrace_allowed,
        "ready": report.ready,
    }

    if report.warnings:
        result["warnings"] = report.warnings
    if report.errors:
        result["errors"] = report.errors
    if report.suggestions:
        result["suggestions"] = report.suggestions

    return result
