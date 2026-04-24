# GDB CLI para IA

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | Español | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | [Русский](README.ru.md) | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Italiano](README.it.md)

Una herramienta de depuración GDB diseñada para Agentes de IA (Claude Code, etc.). Utiliza una arquitectura de "CLI cliente ligero + Servidor RPC Python integrado en GDB", permitiendo la depuración GDB con estado a través de Bash.

## Características

- **Análisis de Core Dump**: Carga volcados de memoria con símbolos residentes para respuesta en milisegundos
- **Depuración Live Attach**: Adjuntar a procesos en ejecución con soporte para modo non-stop
- **Salida JSON Estructurada**: Todos los comandos producen JSON con truncamiento/paginación automática y sugerencias de operación
- **Mecanismos de Seguridad**: Lista blanca de comandos, limpieza automática por timeout de heartbeat, garantías de idempotencia
- **Optimizado para Bases de Datos**: scheduler-locking, paginación de objetos grandes, truncamiento multi-hilo

## Requisitos

- **Python**: 3.6.8+
- **GDB**: 9.0+ con **soporte Python habilitado**
- **SO**: Linux

### Verificar Soporte Python en GDB

```bash
# Verificar si GDB tiene soporte Python
gdb -nx -q -batch -ex "python print('OK')"

# Si el GDB del sistema carece de Python, verificar GCC Toolset (RHEL/CentOS)
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Instalación

```bash
# Instalar desde PyPI
pip install gdb-cli

# O instalar desde GitHub
pip install git+https://github.com/Cerdore/gdb-cli.git

# O clonar e instalar localmente
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# Verificación de entorno
gdb-cli env-check
```

## Inicio Rápido

### 1. Cargar Core Dump

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Salida:
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

Al cargar un binario grande o archivo core, consulta hasta que la sesión esté lista:

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

> Si el GDB predeterminado del sistema no tiene soporte Python, especifícalo con `--gdb-path`:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Operaciones de Depuración

Todas las operaciones usan `--session` / `-s` para especificar el ID de sesión:

```bash
SESSION="f465d650"

# Listar hilos
gdb-cli threads -s $SESSION

# Obtener backtrace (predeterminado: hilo actual)
gdb-cli bt -s $SESSION

# Obtener backtrace de un hilo específico
gdb-cli bt -s $SESSION --thread 3

# Evaluar expresiones C/C++
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Acceder a elementos de array
gdb-cli eval-element -s $SESSION "my_array" --index 5

# Ver variables locales
gdb-cli locals-cmd -s $SESSION

# Ejecutar comandos GDB sin procesar
gdb-cli exec -s $SESSION "info registers"

# Verificar estado de sesión
gdb-cli status -s $SESSION
```

### 3. Gestión de Sesiones

```bash
# Listar todas las sesiones activas
gdb-cli sessions

# Detener una sesión
gdb-cli stop -s $SESSION
```

### 4. Depuración Live Attach

```bash
# Adjuntar a un proceso en ejecución (predeterminado: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Adjuntar con archivo de símbolos
gdb-cli attach --pid 9876 --binary ./my_program

# Permitir modificación de memoria y llamadas a funciones
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Referencia Completa de Comandos

### load — Cargar Core Dump

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      Ruta del archivo ejecutable (requerido)
  --core, -c        Ruta del archivo core dump (requerido)
  --sysroot         Ruta sysroot (para depuración entre máquinas)
  --solib-prefix    Prefijo de bibliotecas compartidas
  --source-dir      Directorio de código fuente
  --timeout         Timeout de heartbeat en segundos (predeterminado: 600)
  --gdb-path        Ruta ejecutable de GDB (predeterminado: "gdb")
```

`load` retorna inmediatamente con `"status": "loading"` después de que el servidor RPC sea alcanzable. Usa `gdb-cli status -s <session>` y espera `"state": "ready"` antes de comandos de inspección pesados.

### attach — Adjuntar a Proceso

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               PID del proceso (requerido)
  --binary                Ruta del archivo ejecutable (opcional)
  --scheduler-locking     Habilitar scheduler-locking (predeterminado: true)
  --non-stop              Habilitar modo non-stop (predeterminado: true)
  --timeout               Timeout de heartbeat en segundos (predeterminado: 600)
  --allow-write           Permitir modificación de memoria
  --allow-call            Permitir llamadas a funciones
```

### threads — Listar Hilos

