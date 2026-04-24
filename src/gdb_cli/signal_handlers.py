"""
Signal Handlers - 集中式信号处理

注册 SIGTERM/SIGINT 处理，确保 GDB 子进程在 CLI 被终止时得到清理。
"""

import signal
import sys
from typing import Callable, List

_cleanup_handlers: List[Callable[[], None]] = []


def register_cleanup(handler: Callable[[], None]) -> None:
    """注册清理回调，在收到终止信号时调用"""
    _cleanup_handlers.append(handler)


def _signal_handler(signum: int, frame) -> None:
    """信号处理入口"""
    for handler in _cleanup_handlers:
        try:
            handler()
        except Exception:
            pass
    sys.exit(128 + signum)


def setup_signal_handlers() -> None:
    """注册 SIGTERM 和 SIGINT 处理器"""
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
