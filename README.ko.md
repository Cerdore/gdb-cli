# GDB CLI for AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | 한국어 | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | [Русский](README.ru.md) | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Italiano](README.it.md)

AI 에이전트(Claude Code 등)를 위한 GDB 디버깅 도구입니다. "Thin client CLI + GDB 내장 Python RPC Server" 아키텍처를 사용하여 Bash를 통해 상태를 유지하는 GDB 디버깅을 가능하게 합니다.

## 기능

- **Core Dump 분석**: 심볼을 메모리에 상주시킨 상태로 core dump 로드 및 밀리초 단위 응답
- **실시간 Attach 디버깅**: 실행 중인 프로세스에 attaching 및 non-stop 모드 지원
- **구조화된 JSON 출력**: 모든 명령어가 JSON으로 출력되며 자동 절단/페이지네이션 및 작업 힌트 제공
- **보안 메커니즘**: 명령어 화이트리스트, heartbeat 타임아웃 자동 정리, 멱등성 보장
- **데이터베이스 최적화**: scheduler-locking, 대용량 객체 페이지네이션, 다중 스레드 절단

## 요구 사항

- **Python**: 3.6.8+
- **GDB**: 9.0+ with **Python support enabled**
- **OS**: Linux

### GDB Python 지원 확인

```bash
# GDB에 Python 지원이 있는지 확인
gdb -nx -q -batch -ex "python print('OK')"

# 시스템 GDB가 Python을 지원하지 않으면 GCC Toolset 확인 (RHEL/CentOS)
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## 설치

```bash
# PyPI에서 설치
pip install gdb-cli

# GitHub에서 설치
pip install git+https://github.com/Cerdore/gdb-cli.git

# 복제 후 로컬 설치
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .

# 환경 확인
gdb-cli env-check
```

## 빠른 시작

### 1. Core Dump 로드

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

출력:
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

대용량 바이너리 또는 core 파일을 로드할 때, 세션이 준비될 때까지 폴링합니다.

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

> 시스템 기본 GDB가 Python을 지원하지 않으면 `--gdb-path`로 지정:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. 디버깅 작업

모든 작업은 `--session` / `-s`를 사용하여 세션 ID를 지정합니다.

```bash
SESSION="f465d650"

# 스레드 목록
gdb-cli threads -s $SESSION

# Backtrace 획득 (기본값: 현재 스레드)
gdb-cli bt -s $SESSION

# 특정 스레드의 backtrace 획득
gdb-cli bt -s $SESSION --thread 3

# C/C++ 표현식 평가
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# 배열 요소 접근
gdb-cli eval-element -s $SESSION "my_array" --index 5

# 지역 변수 보기
gdb-cli locals-cmd -s $SESSION

# 원시 GDB 명령어 실행
gdb-cli exec -s $SESSION "info registers"

# 세션 상태 확인
gdb-cli status -s $SESSION
```

### 3. 세션 관리

```bash
# 모든 활성 세션 나열
gdb-cli sessions

# 세션 중지
gdb-cli stop -s $SESSION
```

### 4. 실시간 Attach 디버깅

```bash
# 실행 중인 프로세스에 attaching (기본값: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# 심볼 파일과 함께 attaching
gdb-cli attach --pid 9876 --binary ./my_program

# 메모리 수정 및 함수 호출 허용
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## 전체 명령어 레퍼런스

### load — Core Dump 로드

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b     실행 파일 경로 (필수)
  --core, -c        Core dump 파일 경로 (필수)
  --sysroot         sysroot 경로 (크로스 머신 디버깅용)
  --solib-prefix    공유 라이브러리 접두사
  --source-dir      소스 코드 디렉토리
  --timeout         Heartbeat 타임아웃(초) (기본값: 600)
  --gdb-path        GDB 실행 파일 경로 (기본값: "gdb")
```

`load`는 RPC 서버가 도달 가능해지면 즉시 `"status": "loading"`을 반환합니다. 무거운 검사 명령어를 실행하기 전에 `gdb-cli status -s <session>`을 사용하고 `"state": "ready"`가 될 때까지 기다리십시오.

### attach — 프로세스에 Attach

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               프로세스 PID (필수)
  --binary                실행 파일 경로 (선택적)
  --scheduler-locking     Scheduler-locking 활성화 (기본값: true)
  --non-stop              Non-stop 모드 활성화 (기본값: true)
  --timeout               Heartbeat 타임아웃(초) (기본값: 600)
  --allow-write           메모리 수정 허용
  --allow-call            함수 호출 허용
```

### threads — 스레드 목록

