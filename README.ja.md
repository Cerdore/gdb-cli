# GDB CLI for AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | 日本語 | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | [Русский](README.ru.md) | [Türkçe](README.tr.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Italiano](README.it.md)

AIエージェント（Claude Codeなど）用に設計されたGDBデバッグツール。「thin client CLI + GDB内蔵Python RPC Server」アーキテクチャを使用し、Bashを通じてステートフルなGDBデバッグを実現します。

## 機能

- **コアダンプ分析**: コアダンプをロードし、シンボルをメモリに常駐させ、ミリ秒レベルの応答を実現
- **ライブアタッチデバッグ**: 実行中のプロセスにアタッチし、non-stopモードをサポート
- **構造化JSON出力**: すべてのコマンドがJSONで出力され、自動切り落とし/ページネーションおよび操作ヒント付き
- **セキュリティメカニズム**: コマンドホワイトリスト、ハートビートタイムアウト自動クリーンアップ、冪等性保証
- **データベース最適化**: scheduler-locking、大オブジェクトページネーション、マルチスレッド切り落とし

## 要件

- **Python**: 3.6.8+
- **GDB**: 9.0+ かつ **Pythonサポート有効**
- **OS**: Linux

### GDB Pythonサポートの確認

```bash
# GDBにPythonサポートがあるか確認
gdb -nx -q -batch -ex "python print('OK')"

# システムGDBにPythonがない場合、GCC Toolset (RHEL/CentOS)を確認
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## インストール

```bash
# PyPIからインストール
pip install gdb-cli

# またはGitHubからインストール
pip install git+https://github.com/Cerdore/gdb-cli.git

# またはクローンしてローカルにインストール
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .
```

# 環境確認
gdb-cli env-check
```

## クイックスタート

### 1. コアダンプのロード

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

出力:
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

ビッグバイナリやコアファイルをロードする場合は、セッションがreadyになるまでポーリングします:

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

> システムのデフォルトGDBがPythonサポートを持たない場合、`--gdb-path`で指定可能です:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. デバッグ操作

すべての操作は `--session` / `-s` でセッションIDを指定します:

```bash
SESSION="f465d650"

# スレッド一覧
gdb-cli threads -s $SESSION

# バックトレース（デフォルト：現在のスレッド）
gdb-cli bt -s $SESSION

# 特定のスレッドのバックトレース
gdb-cli bt -s $SESSION --thread 3

# C/C++式の評価
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# 配列要素へのアクセス
gdb-cli eval-element -s $SESSION "my_array" --index 5

# ローカル変数の表示
gdb-cli locals-cmd -s $SESSION

# 生GDBコマンドの実行
gdb-cli exec -s $SESSION "info registers"

# セッション状態の確認
gdb-cli status -s $SESSION
```

### 3. セッション管理

```bash
# アクティブなセッション一覧
gdb-cli sessions

# セッション停止
gdb-cli stop -s $SESSION
```

### 4. ライブアタッチデバッグ

```bash
# 実行中プロセスにアタッチ（デフォルト：scheduler-locking + non-stop）
gdb-cli attach --pid 9876

# シンボルファイルを指定してアタッチ
gdb-cli attach --pid 9876 --binary ./my_program

# メモリ変更と関数呼び出しを許可
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## 完全なコマンドリファレンス

### load — コアダンプのロード

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      実行ファイルパス（必須）
  --core, -c        コアダンプファイルパス（必須）
  --sysroot         sysrootパス（クロスマシンデバッグ用）
  --solib-prefix    共有ライブラリ接頭辞
  --source-dir      ソースコードディレクトリ
  --timeout         ハートビートタイムアウト秒数（デフォルト: 600）
  --gdb-path        GDB実行ファイルパス（デフォルト: "gdb"）
```

`load`は、RPCサーバーが到達可能になると、`"status": "loading"`で即座に返ります。重い検査コマンドを実行する前に、`gdb-cli status -s <session>`を使用し、`"state": "ready"`になるまで待機します。

### attach — プロセスにアタッチ

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               プロセスPID（必須）
  --binary                実行ファイルパス（省略可能）
  --scheduler-locking     scheduler-lockingを有効化（デフォルト: true）
  --non-stop              non-stopモードを有効化（デフォルト: true）
  --timeout               ハートビートタイムアウト秒数（デフォルト: 600）
  --allow-write           メモリ変更を許可
  --allow-call            関数呼び出しを許可
