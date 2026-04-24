# GDB CLI для ИИ

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | Русский | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Italiano](README.it.md)

Инструмент отладки GDB, разработанный для ИИ-агентов (Claude Code и др.). Использует архитектуру «тонкий клиент CLI + RPC-сервер на Python внутри GDB», обеспечивая отладку GDB с сохранением состояния через Bash.

## Возможности

- **Анализ core dump**: загрузка core dump с символами, постоянно находящимися в памяти, для ответа в миллисекундах
- **Отладка живых процессов**: подключение к работающим процессам с поддержкой non-stop режима
- **Структурированный JSON-вывод**: все команды выводят JSON с автоматическим усечением/пагинацией и подсказками для операций
- **Механизмы безопасности**: whitelist команд, автоматическая очистка по таймауту heartbeat, гарантии идемпотентности
- **Оптимизация для баз данных**: scheduler-locking, пагинация больших объектов, усечение многопоточных данных

## Требования

- **Python**: 3.6.8+
- **GDB**: 9.0+ с **включённой поддержкой Python**
- **ОС**: Linux

### Проверка поддержки Python в GDB

```bash
# Проверить, есть ли в GDB поддержка Python
gdb -nx -q -batch -ex "python print('OK')"

# Если системный GDB без Python, проверьте GCC Toolset (RHEL/CentOS)
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Установка

```bash
# Установка из PyPI
pip install gdb-cli

# Или установка из GitHub
pip install git+https://github.com/Cerdore/gdb-cli.git

# Или клонирование и локальная установка
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# Проверка окружения
gdb-cli env-check
```

## Быстрый старт

### 1. Загрузка Core Dump

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Вывод:
```json
{
  "session_id": "f465d650",
  "mode": "core",
  "binary": "./my_program",
  "core": "./core.12345",
  "gdb_pid": 12345,
  "status": "loading"
}
```

При загрузке большого бинарного файла или core dump опрашивайте статус до готовности сеанса:

```bash
gdb-cli status -s f465d650
```

```json
{
  "session_id": "f465d650",
  "state": "ready",
  "mode": "core",
  "binary": "./my_program"
}
```

> Если системный GDB без поддержки Python, укажите его через `--gdb-path`:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Операции отладки

Все операции используют `--session` / `-s` для указания ID сеанса:

```bash
SESSION="f465d650"

# Список потоков
gdb-cli threads -s $SESSION

# Получить backtrace (по умолчанию: текущий поток)
gdb-cli bt -s $SESSION

# Получить backtrace для конкретного потока
gdb-cli bt -s $SESSION --thread 3

# Вычислить выражения C/C++
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Доступ к элементам массива
gdb-cli eval-element -s $SESSION "my_array" --index 5

# Просмотр локальных переменных
gdb-cli locals-cmd -s $SESSION

# Выполнить raw-команды GDB
gdb-cli exec -s $SESSION "info registers"

# Проверить статус сеанса
gdb-cli status -s $SESSION
```

### 3. Управление сеансами

```bash
# Список всех активных сеансов
gdb-cli sessions

# Остановить сеанс
gdb-cli stop -s $SESSION
```

### 4. Отладка живых процессов

```bash
# Подключиться к работающему процессу (по умолчанию: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Подключиться с файлом символов
gdb-cli attach --pid 9876 --binary ./my_program

# Разрешить модификацию памяти и вызовы функций
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Полный справочник команд

### load — Загрузка Core Dump

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      Путь к исполняемому файлу (обязательно)
  --core, -c        Путь к файлу core dump (обязательно)
  --sysroot         путь к sysroot (для межмашинной отладки)
  --solib-prefix    Префикс разделяемых библиотек
  --source-dir      Каталог исходного кода
  --timeout         Таймаут heartbeat в секундах (по умолчанию: 600)
  --gdb-path        Путь к исполняемому файлу GDB (по умолчанию: "gdb")
```

`load` возвращается немедленно с `"status": "loading"` после того, как RPC-сервер становится доступным. Используйте `gdb-cli status -s <session>` и дождитесь `"state": "ready"` перед командами глубокого анализа.

### attach — Подключение к процессу

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               PID процесса (обязательно)
  --binary                Путь к исполняемому файлу (опционально)
  --scheduler-locking     Включить scheduler-locking (по умолчанию: true)
  --non-stop              Включить non-stop режим (по умолчанию: true)
  --timeout               Таймаут heartbeat в секундах (по умолчанию: 600)
  --allow-write           Разрешить модификацию памяти
  --allow-call            Разрешить вызовы функций
```

### threads — Список потоков

```
gdb-cli threads -s <session> [options]

  --range           Диапазон потоков, например "3-10"
  --limit           Максимальное количество (по умолчанию: 20)
  --filter-state    Фильтр по состоянию ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      Указать ID потока
  --limit           Максимальное количество фреймов (по умолчанию: 30)
  --full            Включить локальные переменные
  --range           Диапазон фреймов, например "5-15"
```

