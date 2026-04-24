# GDB CLI for AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | [Русский](README.ru.md) | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | Français | [Italiano](README.it.md)

Un outil de débogage GDB conçu pour les agents IA (Claude Code, etc.). Utilise une architecture "CLI client léger + serveur RPC Python intégré à GDB", permettant un débogage GDB stateful via Bash.

## Fonctionnalités

- **Analyse de Core Dump** : Chargement de core dumps avec les symboles résidents en mémoire pour une réponse en temps milliseconde
- **Débogage Live Attach** : Attachement aux processus en cours d'exécution avec support du mode non-stop
- **Sorties JSON Structurées** : Toutes les commandes sortent en JSON avec troncature/pagination automatique et indices d'opération
- **Mécanismes de Sécurité** : Liste blanche des commandes, nettoyage automatique par timeout de heartbeat, garanties d'idempotence
- **Optimisation pour Bases de Données** : scheduler-locking, pagination des grands objets, troncature multi-thread

## Prérequis

- **Python** : 3.6.8+
- **GDB** : 9.0+ avec **support Python activé**
- **OS** : Linux

### Vérifier le support Python de GDB

```bash
# Vérifier si GDB a le support Python
gdb -nx -q -batch -ex "python print('OK')"

# Si le GDB système n'a pas de Python, vérifier GCC Toolset (RHEL/CentOS)
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Installation

```bash
# Installer depuis PyPI
pip install gdb-cli

# Ou installer depuis GitHub
pip install git+https://github.com/Cerdore/gdb-cli.git

# Ou cloner et installer localement
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# Vérification de l'environnement
gdb-cli env-check
```

## Démarrage Rapide

### 1. Charger un Core Dump

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Sortie :
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

Lors du chargement d'un grand binaire ou d'un fichier core, interrogez jusqu'à ce que la session soit prête :

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

> Si le GDB par défaut de votre système n'a pas de support Python, spécifiez-le avec `--gdb-path` :
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Opérations de Débogage

Toutes les opérations utilisent `--session` / `-s` pour spécifier l'ID de session :

```bash
SESSION="f465d650"

# Lister les threads
gdb-cli threads -s $SESSION

# Obtenir un backtrace (par défaut : thread actuel)
gdb-cli bt -s $SESSION

# Obtenir un backtrace pour un thread spécifique
gdb-cli bt -s $SESSION --thread 3

# Évaluer des expressions C/C++
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Accéder aux éléments de tableau
gdb-cli eval-element -s $SESSION "my_array" --index 5

# Vérifier les variables locales
gdb-cli locals-cmd -s $SESSION

# Exécuter des commandes GDB brutes
gdb-cli exec -s $SESSION "info registers"

# Vérifier le statut de la session
gdb-cli status -s $SESSION
```

### 3. Gestion des Sessions

```bash
# Lister toutes les sessions actives
gdb-cli sessions

# Arrêter une session
gdb-cli stop -s $SESSION
```

### 4. Débogage Live Attach

```bash
# Attacher à un processus en cours d'exécution (par défaut : scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Attacher avec un fichier de symboles
gdb-cli attach --pid 9876 --binary ./my_program

# Autoriser la modification mémoire et les appels de fonction
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Référence Complète des Commandes

### load — Charger un Core Dump

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      Chemin du fichier exécutable (requis)
  --core, -c        Chemin du fichier core dump (requis)
  --sysroot         Chemin sysroot (pour débogage inter-machine)
  --solib-prefix    Préfixe des bibliothèques partagées
  --source-dir      Répertoire du code source
  --timeout         Timeout du heartbeat en secondes (défaut : 600)
  --gdb-path        Chemin de l'exécutable GDB (défaut : "gdb")
```

`load` retourne immédiatement avec `"status": "loading"` une fois le serveur RPC accessible. Utilisez `gdb-cli status -s <session>` et attendez `"state": "ready"` avant les commandes d'inspection lourdes.

### attach — Attacher à un Processus

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               PID du processus (requis)
  --binary                Chemin du fichier exécutable (optionnel)
  --scheduler-locking     Activer scheduler-locking (défaut : true)
  --non-stop              Activer le mode non-stop (défaut : true)
  --timeout               Timeout du heartbeat en secondes (défaut : 600)
  --allow-write           Autoriser la modification mémoire
  --allow-call            Autoriser les appels de fonction
```

### threads — Lister les Threads

