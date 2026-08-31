# ds4-mapper — Claude Code Instructions

## Project Overview

Python 3.11+ CLI app that maps DualShock 4 controller input (via pygame) to keyboard/mouse output (via pynput). Entry point: `ds4mapper/__main__.py`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ds4-mapper [--profile NAME] [--discover]
```

## Key Files

| Path | Purpose |
|------|---------|
| `ds4mapper/__main__.py` | Entry point, splash screen, controller wait loop |
| `ds4mapper/cli.py` | Main run loop; Live display + prompt_toolkit session |
| `ds4mapper/mapper.py` | Button/axis → pynput key event dispatch |
| `ds4mapper/profiles.py` | TOML profile loader; `PROFILES_DIR = Path(__file__).parent / "profiles"` |
| `ds4mapper/profiles/default.toml` | Default profile (ships with the package) |
| `pyproject.toml` | Build config; `setuptools.build_meta` (NOT `setuptools.backends`) |
| `.github/workflows/ci.yml` | CI: xvfb-run for pynput on Linux, ruff excludes docs/ |

## Architecture Notes

- **Thread model:** `cli.py` runs `PromptSession.prompt()` on a daemon thread; main thread drives `rich.Live` at 30 fps. Never block the main thread with input.
- **Profile swap safety:** `_pressed_keys` dict stores the key that was pressed at press-time so release always uses the same key even after a profile switch. `_current = [Profile, stem]` list (mutable) allows atomic swap without a new variable.
- **Shutdown order:** `stop()` → `join()` → `release_all()`. Do not call `release_all()` before the mapper thread exits.
- **Profiles directory:** Lives inside the package (`ds4mapper/profiles/`) so it ships with both editable and non-editable installs. Declared as package-data in `pyproject.toml`.

## Splash Screen ASCII Art

`_ART_LINES` in `__main__.py` is a list of 11 `[(style, text), ...]` rows. **All rows must render to exactly 39 characters.** The border `│` must sit at columns 2 and 36 (0-indexed). Use `sum(len(t) for _, t in row)` to verify any edited row before committing.

Row structure for inner rows: `border(5) + left_widget(6) + gap(2) + center_widget(13) + gap(2) + right_widget(6) + border(5) = 39`.

## Dev Commands

```bash
ruff format . && ruff check .   # lint + format (ruff excludes docs/)
pytest tests/ -v                # tests (needs xvfb-run on headless Linux)
```

## CI Notes

- `ruff` config excludes `docs/` to avoid linting Python snippets in markdown plan files.
- GitHub Actions installs `xvfb` and runs `xvfb-run pytest tests/` so pynput gets an X display on Ubuntu.
- Build system: `setuptools.build_meta` — the `setuptools.backends.legacy:build` form causes install failures on macOS.

## Coding Conventions

- No inline comments unless the WHY is non-obvious.
- No inline style attributes (N/A here — no HTML/Lit templates, but keep Rich styling in `static` definitions).
- `pygame-ce`, `pynput`, `rich`, `prompt_toolkit` are the four runtime deps. Don't add new ones without discussion.
- Controller event polling uses `pygame.event.pump()` inside wait loops so SDL can detect newly connected devices.