```
gdb-cli threads -s <session> [options]

  --range           Rango de hilos, ej., "3-10"
  --limit           Cantidad máxima de retorno (predeterminado: 20)
  --filter-state    Filtrar por estado ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      Especificar ID de hilo
  --limit           Cantidad máxima de frames (predeterminado: 30)
  --full            Incluir variables locales
  --range           Rango de frames, ej., "5-15"
```

### eval-cmd — Evaluar Expresión

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Límite de profundidad de recursión (predeterminado: 3)
  --max-elements    Límite de elementos de array (predeterminado: 50)
```

### eval-element — Acceder a Elementos de Array/Contenedor

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Ejecutar Comando GDB Sin Procesar

```
gdb-cli exec -s <session> <command>

  --safety-level    Nivel de seguridad (readonly / readwrite / full)
```

### thread-apply — Operaciones por Lotes en Hilos

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Ejemplos de Salida

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

## Mecanismos de Seguridad

### Lista Blanca de Comandos (Modo Attach)

| Nivel de Seguridad | Comandos Permitidos |
|--------------------|---------------------|
| `readonly` (predeterminado) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` siempre están bloqueados.

### Timeout de Heartbeat

Se desconecta y termina automáticamente después de 10 minutos de inactividad por defecto. Configurable mediante `--timeout`.

### Idempotencia

Solo se permite una sesión por PID / archivo core. Cargas/attachments repetidos retornan el session_id existente.

## Depuración de Core Dumps entre Máquinas

Al analizar core dumps de otras máquinas, las rutas de bibliotecas compartidas pueden diferir:

```bash
# Establecer sysroot (reemplazo de prefijo de ruta)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Establecer directorio de código fuente (para depuración a nivel de fuente)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Desarrollo

### Estructura del Proyecto

```
src/gdb_cli/
├── cli.py              # Punto de entrada CLI (Click)
├── client.py           # Cliente Unix Socket
├── launcher.py         # Lanzador de proceso GDB
├── session.py          # Gestión de metadatos de sesión
├── safety.py           # Filtro de lista blanca de comandos
├── formatters.py       # Formateo de salida JSON
├── env_check.py        # Verificación de entorno
├── errors.py           # Clasificación de errores
└── gdb_server/
    ├── gdb_rpc_server.py   # Núcleo del Servidor RPC
    ├── handlers.py         # Manejadores de comandos
    ├── value_formatter.py  # Serialización gdb.Value
    └── heartbeat.py        # Gestión de timeout de heartbeat

skills/
└── gdb-cli/               # Skill de Claude Code para depuración inteligente
    ├── SKILL.md            # Definición del skill
    └── evals/              # Casos de prueba para evaluación del skill
```

### Ejecutar Pruebas

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Pruebas End-to-End

Requiere GDB con soporte Python. Usa el programa de prueba de crash en `tests/crash_test/`:

```bash
# Compilar programa de prueba
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Generar coredump
ulimit -c unlimited
./crash_test  # Producirá SIGSEGV

# Encontrar archivo core
ls /path/to/core_dumps/core-crash_test-*

# Ejecutar prueba E2E
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Limitaciones Conocidas

- Sin soporte para `target remote` (usa SSH para depuración remota, ver abajo)
- Sin soporte para depuración multi-inferior
- Los pretty printers Guile en GDB 12.x no son thread-safe, solución mediante `format_string(raw=True)`
- La versión de Python embebido en GDB puede ser más antigua (ej., 3.6.8), el código tiene manejo de compatibilidad

## Depuración Remota vía SSH

Instalar y ejecutar en máquina remota en un solo comando:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

O instalar primero, luego depurar:

```bash
# Instalar en remoto
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Ejecutar depuración
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Skills de Claude Code

Este proyecto incluye un **skill gdb-cli** para Claude Code que proporciona asistencia de depuración inteligente combinando análisis de código fuente con inspección de estado en tiempo de ejecución.

### Instalar el Skill

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Uso en Claude Code

```
/gdb-cli

# O describe tu necesidad de depuración:
Tengo un core dump en ./core.1234 y el binario en ./myapp. Ayúdame a depurarlo.
```

### Características

- **Correlación de Código Fuente**: Lee automáticamente archivos fuente alrededor de los puntos de crash
- **Detección de Deadlock**: Identifica patrones de espera circular en programas multi-hilo
- **Advertencias de Seguridad**: Alerta sobre riesgos en entornos de producción al adjuntar a procesos en vivo
- **Informes Estructurados**: Genera análisis con hipótesis de causa raíz y próximos pasos

Consulta [skills/README.md](skills/README.md) para más detalles.

## Licencia

Apache License 2.0
