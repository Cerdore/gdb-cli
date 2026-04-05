"""
i18n Module - 国际化支持

提供轻量级运行时翻译层:
- resolve_locale(): 从环境/系统检测 locale
- normalize_locale(): 规范化 locale 别名
- t(): 翻译查找 + 参数插值
"""

import locale as sys_locale
import os
from typing import Optional

# 支持的语言
SUPPORTED_LOCALES = {"en", "zh-CN", "ru"}

# Locale 别名映射
LOCALE_ALIAS_MAP = {
    # English variants
    "en": "en",
    "en_us": "en",
    "en-us": "en",
    "en_gb": "en",
    "en-gb": "en",
    "c": "en",  # POSIX C locale
    "posix": "en",

    # Chinese variants
    "zh": "zh-CN",
    "zh_cn": "zh-CN",
    "zh-cn": "zh-CN",
    "zh_hans_cn": "zh-CN",
    "zh-hans-cn": "zh-CN",
    "zh_sg": "zh-CN",
    "zh-sg": "zh-CN",

    # Russian variants
    "ru": "ru",
    "ru_ru": "ru",
    "ru-ru": "ru",
    "ru_ua": "ru",
    "ru-ua": "ru",
}

# 当前活跃 locale (延迟初始化)
_current_locale: Optional[str] = None


def normalize_locale(locale_str: str) -> str:
    """
    规范化 locale 标识符

    Args:
        locale_str: 原始 locale 字符串

    Returns:
        规范化后的 locale ("en", "zh-CN", "ru")
    """
    if not locale_str:
        return "en"

    # 转小写，替换常见分隔符
    normalized = locale_str.lower().replace("_", "-")

    # 查找映射
    if normalized in LOCALE_ALIAS_MAP:
        return LOCALE_ALIAS_MAP[normalized]

    # 查找原始格式 (下划线版本)
    underscore_ver = locale_str.lower().replace("-", "_")
    if underscore_ver in LOCALE_ALIAS_MAP:
        return LOCALE_ALIAS_MAP[underscore_ver]

    # 未找到则回退英语
    return "en"


def resolve_locale() -> str:
    """
    解析当前 locale

    优先级:
    1. GDB_CLI_LANG 环境变量
    2. 系统 locale (LANG, LC_ALL, LC_MESSAGES)
    3. 默认英语

    Returns:
        规范化后的 locale
    """
    global _current_locale

    if _current_locale is not None:
        return _current_locale

    # 1. 环境变量覆盖
    env_lang = os.environ.get("GDB_CLI_LANG")
    if env_lang:
        _current_locale = normalize_locale(env_lang)
        return _current_locale

    # 2. 系统 locale
    sys_lang = os.environ.get("LANG") or \
               os.environ.get("LC_ALL") or \
               os.environ.get("LC_MESSAGES")

    if sys_lang:
        # 提取语言部分 (如 "zh_CN.UTF-8" -> "zh_CN")
        lang_part = sys_lang.split(".")[0].split("@")[0]
        _current_locale = normalize_locale(lang_part)
        return _current_locale

    # 尝试 Python locale 模块
    try:
        sys_locale.setlocale(sys_locale.LC_MESSAGES, "")
        loc = sys_locale.getlocale(sys_locale.LC_MESSAGES)
        if loc and loc[0]:
            _current_locale = normalize_locale(loc[0])
            return _current_locale
    except Exception:
        pass

    # 3. 默认英语
    _current_locale = "en"
    return _current_locale


def get_current_locale() -> str:
    """
    获取当前活跃 locale

    Returns:
        当前 locale
    """
    return resolve_locale()


def set_locale(locale_str: str) -> str:
    """
    强制设置 locale (主要用于测试)

    Args:
        locale_str: 目标 locale

    Returns:
        实际设置的 locale
    """
    global _current_locale
    _current_locale = normalize_locale(locale_str)
    return _current_locale


def t(key: str, **params) -> str:
    """
    翻译函数

    Args:
        key: 翻译键 (如 "cli.load.binary_help")
        **params: 插值参数

    Returns:
        翻译后的文本
    """
    from .locales import get_catalog

    loc = resolve_locale()
    catalog = get_catalog(loc)

    # 查找翻译
    if key in catalog:
        text = catalog[key]
    else:
        # 回退英语
        en_catalog = get_catalog("en")
        if key in en_catalog:
            text = en_catalog[key]
        else:
            # 键缺失，返回键本身 (开发调试)
            return f"[MISSING:{key}]"

    # 参数插值
    if params:
        try:
            return text.format(**params)
        except KeyError as e:
            # 插值参数缺失
            return f"[INTERPOLATION_ERROR:{key}:{e}]"

    return text


def reset_locale() -> None:
    """
    重置 locale 缓存 (主要用于测试)
    """
    global _current_locale
    _current_locale = None
