# Implementation Plan: Multilanguage Support for gdb-cli

**Source Spec**: `docs/superpowers/specs/2026-04-04-multilanguage-support-design.md`
**Target Languages**: `en`, `zh-CN`, `ru`
**Date**: 2026-04-04

---

## Requirements Summary

Implement first-version multilanguage support for gdb-cli covering:
- Runtime CLI help text and user-facing messages
- JSON response messages, hints, warnings, suggestions
- Repository README files (en, zh-CN, ru)

## Current State Analysis

| File | Current State | Action Required |
|------|---------------|-----------------|
| `cli.py` | Hardcoded Chinese help text | Full i18n conversion |
| `errors.py` | `ERROR_SUGGESTIONS` dict with Chinese text | i18n catalog integration |
| `env_check.py` | Hardcoded English suggestions/warnings | i18n catalog integration |
| `README.md` | English, existing | Add language switcher with ru |
| `README.zh-CN.md` | Chinese, existing | Add language switcher with ru |
| `README.ru.md` | Missing | Create from README.md |

---

## Implementation Steps

### Phase 1: i18n Infrastructure (Foundation)

#### Step 1.1: Create locale package structure

**Files to create**:
- `src/gdb_cli/locales/__init__.py`
- `src/gdb_cli/locales/en.py`
- `src/gdb_cli/locales/zh_cn.py`
- `src/gdb_cli/locales/ru.py`

**Implementation**:
```
src/gdb_cli/locales/
├── __init__.py   # Package init, exposes get_catalog()
├── en.py         # ENGLISH_CATALOG dict (source language)
├── zh_cn.py      # ZH_CN_CATALOG dict
└── ru.py         # RU_CATALOG dict
```

#### Step 1.2: Create i18n module

**File**: `src/gdb_cli/i18n.py`

**Functions**:
- `resolve_locale() -> str` - Detect locale from env/system
- `normalize_locale(locale_str: str) -> str` - Normalize aliases
- `t(key: str, **params) -> str` - Translation lookup with interpolation
- `get_current_locale() -> str` - Return active locale

**Locale precedence**:
1. `GDB_CLI_LANG` environment variable
2. System locale (`LANG`, `LC_ALL`, `LC_MESSAGES`)
3. Default to `en`

**Normalization rules** (per spec):
- `en`, `en_US`, `en-US` -> `en`
- `zh`, `zh_CN`, `zh-CN`, `zh_Hans_CN` -> `zh-CN`
- `ru`, `ru_RU`, `ru-RU` -> `ru`
- Unknown -> `en`

#### Step 1.3: Define stable key families

**Key naming convention**: `{module}.{context}.{item}`

Example keys (to be defined in catalogs):
```
cli.group.help
cli.load.binary_help
cli.load.core_help
cli.load.sysroot_help
cli.attach.pid_help
cli.threads.session_help
cli.threads.range_help

errors.session_not_found
errors.connection_error
errors.ptrace_denied.suggestion
errors.memory_access_failed.suggestion

env_check.gdb_not_found
env_check.gdb_below_minimum
env_check.ptrace_restricted
env_check.debuginfo_install_hint
```

---

### Phase 2: Catalog Content (Translation Files)

#### Step 2.1: English catalog (source)

**File**: `src/gdb_cli/locales/en.py`

Extract all user-facing strings from:
- `cli.py`: 40+ help texts, error messages
- `errors.py`: 15 suggestion templates
- `env_check.py`: 20+ warning/suggestion texts

#### Step 2.2: Chinese catalog

**File**: `src/gdb_cli/locales/zh_cn.py`

Many existing texts are already Chinese. Preserve them with key mapping.

#### Step 2.3: Russian catalog

**File**: `src/gdb_cli/locales/ru.py`

Translate all keys from English catalog.

---

### Phase 3: CLI Integration

#### Step 3.1: Update cli.py Click decorators

**Challenge**: Click evaluates help text at import time.

**Solution**: Use lazy translation helper.

```python
# Pattern for Click help text
from .i18n import t

@click.option("--binary", "-b", required=True, help=t("cli.load.binary_help"))
```

**Alternative if needed** (deferred evaluation):
```python
def lazy_help(key: str):
    return lambda: t(key)

@click.option("--binary", "-b", required=True, help=lazy_help("cli.load.binary_help"))
```

#### Step 3.2: Update print_error/print_json messages

Replace hardcoded strings with `t()` calls:

