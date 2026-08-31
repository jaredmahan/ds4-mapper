# DS4 Mapper — Profiles & CLI Design

**Date:** 2026-08-31
**Status:** Approved

## Overview

Add a TOML-based profile system and an interactive terminal CLI to ds4-mapper. Profiles define button/axis/trigger mappings and can be switched at runtime without restarting the mapper. The terminal displays a live Rich layout above a prompt_toolkit input line.

---

## Architecture

The single `ds4_mapper.py` is replaced by a package and a `main.py` entry point.

```
ds4-mapper/
  ds4mapper/
    __init__.py
    profiles.py      # load/save/validate TOML profiles
    mapper.py        # pygame controller loop (thread)
    cli.py           # Rich Live display + prompt_toolkit input loop
    keys.py          # key name ↔ pynput Key resolution
  profiles/
    default.toml     # ships with repo, mirrors current hardcoding
  tests/
    test_profiles.py
    test_keys.py
    test_mapper.py
  main.py
```

### Runtime Threads

| Thread | Responsibility |
|---|---|
| Main | `prompt_toolkit` `PromptSession` reads commands; `patch_stdout=True` lets Rich print above |
| Mapper | pygame event loop — reads controller, fires keypresses via pynput |
| Rich Live | Renders profile info + button activity panel at ~30fps |

Shared state between main and mapper is a single `current_profile: Profile` reference protected by `threading.Lock`. Switching profiles replaces the reference atomically.

### Dependencies

- `rich` — live terminal layout
- `prompt_toolkit` — input line with history and tab-completion
- `tomli-w` — writing TOML files (reading via stdlib `tomllib` on Python 3.11+)
- existing: `pygame-ce`, `pynput`

---

## Profile Format

Profiles are TOML files in `profiles/`. Filename minus `.toml` is the profile name. `default.toml` ships with the repo.

```toml
name = "default"
description = "Standard browser game layout"

[buttons]
# index = "key"
0  = "x"        # Cross
1  = "z"        # Circle
2  = "s"        # Square
3  = "a"        # Triangle
4  = "v"        # Share
6  = "enter"    # Options / START
9  = "q"        # L1
10 = "e"        # R1
11 = "up"       # D-pad up
12 = "down"     # D-pad down
13 = "left"     # D-pad left
14 = "right"    # D-pad right

[axes]
# index = ["negative_key", "positive_key"]
0 = ["f", "h"]  # Left stick X
1 = ["t", "g"]  # Left stick Y
2 = ["j", "l"]  # Right stick X
3 = ["i", "k"]  # Right stick Y

[triggers]
# index = "key"
4 = "tab"       # L2
5 = "r"         # R2
```

### Key Resolution (`keys.py`)

Single characters (`"x"`, `"v"`) pass through directly. Special names resolve to `pynput.Key` values:

| Name | Resolves to |
|---|---|
| `enter` | `Key.enter` |
| `tab` | `Key.tab` |
| `up` / `down` / `left` / `right` | `Key.up` etc. |
| `space` | `Key.space` |
| `esc` | `Key.esc` |
| `shift` / `ctrl` / `alt` | `Key.shift` etc. |

Unknown key names raise `ValueError` with the name included in the message. Validation runs at load time so bad profiles fail fast.

---

## CLI Commands

Typed at the prompt while the mapper is running:

| Command | Description |
|---|---|
| `list` | Show all available profiles |
| `switch <name>` | Load profile by name (tab-completes) |
| `current` | Show active profile name and description |
| `reload` | Re-read current profile file from disk |
| `help` | Print command reference |
| `quit` / `exit` | Stop the mapper |

- Tab-completion on `switch` reads `profiles/` at completion time — new files appear without restart.
- Input history is session-scoped (arrow keys); not persisted to disk.
- Invalid commands print an inline red error; no interruption to the live display.

---

## Display Layout

Rich `Layout` rendered above the prompt_toolkit input line via `patch_stdout`:

```
╭─ DS4 Mapper ──────────────────────────────────────╮
│ Profile: default  │  "Standard browser game layout" │
│ Controller: DualShock 4 Wireless Controller         │
╰─────────────────────────────────────────────────────╯
╭─ Active Buttons ────────╮  ╭─ Last Press ───────────╮
│                         │  │ Cross      →  x         │
│  [Cross]  [L1]          │  │ L1         →  q         │
│                         │  │ R-Stick ↑  →  i         │
╰─────────────────────────╯  ╰────────────────────────╯
> _
```

- **Top panel** — active profile name, description, connected controller name
- **Active Buttons** — buttons/axes currently held; clears on release
- **Last Press** — rolling log of last 5 inputs with mapped key; older entries rendered dim
- **Prompt** — owned by prompt_toolkit, sits below Rich panels

---

## Testing

`pytest`, no hardware required. pygame and pynput are stubbed at module level.

### `test_profiles.py`
- Valid TOML loads into correct `Profile` dataclass
- Unknown key name raises `ValueError`
- Missing `[buttons]` section raises `ValueError`
- `list_profiles()` returns names sorted alphabetically

### `test_keys.py`
- Single char `"x"` resolves to `"x"`
- Special name `"enter"` resolves to `pynput.Key.enter`
- Unknown name raises `ValueError`

### `test_mapper.py` (stubs pygame + pynput Controller)
- Button down fires `keyboard.press()` with mapped key
- Button up fires `keyboard.release()`
- Unmapped button index is ignored
- Profile switch mid-run applies new mappings to subsequent events
- Axis past deadzone triggers press; returning inside deadzone triggers release

CLI rendering and threading are verified manually by running the app.