### eval-cmd — Вычисление выражения

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Лимит глубины рекурсии (по умолчанию: 3)
  --max-elements    Лимит элементов массива (по умолчанию: 50)
```

### eval-element — Доступ к элементам массива/контейнера

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Выполнение raw-команды GDB

```
gdb-cli exec -s <session> <command>

  --safety-level    Уровень безопасности (readonly / readwrite / full)
```

### thread-apply — Batch-операции над потоками

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Примеры вывода

### threads

```json
{
  "threads": [
    {"id": 1, "global_id": 1, "state": "stopped"},
    {"id": 2, "global_id": 2, "state": "stopped"}
  ],
  "total_count": 5,
  "truncated": true,
  "current_thread": {"id": 1, "global_id": 1, "state": "stopped"},
  "hint": "use 'threads --range START-END' for specific threads"
}
```

### eval-cmd

```json
{
  "expression": "(int)5+3",
  "value": 8,
  "type": "int",
  "size": 4
}
```

### bt

```json
{
  "frames": [
    {"number": 0, "function": "crash_thread", "address": "0x400a1c", "file": "test.c", "line": 42},
    {"number": 1, "function": "start_thread", "address": "0x7f3fa2e13fa"}
  ],
  "total_count": 2,
  "truncated": false
}
```

## Механизмы безопасности

### Whitelist команд (режим attach)

| Уровень безопасности | Разрешённые команды |
|----------------------|---------------------|
| `readonly` (по умолчанию) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` всегда заблокированы.

### Таймаут Heartbeat

Автоматически отключается и завершает работу после 10 минут неактивности по умолчанию. Настраивается через `--timeout`.

### Идемпотентность

Только один сеанс на PID / Core file. Повторные load/attach возвращают существующий session_id.

## Отладка core dump с другого компьютера

При анализе core dump с других машин пути разделяемых библиотек могут отличаться:

```bash
# Установить sysroot (префикс замены пути)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Установить каталог исходников (для отладки на уровне исходного кода)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Разработка

### Структура проекта

```
src/gdb_cli/
├── cli.py              # Точка входа CLI (Click)
├── client.py           # Клиент Unix Socket
├── launcher.py         # Запуск процесса GDB
├── session.py          # Управление метаданными сеанса
├── safety.py           # Фильтр whitelist команд
├── formatters.py       # Форматирование JSON-вывода
├── env_check.py        # Проверка окружения
├── errors.py           # Классификация ошибок
└── gdb_server/
    ├── gdb_rpc_server.py   # Ядро RPC Server
    ├── handlers.py         # Обработчики команд
    ├── value_formatter.py  # Сериализация gdb.Value
    └── heartbeat.py         # Управление таймаутом heartbeat

skills/
└── gdb-cli/               # Skill Claude Code для интеллектуальной отладки
    ├── SKILL.md            # Определение skill
    └── evals/              # Тест-кейсы для оценки skill
```

### Запуск тестов

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### End-to-End тестирование

Требует GDB с поддержкой Python. Используйте тестовую программу crash в `tests/crash_test/`:

```bash
# Компиляция тестовой программы
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Генерация coredump
ulimit -c unlimited
./crash_test  # Будет SIGSEGV

# Найти файл core
ls /path/to/core_dumps/core-crash_test-*

# Запуск E2E теста
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Известные ограничения

- Нет поддержки `target remote` (используйте SSH для удалённой отладки, см. ниже)
- Нет поддержки multi-inferior отладки
- Guile pretty-printers в GDB 12.x не thread-safe, обход через `format_string(raw=True)`
- Встроенная версия Python в GDB может быть старее (например, 3.6.8), код имеет обработку совместимости

## Удалённая отладка через SSH

Установка и запуск на удалённой машине в одну команду:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

Или сначала установка, затем отладка:

```bash
# Установка на удалённой машине
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Запуск отладки
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Skills для Claude Code

Этот проект включает **gdb-cli skill** для Claude Code, который предоставляет интеллектуальную помощь в отладке, комбинируя анализ исходного кода с инспекцией состояния runtime.

### Установка Skill

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Использование в Claude Code

```
/gdb-cli

# Или описать потребность в отладке:
I have a core dump at ./core.1234 and binary at ./myapp. Help me debug it.
```

### Возможности

- **Корреляция с исходным кодом**: Автоматически читает файлы исходного кода вокруг точек crash
- **Обнаружение deadlock**: Идентифицирует паттерны circular wait в многопоточных программах
- **Предупреждения безопасности**: Уведомляет о рисках в production-окружении при подключении к живым процессам
- **Структурированные отчёты**: Генерирует анализ с гипотезами root cause и следующими шагами

См. [skills/README.md](skills/README.md) для подробностей.

## Лицензия

Apache License 2.0