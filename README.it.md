# GDB CLI for AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | [Русский](README.ru.md) | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | Italiano

Uno strumento di debug GDB progettato per Agenti IA (Claude Code, ecc.). Utilizza un'architettura "thin client CLI + server RPC Python integrato in GDB", consentendo il debug GDB stateful tramite Bash.

## Caratteristiche

- **Analisi Core Dump**: Carica core dump con simboli residenti in memoria per risposte a livello di millisecondi
- **Debug Live Attach**: Si collega a processi in esecuzione con supporto modalità non-stop
- **Output JSON Strutturato**: Tutti i comandi producono JSON con troncamento/paginazione automatici e suggerimenti operativi
- **Meccanismi di Sicurezza**: Whitelist comandi, timeout heartbeat con pulizia automatica, garanzie di idempotenza
- **Ottimizzato per Database**: scheduler-locking, paginazione grandi oggetti, troncamento multi-thread

## Requisiti

- **Python**: 3.6.8+
- **GDB**: 9.0+ con **supporto Python abilitato**
- **OS**: Linux

### Verificare il Supporto Python in GDB

```bash
# Verifica se GDB ha il supporto Python
gdb -nx -q -batch -ex "python print('OK')"

# Se il GDB di sistema non ha Python, controlla GCC Toolset (RHEL/CentOS)
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Installazione

```bash
# Installa da PyPI
pip install gdb-cli

# Oppure installa da GitHub
pip install git+https://github.com/Cerdore/gdb-cli.git

# Oppure clona e installa localmente
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# Verifica ambiente
gdb-cli env-check
```

## Avvio Rapido

### 1. Caricare Core Dump

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Output:
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

Quando carichi un binario o file core di grandi dimensioni, esegui polling fino a quando la sessione diventa pronta:

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

> Se il GDB predefinito del sistema non ha supporto Python, specificalo con `--gdb-path`:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Operazioni di Debug

Tutte le operazioni usano `--session` / `-s` per specificare l'ID sessione:

```bash
SESSION="f465d650"

# Elenca i thread
gdb-cli threads -s $SESSION

# Ottieni backtrace (predefinito: thread corrente)
gdb-cli bt -s $SESSION

# Ottieni backtrace per un thread specifico
gdb-cli bt -s $SESSION --thread 3

# Valuta espressioni C/C++
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Accedi agli elementi di array
gdb-cli eval-element -s $SESSION "my_array" --index 5

# Visualizza variabili locali
gdb-cli locals-cmd -s $SESSION

# Esegui comandi GDB raw
gdb-cli exec -s $SESSION "info registers"

# Controlla stato sessione
gdb-cli status -s $SESSION
```

### 3. Gestione Sessioni

```bash
# Elenca tutte le sessioni attive
gdb-cli sessions

# Ferma una sessione
gdb-cli stop -s $SESSION
```

### 4. Debug Live Attach

```bash
# Collegati a un processo in esecuzione (predefinito: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Collegati con file di simboli
gdb-cli attach --pid 9876 --binary ./my_program

# Consenti modifica memoria e chiamate a funzione
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Riferimento Completo dei Comandi

### load — Caricare Core Dump

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      Percorso file eseguibile (richiesto)
  --core, -c        Percorso file core dump (richiesto)
  --sysroot         Percorso sysroot (per debugging cross-machine)
  --solib-prefix    Prefisso librerie condivise
  --source-dir      Directory codice sorgente
  --timeout         Timeout heartbeat in secondi (predefinito: 600)
  --gdb-path        Percorso eseguibile GDB (predefinito: "gdb")
```

`load` ritorna immediatamente con `"status": "loading"` dopo che il server RPC diventa raggiungibile. Usa `gdb-cli status -s <session>` e attendi `"state": "ready"` prima di eseguire comandi di ispezione pesanti.

### attach — Collegati a un Processo

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               PID processo (richiesto)
  --binary                Percorso file eseguibile (opzionale)
  --scheduler-locking     Abilita scheduler-locking (predefinito: true)
  --non-stop              Abilita modalità non-stop (predefinito: true)
  --timeout               Timeout heartbeat in secondi (predefinito: 600)
  --allow-write           Consenti modifica memoria
  --allow-call            Consenti chiamate a funzione
```

### threads — Elenca Thread

