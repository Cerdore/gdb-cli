# GDB CLI for AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | Português | [Русский](README.ru.md) | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Italiano](README.it.md)

Uma ferramenta de debug do GDB projetada para Agentes de IA (Claude Code, etc.). Usa uma arquitetura "CLI cliente leve + Servidor RPC Python embutido no GDB", permitindo debug do GDB com estado através do Bash.

## Funcionalidades

- **Análise de Core Dump**: Carrega core dumps com símbolos residindo na memória para resposta em nível de milissegundo
- **Debug em Tempo Real (Attach)**: Conecta a processos em execução com suporte a modo non-stop
- **Saída JSON Estruturada**: Todos os comandos produzem JSON com truncamento/paginação automática e dicas de operação
- **Mecanismos de Segurança**: Lista branca de comandos, limpeza automática por timeout de heartbeat, garantias de idempotência
- **Otimizado para Banco de Dados**: scheduler-locking, paginação de objetos grandes, truncamento multi-thread

## Requisitos

- **Python**: 3.6.8+
- **GDB**: 9.0+ com **suporte a Python habilitado**
- **SO**: Linux

### Verificar Suporte Python do GDB

```bash
# Verificar se o GDB tem suporte a Python
gdb -nx -q -batch -ex "python print('OK')"

# Se o GDB do sistema não tiver Python, verifique GCC Toolset (RHEL/CentOS)
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Instalação

```bash
# Instalar do PyPI
pip install gdb-cli

# Ou instalar do GitHub
pip install git+https://github.com/Cerdore/gdb-cli.git

# Ou clonar e instalar localmente
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# Verificação de ambiente
gdb-cli env-check
```

## Início Rápido

### 1. Carregar Core Dump

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Saída:
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

Ao carregar um binário ou arquivo core grande, faça polling até que a sessão fique pronta:

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

> Se o GDB padrão do seu sistema não tiver suporte a Python, especifique-o com `--gdb-path`:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Operações de Debug

Todas as operações usam `--session` / `-s` para especificar o ID da sessão:

```bash
SESSION="f465d650"

# Listar threads
gdb-cli threads -s $SESSION

# Obter backtrace (padrão: thread atual)
gdb-cli bt -s $SESSION

# Obter backtrace para uma thread específica
gdb-cli bt -s $SESSION --thread 3

# Avaliar expressões C/C++
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Acessar elementos de array
gdb-cli eval-element -s $SESSION "my_array" --index 5

# Ver variáveis locais
gdb-cli locals-cmd -s $SESSION

# Executar comandos brutos do GDB
gdb-cli exec -s $SESSION "info registers"

# Verificar status da sessão
gdb-cli status -s $SESSION
```

### 3. Gerenciamento de Sessões

```bash
# Listar todas as sessões ativas
gdb-cli sessions

# Parar uma sessão
gdb-cli stop -s $SESSION
```

### 4. Debug em Tempo Real (Attach)

```bash
# Conectar a um processo em execução (padrão: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Conectar com arquivo de símbolos
gdb-cli attach --pid 9876 --binary ./my_program

# Permitir modificação de memória e chamadas de função
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Referência Completa de Comandos

### load — Carregar Core Dump

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      Caminho do arquivo executável (obrigatório)
  --core, -c        Caminho do arquivo core dump (obrigatório)
  --sysroot         Caminho do sysroot (para debug entre máquinas)
  --solib-prefix    Prefixo de bibliotecas compartilhadas
  --source-dir      Diretório do código-fonte
  --timeout         Timeout do heartbeat em segundos (padrão: 600)
  --gdb-path        Caminho do executável GDB (padrão: "gdb")
```

`load` retorna imediatamente com `"status": "loading"` após o servidor RPC tornar-se acessível. Use `gdb-cli status -s <session>` e espere por `"state": "ready"` antes de comandos pesados de inspeção.

### attach — Conectar a Processo

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               PID do processo (obrigatório)
  --binary                Caminho do arquivo executável (opcional)
  --scheduler-locking     Habilitar scheduler-locking (padrão: true)
  --non-stop              Habilitar modo non-stop (padrão: true)
  --timeout               Timeout do heartbeat em segundos (padrão: 600)
  --allow-write           Permitir modificação de memória
  --allow-call            Permitir chamadas de função
```

### threads — Listar Threads

