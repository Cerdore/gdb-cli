"""
Locales Package - 翻译目录

支持的语言: en, zh-CN, ru
"""

from typing import Dict

# 延迟加载 catalogs
_CATALOGS: Dict[str, Dict[str, str]] = {}


def get_catalog(locale: str) -> Dict[str, str]:
    """
    获取指定语言的翻译目录

    Args:
        locale: 语言代码 ("en", "zh-CN", "ru")

    Returns:
        翻译目录字典
    """
    if locale in _CATALOGS:
        return _CATALOGS[locale]

    # 延迟加载
    if locale == "en":
        from .en import ENGLISH_CATALOG
        _CATALOGS[locale] = ENGLISH_CATALOG
    elif locale == "zh-CN":
        from .zh_cn import ZH_CN_CATALOG
        _CATALOGS[locale] = ZH_CN_CATALOG
    elif locale == "ru":
        from .ru import RU_CATALOG
        _CATALOGS[locale] = RU_CATALOG
    else:
        # 回退英语
        from .en import ENGLISH_CATALOG
        _CATALOGS[locale] = ENGLISH_CATALOG

    return _CATALOGS[locale]


def get_supported_locales():
    """返回支持的语言列表"""
    return ["en", "zh-CN", "ru"]
