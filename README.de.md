# GDB CLI for AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | [Русский](README.ru.md) | [Türkçe](README.tr.md) | Deutsch | [Français](README.fr.md) | [Italiano](README.it.md)

Ein GDB-Debugging-Tool, entwickelt für KI-Agenten (Claude Code usw.). Nutzt eine "Thin-Client-CLI + GDB-integrierter Python-RPC-Server"-Architektur, um zustandsbasiertes GDB-Debugging über Bash zu ermöglichen.

## Funktionen

- **Core-Dump-Analyse**: Lade Core Dumps mit im Speicher gehaltenen Symbolen für Millisekunden-Reaktionszeit
- **Live-Attach-Debugging**: Verbinde mit laufenden Prozessen mit Non-Stop-Modus-Unterstützung
- **Strukturierte JSON-Ausgabe**: Alle Befehle geben JSON mit automatischer Trunkierung/Paginierung und Operation-Hints aus
- **Sicherheitsmechanismen**: Befehls-Whitelist, Heartbeat-Timeout-Autocleanup, Idempotenz-Garantien
- **Datenbank-optimiert**: scheduler-locking, Large-Object-Paginierung, Multi-Thread-Trunkierung

## Anforderungen

- **Python**: 3.6.8+
- **GDB**: 9.0+ mit **Python-Unterstützung aktiviert**
- **OS**: Linux

### GDB Python-Unterstützung prüfen

```bash
# Prüfen, ob GDB Python-Unterstützung hat
gdb -nx -q -batch -ex "python print('OK')"

# Falls System-GDB Python nicht unterstützt, GCC Toolset (RHEL/CentOS) prüfen
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Installation

```bash
# Von PyPI installieren
pip install gdb-cli

# Oder von GitHub installieren
pip install git+https://github.com/Cerdore/gdb-cli.git

# Oder lokales Repository klonen und installieren
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# Umgebungsprüfung
gdb-cli env-check
```

## Schnellstart

### 1. Core Dump laden

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Ausgabe:
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

Wenn ein großes Binary oder eine Core-Datei geladen wird, poll bis der Session bereit ist:

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

> Falls der Standard-GDB des Systems keine Python-Unterstützung hat, gib ihn mit `--gdb-path` an:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Debugging-Operationen

Alle Operationen nutzen `--session` / `-s` zum Spezifizieren der Session-ID:

```bash
SESSION="f465d650"

# Threads auflisten
gdb-cli threads -s $SESSION

# Backtrace abrufen (Standard: aktueller Thread)
gdb-cli bt -s $SESSION

# Backtrace für spezifischen Thread abrufen
gdb-cli bt -s $SESSION --thread 3

# C/C++-Ausdrücke evaluieren
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Array-Elemente zugreifen
gdb-cli eval-element -s $SESSION "my_array" --index 5

# Lokale Variablen anzeigen
gdb-cli locals-cmd -s $SESSION

# Rohen GDB-Befehl ausführen
gdb-cli exec -s $SESSION "info registers"

# Session-Status prüfen
gdb-cli status -s $SESSION
```

### 3. Session-Management

```bash
# Alle aktiven Sessions auflisten
gdb-cli sessions

# Session stoppen
gdb-cli stop -s $SESSION
```

### 4. Live-Attach-Debugging

```bash
# An laufenden Prozess anhängen (Standard: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Mit Symbol-Datei anhängen
gdb-cli attach --pid 9876 --binary ./my_program

# Speichermodifikation und Funktionsaufrufe erlauben
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Vollständige Befehlsreferenz

### load — Core Dump laden

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      Executable-Dateipfad (erforderlich)
  --core, -c        Core-Dump-Dateipfad (erforderlich)
  --sysroot         Sysroot-Pfad (für Cross-Machine-Debugging)
  --solib-prefix    Shared-Library-Präfix
  --source-dir      Quellcode-Verzeichnis
  --timeout         Heartbeat-Timeout in Sekunden (Standard: 600)
  --gdb-path        GDB-Executable-Pfad (Standard: "gdb")
```

`load` kehrt sofort mit `"status": "loading"` zurück, sobald der RPC-Server erreichbar ist. Nutze `gdb-cli status -s <session>` und warte auf `"state": "ready"` vor schweren Inspektionsbefehlen.

### attach — An Prozess anhängen

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               Prozess-PID (erforderlich)
  --binary                Executable-Dateipfad (optional)
  --scheduler-locking     Scheduler-Locking aktivieren (Standard: true)
  --non-stop              Non-Stop-Modus aktivieren (Standard: true)
  --timeout               Heartbeat-Timeout in Sekunden (Standard: 600)
  --allow-write           Speichermodifikation erlauben
  --allow-call            Funktionsaufrufe erlauben
```

### threads — Threads auflisten

