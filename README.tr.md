# GDB CLI for AI

[![PyPI version](https://img.shields.io/pypi/v/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![Python](https://img.shields.io/pypi/pyversions/gdb-cli.svg)](https://pypi.org/project/gdb-cli/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Cerdore/gdb-cli/actions/workflows/ci.yml)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Tiếng Việt](README.vi.md) | [Português](README.pt.md) | [Русский](README.ru.md) | Türkçe | [Deutsch](README.de.md) | [Français](README.fr.md) | [Italiano](README.it.md)

AI ajanları (Claude Code vb.) için tasarlanmış bir GDB hata ayıklama aracı. "İnce istemci CLI + GDB dahili Python RPC Sunucusu" mimarisini kullanarak Bash aracılığıyla durumlu GDB hata ayıklamasını etkinleştirir.

## Özellikler

- **Core Dump Analizi**: Semboller bellekte resident olarak tutulan core dump'ları yükleme, milisaniye seviyesinde yanıt
- **Canlı Ekleme Hata Ayıklama**: Çalışan süreçlere ekleme, non-stop modu desteği ile
- **Yapılandırılmış JSON Çıktısı**: Tüm komutlar JSON çıktısı verir, otomatik kırpma/sayfalama ve işlem ipuçları ile
- **Güvenlik Mekanizmaları**: Komut beyaz listesi, heartbeat zaman aşımı otomatik temizleme, idempotency garantileri
- **Veritabanı Optimizasyonu**: scheduler-locking, büyük nesne sayfalama, çoklu iş parçacığı kırpma

## Gereksinimler

- **Python**: 3.6.8+
- **GDB**: 9.0+ (Python desteği etkin)
- **İşletim Sistemi**: Linux

### GDB Python Desteğini Kontrol Etme

```bash
# GDB'nin Python desteği olup olmadığını kontrol edin
gdb -nx -q -batch -ex "python print('OK')"

# Sistem GDB'si Python'a sahip değilse, GCC Toolset'i (RHEL/CentOS) kontrol edin
/opt/rh/gcc-toolset-13/root/usr/bin/gdb -nx -q -batch -ex "python print('OK')"
```

## Kurulum

```bash
# PyPI'den kurulum
pip install gdb-cli

# Veya GitHub'dan kurulum
pip install git+https://github.com/Cerdore/gdb-cli.git

# Veya yerel olarak klonlayıp kurma
git clone https://github.com/Cerdore/gdb-cli.git
cd gdb-cli
pip install -e .

# Ortam kontrolü
gdb-cli env-check
```

## Hızlı Başlangıç

### 1. Core Dump Yükleme

```bash
gdb-cli load --binary ./my_program --core ./core.12345
```

Çıktı:
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

Büyük bir ikili dosya veya core dosyası yüklenirken, oturum hazır olana kadar polling yapın:

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

> Sistem varsayılan GDB'si Python desteğine sahip değilse, `--gdb-path` ile belirtin:
> ```bash
> gdb-cli load --binary ./my_program --core ./core.12345 \
>   --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
> ```

### 2. Hata Ayıklama İşlemleri

Tüm işlemler oturum kimliğini belirtmek için `--session` / `-s` kullanır:

```bash
SESSION="f465d650"

# İş parçacıklarını listele
gdb-cli threads -s $SESSION

# Backtrace al (varsayılan: geçerli iş parçacığı)
gdb-cli bt -s $SESSION

# Belirli bir iş parçacığı için backtrace al
gdb-cli bt -s $SESSION --thread 3

# C/C++ ifadelerini değerlendir
gdb-cli eval-cmd -s $SESSION "my_struct->field"

# Dizi elemanlarına eriş
gdb-cli eval-element -s $SESSION "my_array" --index 5

# Yerel değişkenleri görüntüle
gdb-cli locals-cmd -s $SESSION

# Ham GDB komutlarını çalıştır
gdb-cli exec -s $SESSION "info registers"

# Oturum durumunu kontrol et
gdb-cli status -s $SESSION
```

### 3. Oturum Yönetimi

```bash
# Tüm aktif oturumları listele
gdb-cli sessions

# Bir oturumu durdur
gdb-cli stop -s $SESSION
```

### 4. Canlı Ekleme Hata Ayıklama

```bash
# Çalışan bir sürece ekleme (varsayılan: scheduler-locking + non-stop)
gdb-cli attach --pid 9876

# Sembol dosyası ile ekleme
gdb-cli attach --pid 9876 --binary ./my_program

# Bellek değişikliğine ve fonksiyon çağrılarına izin ver
gdb-cli attach --pid 9876 --allow-write --allow-call
```

## Komut Referansı

### load — Core Dump Yükleme

```
gdb-cli load --binary <path> --core <path> [options]

  --binary, -b      İkili dosya yolu (zorunlu)
  --core, -c        Core dump dosyası yolu (zorunlu)
  --sysroot         sysroot yolu (çapraz makine hata ayıklama için)
  --solib-prefix    Paylaşılan kütüphane ön eki
  --source-dir      Kaynak kod dizini
  --timeout         Saniye cinsinden heartbeat zaman aşımı (varsayılan: 600)
  --gdb-path        GDB çalıştırılabilir dosya yolu (varsayılan: "gdb")
```

`load`, RPC sunucusu erişilebilir hale geldikten hemen sonra `"status": "loading"` ile döner. Ağır denetim komutlarından önce `gdb-cli status -s <session>` kullanın ve `"state": "ready"` olana kadar bekleyin.

### attach — Sürece Ekleme

```
gdb-cli attach --pid <pid> [options]

  --pid, -p               Süreç PID'si (zorunlu)
  --binary                İkili dosya yolu (isteğe bağlı)
  --scheduler-locking     scheduler-locking'i etkinleştir (varsayılan: true)
  --non-stop              non-stop modunu etkinleştir (varsayılan: true)
  --timeout               Saniye cinsinden heartbeat zaman aşımı (varsayılan: 600)
  --allow-write           Bellek değişikliğine izin ver
  --allow-call            Fonksiyon çağrılarına izin ver
```

### threads — İş Parçacıklarını Listeleme

```
gdb-cli threads -s <session> [options]

  --range           İş parçacığı aralığı, örn. "3-10"
  --limit           Maksimum dönüş sayısı (varsayılan: 20)
  --filter-state    Duruma göre filtrele ("running" / "stopped")
```

### bt — Backtrace

```
gdb-cli bt -s <session> [options]

  --thread, -t      İş parçacığı ID'si belirtin
  --limit           Maksimum çerçeve sayısı (varsayılan: 30)
  --full            Yerel değişkenleri dahil et
  --range           Çerçeve aralığı, örn. "5-15"
```

### eval-cmd — İfade Değerlendirme

```
gdb-cli eval-cmd -s <session> <expr> [options]

  --max-depth       Özyineleme derinliği sınırı (varsayılan: 3)
  --max-elements    Dizi eleman sınırı (varsayılan: 50)
```

### eval-element — Dizi/Konteyner Elemanlarına Erişim

```
gdb-cli eval-element -s <session> <expr> --index <N>
```

### exec — Ham GDB Komutu Çalıştırma

```
gdb-cli exec -s <session> <command>

  --safety-level    Güvenlik seviyesi (readonly / readwrite / full)
```

### thread-apply — Toplu İş Parçacığı İşlemleri

```
gdb-cli thread-apply -s <session> <command> --all
gdb-cli thread-apply -s <session> <command> --threads "1,3,5"
```

## Çıktı Örnekleri

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

## Güvenlik Mekanizmaları

### Komut Beyaz Listesi (Ekleme Modu)

| Güvenlik Seviyesi | İzinli Komutlar |
|-------------------|-----------------|
| `readonly` (varsayılan) | bt, info, print, threads, locals, frame |
| `readwrite` | + set variable |
| `full` | + call, continue, step, next |

`quit`, `kill`, `shell`, `signal` her zaman engellenir.

### Heartbeat Zaman Aşımı

Varsayılan olarak 10 dakika hareketsizlikten sonra otomatik olarak ayrılır ve çıkar. `--timeout` ile yapılandırılabilir.

### Idempotency

Her bir PID / Core dosyası için yalnızca bir oturuma izin verilir. Tekrarlanan load/attach mevcut session_id'yi döndürür.

## Çapraz Makine Core Dump Hata Ayıklama

Diğer makinelerden gelen core dump'ları analiz ederken, paylaşılan kütüphane yolları farklı olabilir:

```bash
# sysroot ayarla (yol ön ek değişimi için)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --sysroot /path/to/target/rootfs

# Kaynak dizini ayarla (kaynak seviyesi hata ayıklama için)
gdb-cli load --binary ./my_program --core ./core.1234 \
  --source-dir /path/to/source
```

## Geliştirme

### Proje Yapısı

```
src/gdb_cli/
├── cli.py              # CLI giriş noktası (Click)
├── client.py           # Unix Socket istemcisi
├── launcher.py         # GDB süreç başlatıcı
├── session.py          # Oturum meta veri yönetimi
├── safety.py           # Komut beyaz listesi filtresi
├── formatters.py       # JSON çıktı biçimlendirme
├── env_check.py        # Ortam kontrolü
├── errors.py           # Hata sınıflandırma
└── gdb_server/
    ├── gdb_rpc_server.py   # RPC Sunucusu çekirdeği
    ├── handlers.py         # Komut işleyicileri
    ├── value_formatter.py  # gdb.Value serielleştirme
    └── heartbeat.py         # Heartbeat zaman aşımı yönetimi

skills/
└── gdb-cli/               # Akıllı hata ayıklama için Claude Code becerisi
    ├── SKILL.md            # Beceri tanımı
    └── evals/              # Beceri değerlendirme test durumları
```

### Testleri Çalıştırma

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Uçtan Uca Test

Python desteği olan GDB gerektirir. `tests/crash_test/` içindeki çökme test programını kullanın:

```bash
# Test programını derleme
cd tests/crash_test
gcc -g -pthread -o crash_test crash_test_c.c

# Coredump oluşturma
ulimit -c unlimited
./crash_test  # SIGSEGV verecek

# Core dosyasını bulma
ls /path/to/core_dumps/core-crash_test-*

# Uçtan Uca testi çalıştırma
gdb-cli load --binary ./crash_test --core /path/to/core \
  --gdb-path /opt/rh/gcc-toolset-13/root/usr/bin/gdb
```

## Bilinen Sınırlamalar

- `target remote` desteği yok (uzaktan hata ayıklama için SSH kullanın, aşağıya bakın)
- Çoklu inferior hata ayıklama desteği yok
- GDB 12.x Guile pretty printers thread-safe değil, geçici çözüm `format_string(raw=True)` ile
- GDB gömülü Python sürümü daha eski olabilir (örn. 3.6.8), kod uyumluluk işlemasına sahiptir

## SSH Üzerinden Uzaktan Hata Ayıklama

Uzak makinede tek komutla kurulum ve çalıştırma:

```bash
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git && gdb-cli load --binary ./my_program --core ./core.12345"
```

Veya önce kurun, sonra hata ayıklayın:

```bash
# Uzakta kurulum
ssh user@remote-host "pip install git+https://github.com/Cerdore/gdb-cli.git"

# Hata ayıklama çalıştırma
ssh user@remote-host "gdb-cli load --binary ./my_program --core ./core.12345"
```

## Claude Code Becerileri

Bu proje, kaynak kodu analizini çalışma zamanı durumu incelemesiyle birleştiren akıllı hata ayıklama yardimi sağlayan bir **gdb-cli** becerisi içerir.

### Beceriyi Kurma

```bash
bunx skills add https://github.com/Cerdore/gdb-cli --skill=gdb-cli
```

### Claude Code'da Kullanım

```
/gdb-cli

# Veya hata ayıklama ihtiyacınızı açıklayın:
I have a core dump at ./core.1234 and binary at ./myapp. Help me debug it.
```

### Özellikler

- **Kaynak Kodu Korelasyonu**: Çökme noktalarının etrafındaki kaynak dosyaları otomatik olarak okuma
- **Ölü Kilitleme Tespiti**: Çoklu iş parçacıklı programlarda döngüsel bekleyiş desenlerini tanımlama
- **Güvenlik Uyarıları**: Canlı süreçlere eklenirken üretim ortamı riskleri hakkında uyarılar
- **Yapılandırılmış Raporlar**: Kök neden hipotezleri ve sonraki adımlarla analiz oluşturma

Daha fazla bilgi için [skills/README.md](skills/README.md) adresine bakın.

## Lisans

Apache License 2.0