```
gdb-cli threads -s <session> [options]

  --range           Intervalo de threads, ex: "3-10"
  --limit           Contagem máxima de retorno (padrão: 20)
  --filter-state    Filtrar por estado ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      Especificar ID da thread
  --limit           Contagem máxima de frames (padrão: 30)
  --full            Incluir variáveis locais
  --range           Intervalo de frames, ex: "5-15"
```

### eval-cmd — Avaliar Expressão

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Limite de profundidade de recursão (padrão: 3)
  --max-elements    Limite de elementos de array (padrão: 50)
```

### eval-element — Acessar Elementos de Array/Container

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Executar Comando Bruto do GDB

```
gdb-cli exec -s <session> <command>

  --safety-level    Nível de segurança (readonly / readwrite / full)
```

### thread-apply — Operações em Lote de Threads

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Exemplos de Saída

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

## Mecanismos de Segurança

### Lista Branca de Comandos (Modo Attach)

| Nível de Segurança | Comandos Permitidos |
|-------------------|---------------------|
| `readonly` (padrão) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` são sempre bloqueados.

### Timeout de Heartbeat

Desconecta e encerra automaticamente após 10 minutos de inatividade por padrão. Configurável via `--timeout`.

### Idempotência

É permitida apenas uma sessão por PID / arquivo core. Carregar/conectar repetidamente retorna o session_id existente.

## Debug de Core Dump entre Máquinas

Ao analisar core dumps de outras máquinas, os caminhos de bibliotecas compartilhadas podem diferir:

```bash
# Definir sysroot (substituição de prefixo de caminho)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Definir diretório de código-fonte (para debug em nível de fonte)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Desenvolvimento

### Estrutura do Projeto

```
src/gdb_cli/
├── cli.py              # Ponto de entrada da CLI (Click)
├── client.py           # Cliente Unix Socket
├── launcher.py         # Iniciador de processo GDB
├── session.py          # Gerenciamento de metadados de sessão
├── safety.py           # Filtro de lista branca de comandos
├── formatters.py       # Formatação de saída JSON
├── env_check.py        # Verificação de ambiente
├── errors.py           # Classificação de erros
└── gdb_server/
    ├── gdb_rpc_server.py   # Núcleo do servidor RPC
    ├── handlers.py         # Manipuladores de comandos
    ├── value_formatter.py  # Serialização gdb.Value
    └── heartbeat.py         # Gerenciamento de timeout de heartbeat

skills/
└── gdb-cli/               # Skill do Claude Code para debug inteligente
    ├── SKILL.md            # Definição da skill
    └── evals/              # Casos de teste para avaliação da skill
```

### Executar Testes

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Testes de Ponta a Ponta

Requer GDB com suporte a Python. Use o programa de teste de crash em `tests/crash_test/`:

```bash
# Compilar programa de teste
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Gerar coredump
ulimit -c unlimited
./crash_test  # Will SIGSEGV

# Encontrar arquivo core
ls /path/to/core_dumps/core-crash_test-*

# Executar teste E2E
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Limitações Conhecidas

- Sem suporte a `target remote` (use SSH para debug remoto, veja abaixo)
- Sem suporte a debug multi-inferior
- Impressoras bonitas Guile do GDB 12.x não são thread-safe, workaround via `format_string(raw=True)`
- A versão Python embutida do GDB pode ser mais antiga (ex: 3.6.8), o código tem manipulação de compatibilidade

## Debug Remoto via SSH

Instale e execute na máquina remota em um único comando:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

Ou instale primeiro e depois faça debug:

```bash
# Instalar na remota
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Executar debug
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Skills do Claude Code

Este projeto inclui uma **skill gdb-cli** para o Claude Code que fornece assistência de debug inteligente combinando análise de código-fonte com inspeção de estado em tempo de execução.

### Instalar a Skill

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Uso no Claude Code

```
/gdb-cli

# Ou descreva sua necessidade de debug:
Tenho um core dump em ./core.1234 e binário em ./myapp. Ajude-me a depurá-lo.
```

### Funcionalidades

- **Correlação de Código-Fonte**: Lê automaticamente arquivos de fonte ao redor de pontos de crash
- **Detecção de Deadlock**: Identifica padrões de espera circular em programas multi-thread
- **Avisos de Segurança**: Alerta sobre riscos de ambiente de produção ao conectar a processos em tempo real
- **Relatórios Estruturados**: Gera análise com hipóteses de causa raiz e próximos passos

Veja [skills/README.md](skills/README.md) para mais detalhes.

## Licença

Apache License 2.0