```python
# Before
print_error("Session not found", session)

# After
print_error(t("errors.session_not_found", session_id=session), session)
```

#### Step 3.3: Update env_check.py suggestions

Replace all hardcoded suggestions:

```python
# Before
report.suggestions.append("Install GDB: 'brew install gdb' (macOS)...")

# After
report.suggestions.append(t("env_check.gdb_install_suggestion"))
```

---

### Phase 4: README Localization

#### Step 4.1: Update language switchers

**Files**: `README.md`, `README.zh-CN.md`

Add Russian to existing switcher:
```markdown
[English](README.md) | [中文](README.zh-CN.md) | [Русский](README.ru.md)
```

#### Step 4.2: Create README.ru.md

**Source**: Translate from `README.md`

**Sections to translate**:
- Title and badges (preserve badge URLs)
- Features
- Requirements
- Installation
- Quick Start (all 4 subsections)
- Full Command Reference
- Output Examples
- Security Mechanisms
- Cross-Machine Debugging
- Development
- Known Limitations
- Remote Debugging via SSH
- License

**Preserve unchanged**:
- Code blocks (commands, JSON output)
- URLs and links
- Badge markdown

---

### Phase 5: Testing

#### Step 5.1: Unit tests for i18n module

**File**: `tests/test_i18n.py`

**Coverage**:
- `normalize_locale()` for all alias formats (en_US, zh_CN, ru_RU, etc.)
- `resolve_locale()` precedence (env var > system > default)
- `t()` lookup for all three languages
- `t()` fallback to English on missing key
- `t()` interpolation with parameters
- Missing catalog falls back gracefully

#### Step 5.2: Integration tests for CLI

**File**: `tests/test_cli_i18n.py`

**Coverage**:
- `gdb-cli --help` output in different locales
- Error messages translated
- `env-check` suggestions in different locales
- Key set consistency across catalogs (all have same keys)

#### Step 5.3: Update existing tests

Update `test_env_check.py`, `test_cli_async.py` to use i18n keys instead of hardcoded string matching.

---

### Phase 6: Rollout Sequence

**Order** (per spec Migration Strategy):

1. Introduce `i18n.py` and `locales/` package
2. Convert central CLI entry points (`cli.py` main group, load, attach)
3. Convert remaining CLI commands
4. Convert `env_check.py` suggestions/warnings
5. Convert `errors.py` ERROR_SUGGESTIONS
6. Create `README.ru.md`, update all README switchers
7. Add tests

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Click help evaluated at import time | Use lambda wrapper for deferred evaluation |
| Catalog key drift across languages | Add test comparing key sets |
| Partial translation = mixed output | English fallback + prioritize shared wrappers first |
| README divergence over time | English as source document, sync structure |

---

## Acceptance Criteria

- [ ] `src/gdb_cli/i18n.py` exists with `t()`, `resolve_locale()`, `normalize_locale()`
- [ ] `src/gdb_cli/locales/` package with `en.py`, `zh_cn.py`, `ru.py`
- [ ] Locale precedence: `GDB_CLI_LANG` > system locale > `en`
- [ ] Normalization: `en_US`->`en`, `zh_CN`->`zh-CN`, `ru_RU`->`ru`
- [ ] CLI help text in English, Chinese, Russian based on locale
- [ ] JSON hints/suggestions translated for supported languages
- [ ] `README.ru.md` exists with language switcher
- [ ] All READMEs have 3-language switcher
- [ ] Tests: locale normalization, fallback, representative CLI outputs
- [ ] Test: key sets match across all catalogs

---

## Estimated Files Changed

| Category | Count |
|----------|-------|
| New files | 5 (`i18n.py`, 3 locales, `README.ru.md`) |
| Modified files | 4 (`cli.py`, `errors.py`, `env_check.py`, `README.md`, `README.zh-CN.md`) |
| Test files | 2 new (`test_i18n.py`, `test_cli_i18n.py`) + 2 updated |

---

## Verification Steps

1. `GDB_CLI_LANG=en gdb-cli --help` -> English output
2. `GDB_CLI_LANG=zh-CN gdb-cli --help` -> Chinese output
3. `GDB_CLI_LANG=ru gdb-cli --help` -> Russian output
4. `GDB_CLI_LANG=invalid gdb-cli --help` -> English (fallback)
5. `pytest tests/test_i18n.py tests/test_cli_i18n.py -v` -> all pass
6. `README.ru.md` exists and has valid language switcher