```
gdb-cli threads -s <session> [options]

  --range           스레드 범위, 예: "3-10"
  --limit           최대 반환 개수 (기본값: 20)
  --filter-state    상태 필터링 ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      스레드 ID 지정
  --limit           최대 프레임 수 (기본값: 30)
  --full            지역 변수 포함
  --range           프레임 범위, 예: "5-15"
```

### eval-cmd — 표현식 평가

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       재귀 깊이 제한 (기본값: 3)
  --max-elements    배열 요소 제한 (기본값: 50)
```

### eval-element — 배열/컨테이너 요소 접근

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — 원시 GDB 명령어 실행

```
gdb-cli exec -s <session> <command>

  --safety-level    보안 수준 (readonly / readwrite / full)
```

### thread-apply — 배치 스레드 작업

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## 출력 예제

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

## 보안 메커니즘

### 명령어 화이트리스트 (Attach 모드)

| 보안 수준             | 허용된 명령어                                |
|-----------------------|-------------------------------------------|
| `readonly` (기본값)    | bt, info, print, threads, locals, frame    |
| `readwrite`           | + set variable                            |
| `full`                | + call, continue, step, next               |

`quit`, `kill`, `shell`, `signal`은 항상 차단됩니다.

### Heartbeat 타임아웃

기본적으로 10분간 비활성화되면 자동으로 detach 및 종료됩니다. `--timeout`을 통해 구성 가능합니다.

### 멱등성

PID / Core 파일 당 하나의 세션만 허용됩니다. 반복된 load/attach는 기존 session_id를 반환합니다.

## 크로스 머신 Core Dump 디버깅

다른 머신에서 생성된 core dump를 분석할 때, 공유 라이브러리 경로가 다를 수 있습니다.

```bash
# Sysroot 설정 (경로 접두사 대체)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# 소스 디렉토리 설정 (소스 수준 디버깅용)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## 개발

### 프로젝트 구조

```
src/gdb_cli/
├── cli.py              # CLI 진입점 (Click)
├── client.py           # Unix Socket 클라이언트
├── launcher.py         # GDB 프로세스 실행기
├── session.py          # 세션 메타데이터 관리
├── safety.py           # 명령어 화이트리스트 필터
├── formatters.py       # JSON 출력 포맷팅
├── env_check.py        # 환경 확인
├── errors.py           # 오류 분류
└── gdb_server/
    ├── gdb_rpc_server.py   # RPC Server 코어
    ├── handlers.py         # 명령어 핸들러
    ├── value_formatter.py  # gdb.Value 시리얼라이제이션
    └── heartbeat.py         # Heartbeat 타임아웃 관리

skills/
└── gdb-cli/               # 지능형 디버깅을 위한 Claude Code 스킬
    ├── SKILL.md            # 스킬 정의
    └── evals/              # 스킬 평가를 위한 테스트 케이스
```

### 테스트 실행

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### End-to-End 테스트

GDB가 Python을 지원해야 합니다. `tests/crash_test/`의 충돌 테스트 프로그램을 사용합니다.

```bash
# 테스트 프로그램 컴파일
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Coredump 생성
ulimit -c unlimited
./crash_test  # SIGSEGV 발생

# Core 파일 찾기
ls /path/to/core_dumps/core-crash_test-*

# E2E 테스트 실행
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## 알려진 한계

- `target remote` 지원 불가 (원격 디버깅에는 SSH 사용)
- 다중 추론기 디버깅 지원 없음
- GDB 12.x Guile pretty printers는 스레드 안전하지 않음, `format_string(raw=True)`로 우회
- GDB 내장 Python 버전이 더 오래될 수 있음 (예: 3.6.8), 코드는 호환성 처리됨

## SSH를 통한 원격 디버깅

원격 머신에서 한 줄 명령어로 설치 및 실행:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

또는 먼저 설치한 후 디버깅:

```bash
# 원격에 설치
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# 디버깅 실행
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Claude Code Skills

이 프로젝트는 소스 코드 분석과 런타임 상태 검사를 결합하여 지능형 디버깅 지원을 제공하는 **gdb-cli 스킬**을 포함합니다.

### 스킬 설치

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Claude Code에서 사용

```
/gdb-cli

# 또는 디버깅 필요 사항 설명:
I have a core dump at ./core.1234 and binary at ./myapp. Help me debug it.
```

### 기능

- **소스 코드 연동**: 충돌 지점 주변 소스 파일 자동 읽기
- **교착 상태 감지**: 다중 스레드 프로그램에서 순환 대기 패턴 식별
- **보안 경고**: 프로세스에 live attaching할 때 생산 환경 위험에 대한 경고
- **구조화된 보고서**: 근본 원인 가설 및 다음 단계가 포함된 분석 생성

자세한 내용은 [skills/README.md](skills/README.md)를 참조하십시오.

## 라이선스

Apache License 2.0