```
gdb-cli threads -s <session> [options]

  --range           Intervallo thread, es. "3-10"
  --limit           Numero massimo restituito (predefinito: 20)
  --filter-state    Filtra per stato ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      Specifica ID thread
  --limit           Numero massimo frame (predefinito: 30)
  --full            Includi variabili locali
  --range           Intervallo frame, es. "5-15"
```

### eval-cmd — Valuta Espressione

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Limite profondità ricorsione (predefinito: 3)
  --max-elements    Limite elementi array (predefinito: 50)
```

### eval-element — Accedi a Elementi Array/Container

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Esegui Comando GDB Raw

```
gdb-cli exec -s <session> <command>

  --safety-level    Livello sicurezza (readonly / readwrite / full)
```

### thread-apply — Operazioni Batch su Thread

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Esempi di Output

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

## Meccanismi di Sicurezza

### Whitelist Comandi (Modalità Attach)

| Livello Sicurezza | Comandi Consentiti |
|-------------------|---------------------|
| `readonly` (predefinito) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` sono sempre bloccati.

### Timeout Heartbeat

Si stacca e termina automaticamente dopo 10 minuti di inattività per impostazione predefinita. Configurabile tramite `--timeout`.

### Idempotenza

È consentita solo una sessione per PID / file core. Caricamenti/attach ripetuti restituiscono il session_id esistente.

## Debugging Cross-Machine di Core Dump

Quando analizzi core dump da altre macchine, i percorsi delle librerie condivise possono differire:

```bash
# Imposta sysroot (sostituzione prefisso percorso)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Imposta directory sorgente (per debugging a livello sorgente)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Sviluppo

### Struttura del Progetto

```
src/gdb_cli/
├── cli.py              # Punto di ingresso CLI (Click)
├── client.py           # Client Unix Socket
├── launcher.py         # Lanciatore processo GDB
├── session.py          # Gestione metadati sessione
├── safety.py           # Filtro whitelist comandi
├── formatters.py       # Formattazione output JSON
├── env_check.py        # Verifica ambiente
├── errors.py           # Classificazione errori
└── gdb_server/
    ├── gdb_rpc_server.py   # Core server RPC
    ├── handlers.py         # Gestori comandi
    ├── value_formatter.py  # Serializzazione gdb.Value
    └── heartbeat.py        # Gestione timeout heartbeat

skills/
└── gdb-cli/               # Skill Claude Code per debugging intelligente
    ├── SKILL.md            # Definizione skill
    └── evals/              # Casi test per valutazione skill
```

### Eseguire Test

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Test End-to-End

Richiede GDB con supporto Python. Usa il programma di test crash in `tests/crash_test/`:

```bash
# Compila programma di test
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Genera coredump
ulimit -c unlimited
./crash_test  # Produrrà SIGSEGV

# Trova file core
ls /path/to/core_dumps/core-crash_test-*

# Esegui test E2E
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Limitazioni Note

- Nessun supporto `target remote` (usa SSH per debug remoto, vedi sotto)
- Nessun supporto debugging multi-inferior
- I pretty printer Guile in GDB 12.x non sono thread-safe, soluzione tramite `format_string(raw=True)`
- La versione Python integrata in GDB potrebbe essere più vecchia (es. 3.6.8), il codice ha gestione compatibilità

## Debugging Remoto via SSH

Installa ed esegui su macchina remota in un solo comando:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

Oppure installa prima, poi esegui debug:

```bash
# Installa su remoto
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Esegui debug
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Skill Claude Code

Questo progetto include una **skill gdb-cli** per Claude Code che fornisce assistenza di debug intelligente combinando analisi del codice sorgente con ispezione dello stato runtime.

### Installare la Skill

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Utilizzo in Claude Code

```
/gdb-cli

# Oppure descrivi la tua esigenza di debug:
Ho un core dump in ./core.1234 e il binario in ./myapp. Aiutami a debuggarlo.
```

### Caratteristiche

- **Correlazione Codice Sorgente**: Legge automaticamente i file sorgente intorno ai punti di crash
- **Rilevamento Deadlock**: Identifica pattern di attesa circolare in programmi multi-thread
- **Avvisi di Sicurezza**: Avvisa sui rischi dell'ambiente di produzione quando ci si collega a processi live
- **Report Strutturati**: Genera analisi con ipotesi sulla causa principale e passi successivi

Vedi [skills/README.md](skills/README.md) per maggiori dettagli.

## Licenza

Apache License 2.0
