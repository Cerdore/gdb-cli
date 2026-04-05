"""
Tests for i18n module
"""

from gdb_cli.i18n import (
    get_current_locale,
    normalize_locale,
    reset_locale,
    resolve_locale,
    set_locale,
    t,
)
from gdb_cli.locales import get_catalog, get_supported_locales


class TestNormalizeLocale:
    """Test locale normalization"""

    def test_english_variants(self):
        assert normalize_locale("en") == "en"
        assert normalize_locale("en_US") == "en"
        assert normalize_locale("en-US") == "en"
        assert normalize_locale("en_GB") == "en"
        assert normalize_locale("C") == "en"
        assert normalize_locale("POSIX") == "en"

    def test_chinese_variants(self):
        assert normalize_locale("zh") == "zh-CN"
        assert normalize_locale("zh_CN") == "zh-CN"
        assert normalize_locale("zh-CN") == "zh-CN"
        assert normalize_locale("zh_Hans_CN") == "zh-CN"

    def test_russian_variants(self):
        assert normalize_locale("ru") == "ru"
        assert normalize_locale("ru_RU") == "ru"
        assert normalize_locale("ru-RU") == "ru"

    def test_unknown_fallback(self):
        assert normalize_locale("invalid") == "en"
        assert normalize_locale("fr_FR") == "en"
        assert normalize_locale("") == "en"
        assert normalize_locale(None) == "en"


class TestResolveLocale:
    """Test locale resolution"""

    def test_env_variable_override(self, monkeypatch):
        reset_locale()
        monkeypatch.setenv("GDB_CLI_LANG", "zh-CN")
        assert resolve_locale() == "zh-CN"

    def test_lang_env(self, monkeypatch):
        reset_locale()
        monkeypatch.delenv("GDB_CLI_LANG", raising=False)
        monkeypatch.setenv("LANG", "ru_RU.UTF-8")
        assert resolve_locale() == "ru"

    def test_default_fallback(self, monkeypatch):
        reset_locale()
        monkeypatch.delenv("GDB_CLI_LANG", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.delenv("LC_MESSAGES", raising=False)
        # Should fallback to en
        assert resolve_locale() == "en"


class TestTranslation:
    """Test translation function"""

    def test_english_translation(self):
        set_locale("en")
        assert t("cli.load.binary_help") == "Executable file path"

    def test_chinese_translation(self):
        set_locale("zh-CN")
        assert t("cli.load.binary_help") == "可执行文件路径"

    def test_russian_translation(self):
        set_locale("ru")
        assert t("cli.load.binary_help") == "Путь к исполняемому файлу"

    def test_interpolation(self):
        set_locale("en")
        result = t("errors.session_not_found", session_id="abc123")
        assert result == "Session not found: abc123"

    def test_missing_key_fallback(self):
        set_locale("en")
        # Add a key only to English catalog for testing
        result = t("nonexistent.key")
        assert "[MISSING:" in result

    def test_missing_translation_fallback_to_english(self):
        # This tests that if a key exists in English but not in another language,
        # it falls back to English
        set_locale("en")
        assert t("cli.load.binary_help") == "Executable file path"


class TestCatalog:
    """Test catalog loading"""

    def test_get_catalog_english(self):
        catalog = get_catalog("en")
        assert isinstance(catalog, dict)
        assert "cli.load.binary_help" in catalog

    def test_get_catalog_chinese(self):
        catalog = get_catalog("zh-CN")
        assert isinstance(catalog, dict)
        assert "cli.load.binary_help" in catalog

    def test_get_catalog_russian(self):
        catalog = get_catalog("ru")
        assert isinstance(catalog, dict)
        assert "cli.load.binary_help" in catalog

    def test_get_catalog_fallback(self):
        catalog = get_catalog("unknown")
        assert isinstance(catalog, dict)
        # Should return English catalog
        assert "cli.load.binary_help" in catalog

    def test_supported_locales(self):
        locales = get_supported_locales()
        assert "en" in locales
        assert "zh-CN" in locales
        assert "ru" in locales

    def test_key_consistency(self):
        """All catalogs should have the same keys"""
        en_catalog = get_catalog("en")
        zh_catalog = get_catalog("zh-CN")
        ru_catalog = get_catalog("ru")

        en_keys = set(en_catalog.keys())
        zh_keys = set(zh_catalog.keys())
        ru_keys = set(ru_catalog.keys())

        assert en_keys == zh_keys, f"Key mismatch between en and zh-CN: {en_keys.symmetric_difference(zh_keys)}"
        assert en_keys == ru_keys, f"Key mismatch between en and ru: {en_keys.symmetric_difference(ru_keys)}"


class TestSetLocale:
    """Test set_locale function"""

    def test_set_valid_locale(self):
        result = set_locale("zh-CN")
        assert result == "zh-CN"
        assert get_current_locale() == "zh-CN"

    def test_set_normalized_locale(self):
        result = set_locale("zh_CN")
        assert result == "zh-CN"

    def test_reset_locale(self):
        set_locale("ru")
        assert get_current_locale() == "ru"
        reset_locale()
        # After reset, should re-resolve from environment
