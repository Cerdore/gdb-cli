# Status Command Elapsed Time Display

**Date**: 2026-03-23
**Status**: Approved

## Problem

`gdb-cli status -s <session_id>` in loading state does not show how long since the session was started. Users need this information to gauge loading progress and detect stuck sessions.

## Design

Add a human-readable `elapsed` field to status output **only in loading state**.

### Output Format

```json
{
  "session_id": "a97a094c",
  "state": "loading",
  "elapsed": "2m30s",
  "message": "GDB process alive, not yet responding"
}
```

### Formatting Rules

Input seconds are truncated to integer via `int(seconds)`. Negative values (clock skew) are clamped to 0.

| Duration | Format | Example |
|----------|--------|---------|
| < 60s | `"{s}s"` | `"42s"` |
| >= 60s, < 3600s | `"{m}m{s}s"` | `"2m30s"` |
| >= 3600s | `"{h}h{m}m"` | `"1h5m"` |

For very long durations (25h+), hours continue to accumulate (e.g. `"25h0m"`). No day-level formatting.

### Changes

**`cli.py` — `status()` function**

Add `import time` to imports.

1. **Fallback path** (socket not connected, in `except GDBClientError` block): Calculate elapsed from `SessionMeta.started_at` via `time.time() - meta.started_at`, format with `_format_elapsed()`, add `"elapsed"` key to output dict.

2. **Normal path** (socket connected): When server returns `state == "loading"` and `elapsed` key exists as a numeric value, replace it with formatted string via `_format_elapsed()`. If `elapsed` key is absent, do not add it.

**`cli.py` — new helper `_format_elapsed(seconds: float) -> str`**

Formats a float seconds value into human-readable string per the rules above. Clamps negative values to 0, truncates to int.

### Out of Scope

- `session_meta` key leaking in normal-path loading response — pre-existing behavior, separate concern
- `sessions` (list) command elapsed display — not requested
- `gdb_rpc_server.py` — server continues returning `elapsed` as float, no changes
- `session.py` — no changes to `SessionMeta`
- `ready` state output — no elapsed field added

### Testing

- Unit test `_format_elapsed()` with boundary values: negative, 0s, 59s, 60s, 150s, 3600s, 3661s
- Integration test: status in loading fallback path includes `elapsed` field
- Integration test: status via RPC in loading state formats elapsed as string