```
gdb-cli threads -s <session> [options]

  --range           Thread-Bereich, z.B. "3-10"
  --limit           Maximale Rückgabeanzahl (Standard: 20)
  --filter-state    Nach Status filtern ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      Thread-ID angeben
  --limit           Max. Frame-Anzahl (Standard: 30)
  --full            Lokale Variablen einschließen
  --range           Frame-Bereich, z.B. "5-15"
```

### eval-cmd — Ausdruck evaluieren

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Rekursionstiefe-Limit (Standard: 3)
  --max-elements    Array-Element-Limit (Standard: 50)
```

### eval-element — Array/Container-Elemente zugreifen

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Rohen GDB-Befehl ausführen

```
gdb-cli exec -s <session> <command>

  --safety-level    Sicherheitslevel (readonly / readwrite / full)
```

### thread-apply — Batch-Thread-Operationen

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Ausgabebeispiele

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

## Sicherheitsmechanismen

### Befehls-Whitelist (Attach-Modus)

| Sicherheitslevel | Erlaubte Befehle |
|------------------|------------------|
| `readonly` (Standard) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` sind immer blockiert.

### Heartbeat-Timeout

Automatisches Detach und Quit nach 10 Minuten Inaktivität (Standard). Konfigurierbar via `--timeout`.

### Idempotenz

Nur eine Session pro PID / Core-Datei erlaubt. Wiederholtes Load/Attach gibt die bestehende Session_ID zurück.

## Cross-Machine Core-Dump-Debugging

Bei der Analyse von Core Dumps von anderen Maschinen können die Shared-Library-Pfade abweichen:

```bash
# Sysroot setzen (Pfad-Präfix-Ersetzung)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Quellverzeichnis setzen (für Source-Level-Debugging)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Entwicklung

### Projektstruktur

```
src/gdb_cli/
├── cli.py              # CLI-Einstiegspunkt (Click)
├── client.py           # Unix-Socket-Client
├── launcher.py         # GDB-Prozess-Launcher
├── session.py          # Session-Metadaten-Management
├── safety.py           # Befehls-Whitelist-Filter
├── formatters.py       # JSON-Ausgabe-Formatierung
├── env_check.py        # Umgebungsprüfung
├── errors.py           # Fehlerklassifizierung
└── gdb_server/
    ├── gdb_rpc_server.py   # RPC-Server-Core
    ├── handlers.py         # Befehls-Handler
    ├── value_formatter.py  # gdb.Value-Serialisierung
    └── heartbeat.py         # Heartbeat-Timeout-Management

skills/
└── gdb-cli/               # Claude-Code-Skill für intelligentes Debugging
    ├── SKILL.md            # Skill-Definition
    └── evals/              # Testfälle für Skill-Evaluierung
```

### Tests ausführen

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### End-to-End-Testing

Benötigt GDB mit Python-Unterstützung. Nutze das Crash-Test-Programm in `tests/crash_test/`:

```bash
# Testprogramm kompilieren
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Core-Dump generieren
ulimit -c unlimited
./crash_test  # Erzeugt SIGSEGV

# Core-Datei finden
ls /path/to/core_dumps/core-crash_test-*

# E2E-Test ausführen
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Bekannte Einschränkungen

- Kein `target remote`-Support (nutze SSH für Remote-Debugging, siehe unten)
- Kein Multi-Inferior-Debugging-Support
- GDB 12.x Guile Pretty Printer sind nicht thread-sicher, Workaround via `format_string(raw=True)`
- GDB-integrierte Python-Version kann älter sein (z.B. 3.6.8), Code hat Kompatibilitäts-Handling

## Remote-Debugging via SSH

Auf Remote-Maschine installieren und in einem Befehl ausführen:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

Oder zuerst installieren, dann debuggen:

```bash
# Auf Remote installieren
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Debugging ausführen
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Claude-Code-Skills

Dieses Projekt enthält einen **gdb-cli-Skill** für Claude Code, der intelligentes Debugging bereitstellt durch Kombination von Quellcode-Analyse mit Laufzeit-Zustandsinspektion.

### Skill installieren

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Nutzung in Claude Code

```
/gdb-cli

# Oder Bedarf beschreiben:
Ich habe einen Core Dump bei ./core.1234 und Binary bei ./myapp. Hilf mir beim Debuggen.
```

### Features

- **Quellcode-Korrelation**: Automatisches Lesen von Quelldateien um Crash-Punkte herum
- **Deadlock-Erkennung**: Identifiziert zirkuläre Wait-Pattern in Multi-Thread-Programmen
- **Sicherheitswarnungen**: Warnt vor Produktionsumgebungsrisiken beim Anhängen an Live-Prozesse
- **Strukturierte Berichte**: Erzeugt Analyse mit Root-Cause-Hypothesen und Nächste-Schritte

Siehe [skills/README.md](skills/README.md) für mehr Details.

## Lizenz

Apache License 2.0