```
gdb-cli threads -s <session> [options]

  --range           Intervalle de threads, ex. "3-10"
  --limit           Nombre maximal de retours (défaut : 20)
  --filter-state    Filtrer par état ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      Spécifier l'ID du thread
  --limit           Nombre maximal de cadres (défaut : 30)
  --full            Inclure les variables locales
  --range           Intervalle de cadres, ex. "5-15"
```

### eval-cmd — Évaluer une Expression

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Limite de profondeur de récursivité (défaut : 3)
  --max-elements    Limite des éléments de tableau (défaut : 50)
```

### eval-element — Accéder aux Éléments Array/Container

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Exécuter une Commande GDB Brute

```
gdb-cli exec -s <session> <command>

  --safety-level    Niveau de sécurité (readonly / readwrite / full)
```

### thread-apply — Opérations Batch sur les Threads

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Exemples de Sortie

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

## Mécanismes de Sécurité

### Liste Blanche des Commandes (Mode Attach)

| Niveau de Sécurité | Commandes Autorisées |
|--------------------|----------------------|
| `readonly` (défaut) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` sont toujours bloqués.

### Timeout du Heartbeat

Déconnexion et arrêt automatiques après 10 minutes d'inactivité par défaut. Configurable via `--timeout`.

### Idempotence

Une seule session est autorisée par PID / Fichier core. Le chargement/attachement répété retourne l'ID de session existant.

## Débogage de Core Dump Inter-Machine

Lors de l'analyse de core dumps d'autres machines, les chemins des bibliothèques partagées peuvent différer :

```bash
# Définir sysroot (remplacement de préfixe de chemin)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Définir le répertoire source (pour le débogage au niveau source)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Développement

### Structure du Projet

```
src/gdb_cli/
├── cli.py              # Point d'entrée CLI (Click)
├── client.py           # Client Unix Socket
├── launcher.py         # Lanceur de processus GDB
├── session.py          # Gestion des métadonnées de session
├── safety.py           # Filtre de liste blanche des commandes
├── formatters.py       # Formatage de sortie JSON
├── env_check.py        # Vérification de l'environnement
├── errors.py           # Classification des erreurs
└── gdb_server/
    ├── gdb_rpc_server.py   # Cœur du serveur RPC
    ├── handlers.py         # Gestionnaires de commandes
    ├── value_formatter.py  # Sérialisation gdb.Value
    └── heartbeat.py         # Gestion du timeout de heartbeat

skills/
└── gdb-cli/               # Compétence Claude Code pour le débogage intelligent
    ├── SKILL.md            # Définition de la compétence
    └── evals/              # Cas de test pour l'évaluation de compétences
```

### Lancer les Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Tests End-to-End

Nécessite GDB avec support Python. Utilisez le programme de test de crash dans `tests/crash_test/` :

```bash
# Compiler le programme de test
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Générer un coredump
ulimit -c unlimited
./crash_test  # Produira SIGSEGV

# Trouver le fichier core
ls /path/to/core_dumps/core-crash_test-*

# Lancer le test E2E
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Limitations Connues

- Pas de support `target remote` (utilisez SSH pour le débogage distant, voir ci-dessous)
- Pas de support de débogage multi-inferior
- Les pretty printers Guile de GDB 12.x ne sont pas thread-safe, solution par `format_string(raw=True)`
- La version Python embarquée de GDB peut être ancienne (ex: 3.6.8), le code gère la compatibilité

## Débogage Distant via SSH

Installez et exécutez sur la machine distante en une commande :

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

Ou installez d'abord, puis déboguez :

```bash
# Installer sur la machine distante
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Lancer le débogage
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Compétences Claude Code

Ce projet inclut une **compétence gdb-cli** pour Claude Code qui fournit une aide de débogage intelligente en combinant l'analyse du code source avec l'inspection de l'état d'exécution.

### Installer la Compétence

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Utilisation dans Claude Code

```
/gdb-cli

# Ou décrivez votre besoin de débogage :
J'ai un core dump à ./core.1234 et un binaire à ./myapp. Aidez-moi à le déboguer.
```

### Fonctionnalités

- **Corrélation Code Source** : Lecture automatique des fichiers source autour des points de crash
- **Détection d'Interblocage** : Identification des modèles d'attente circulaire dans les programmes multi-thread
- **Avertissements de Sécurité** : Alertes sur les risques d'environnement de production lors de l'attachement à des processus en direct
- **Rapports Structurés** : Génération d'analyses avec hypothèses de causes racines et prochaines étapes

Voir [skills/README.md](skills/README.md) pour plus de détails.

## Licence

Apache License 2.0