```

### threads — スレッド一覧

```
gdb-cli threads -s <session> [options]

  --range           スレッド範囲、例: "3-10"
  --limit           最大返却数（デフォルト: 20）
  --filter-state    状態でフィルタ（"running" / "stopped"）
```

### bt — バックトレース

```
gdb-cli bt -s <session> [options]

  --thread, -t      スレッドIDを指定
  --limit           最大フレーム数（デフォルト: 30）
  --full            ローカル変数を含める
  --range           フレーム範囲、例: "5-15"
```

### eval-cmd — 式の評価

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       再帰深度上限（デフォルト: 3）
  --max-elements    配列要素上限（デフォルト: 50）
```

### eval-element — 配列/コンテナ要素へのアクセス

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — 生GDBコマンドの実行

```
gdb-cli exec -s <session> <command>

  --safety-level    セフティレベル（readonly / readwrite / full）
```

### thread-apply — バッチスレッド操作

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## 出力例

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

## セキュリティメカニズム

### コマンドホワイトリスト（アタッチモード）

| セフティレベル | 許可されたコマンド |
|--------------|------------------|
| `readonly` (デフォルト) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` は常にブロックされます。

### ハートビートタイムアウト

デフォルトでは10分の非アクティブ後に自動でアタッチ解除と終了を行います。`--timeout`で設定可能です。

### 冪等性

PID / コアファイルあたり1つのセッションのみ許可されます。繰り返しのload/attachは既存のsession_idを返します。

## クロスマシンコアダンプデバッグ

他のマシンから取得したコアダンプを分析する場合、共有ライブラリのパスが異なる場合があります:

```bash
# sysrootの設定（パスプレフィックス置換）
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# ソースディレクトリの設定（ソースレベルデバッグ用）
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## 開発

### プロジェクト構造

```
src/gdb_cli/
├── cli.py              # CLIエントリポイント (Click)
├── client.py           # Unix Socketクライアント
├── launcher.py         # GDBプロセスランチャー
├── session.py          # セッションメタデータ管理
├── safety.py           # コマンドホワイトリストフィルタ
├── formatters.py       # JSON出力フォーマット
├── env_check.py        # 環境確認
├── errors.py           # エラー分類
└── gdb_server/
    ├── gdb_rpc_server.py   # RPCサーバーコア
    ├── handlers.py         # コマンドハンドラ
    ├── value_formatter.py  # gdb.Valueシリアライゼーション
    └── heartbeat.py         # ハートビートタイムアウト管理

skills/
└── gdb-cli/               # Claude Codeスキル（インテリジェントデバッグ用）
    ├── SKILL.md            # スキル定義
    └── evals/              # スキル評価のテストケース
```

### テスト実行

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### エンドツーエンドテスト

Pythonサポート付きGDBが必要です。`tests/crash_test/`のクラッシュテストプログラムを使用します:

```bash
# テストプログラムのコンパイル
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# コアダンプ生成
ulimit -c unlimited
./crash_test  # SIGSEGVが発生します

# コアファイルの検索
ls /path/to/core_dumps/core-crash_test-*

# E2Eテスト実行
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## 既知の制限

- `target remote` サポートなし（リモートデバッグにはSSHを使用、後述）
- マルチインフェリアデバッグサポートなし
- GDB 12.xのGuile pretty printerはスレッドセーフではないため、`format_string(raw=True)`回避策を使用
- GDB埋め込みPythonバージョンが古い場合がある（例: 3.6.8）、コードには互換性処理あり

## SSH経由のリモートデバッグ

リモートマシンで一度にインストールして実行:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

またはインストール後にデバッグ:

```bash
# リモートにインストール
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# デバッグ実行
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Claude Codeスキル

このプロジェクトには、ソースコード分析と実行時状態検査を組み合わせてインテリジェントなデバッグ支援を行う**gdb-cliスキル**が含まれています。

### スキルのインストール

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Claude Codeでの使用法

```
/gdb-cli

# またはデバッグニーズを記述:
I have a core dump at ./core.1234 and binary at ./myapp. Help me debug it.
```

### 機能

- **ソースコード関連付け**: クラッシュポイント周辺のソースファイルを自動的に読み込み
- **デッドロック検出**: マルチスレッドプログラムの循環待ちパターンを特定
- **セフティ警告**: ライブプロセスにアタッチする際の本番環境リスクをアラート
- **構造化レポート**: 根本原因仮説と次のステップを含む分析を生成

詳細は [skills/README.md](skills/README.md) を参照してください。

## ライセンス

Apache License 2.0
