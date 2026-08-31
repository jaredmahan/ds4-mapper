# DS4 Mapper — Profiles & CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single `ds4_mapper.py` with a `ds4mapper` package that supports TOML profiles switchable at runtime via a Rich Live + prompt_toolkit terminal UI.

**Architecture:** A `MapperThread` runs the pygame event loop, reading from a shared `Profile` reference protected by a `threading.Lock`. The main thread runs a `prompt_toolkit` `PromptSession` with tab-completion; Rich renders a live display above the input line via `patch_stdout`.

**Tech Stack:** Python 3.11+, pygame-ce, pynput, rich, prompt_toolkit, tomli-w, pytest

**Spec:** `docs/superpowers/specs/2026-08-31-ds4-mapper-profiles-cli-design.md`

## Global Constraints

- Python >= 3.11 (use stdlib `tomllib` for reading TOML, `tomli-w` for writing)
- All work on a feature branch; merge to `main` via PR only — branch protection is enabled
- Three required CI checks must pass before merge: `lint` (ruff check), `build` (py_compile), `test` (pytest)
- Run `ruff format .` before every commit; line length 100, double quotes
- No inline style attributes; no print statements in library code (use the `on_event` callback)
- DEADZONE = 0.4, TRIGGER_DEADZONE = -0.5 (unchanged from original)
- Profile files live in `profiles/` at the repo root

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `ds4mapper/__init__.py` | Create | Package marker |
| `ds4mapper/__main__.py` | Create | Entry point (`python -m ds4mapper`) |
| `ds4mapper/keys.py` | Create | Resolve key name string → `pynput.Key` or `str` |
| `ds4mapper/profiles.py` | Create | `Profile` dataclass, load/validate TOML, list profiles |
| `ds4mapper/mapper.py` | Create | `MapperThread` — pygame event loop in a thread |
| `ds4mapper/cli.py` | Create | Rich Live display + prompt_toolkit command loop |
| `profiles/default.toml` | Create | Default profile mirroring original hardcoded mappings |
| `tests/__init__.py` | Create | Empty — makes tests a package |
| `tests/test_keys.py` | Create | Unit tests for key resolution |
| `tests/test_profiles.py` | Create | Unit tests for profile loading/listing |
| `tests/test_mapper.py` | Create | Unit tests for mapper event handling (pygame stubbed) |
| `pyproject.toml` | Modify | Add `[project.scripts]` entry |
| `ds4_mapper.py` | Delete | Replaced by the package |

---

## Task 1: Branch + Package Scaffolding

**Files:**
- Create: `ds4mapper/__init__.py`
- Create: `ds4mapper/__main__.py`
- Create: `tests/__init__.py`
- Create: `profiles/default.toml`
- Modify: `pyproject.toml`
- Delete: `ds4_mapper.py`

**Interfaces:**
- Produces: `python -m ds4mapper` entry point (stub that prints "not yet implemented")

- [ ] **Step 1: Create feature branch**

```bash
git checkout -b feat/profile-system
```

- [ ] **Step 2: Create package files**

`ds4mapper/__init__.py` — empty file.

`ds4mapper/__main__.py`:
```python
def main() -> None:
    print("not yet implemented")


if __name__ == "__main__":
    main()
```

`tests/__init__.py` — empty file.

- [ ] **Step 3: Create `profiles/default.toml`**

```toml
name = "default"
description = "Standard browser game layout"

[buttons]
0  = "x"
1  = "z"
2  = "s"
3  = "a"
4  = "v"
6  = "enter"
9  = "q"
10 = "e"
11 = "up"
12 = "down"
13 = "left"
14 = "right"

[axes]
0 = ["f", "h"]
1 = ["t", "g"]
2 = ["j", "l"]
3 = ["i", "k"]

[triggers]
4 = "tab"
5 = "r"
```

- [ ] **Step 4: Add entry point to `pyproject.toml`**

Add this section at the end of the existing `pyproject.toml`:
```toml
[project.scripts]
ds4-mapper = "ds4mapper.__main__:main"
```

- [ ] **Step 5: Delete old entry point**

```bash
git rm ds4_mapper.py
```

- [ ] **Step 6: Format and verify build**

```bash
ruff format .
python -m py_compile ds4mapper/__init__.py ds4mapper/__main__.py
```

- [ ] **Step 7: Commit**

```bash
git add ds4mapper/ tests/__init__.py profiles/ pyproject.toml
git commit -m "feat: scaffold ds4mapper package, add default profile"
```

---

## Task 2: `keys.py` + `test_keys.py`

**Files:**
- Create: `ds4mapper/keys.py`
- Create: `tests/test_keys.py`

**Interfaces:**
- Produces: `resolve(name: str) -> Key | str` — raises `ValueError` for unknown names

- [ ] **Step 1: Write failing tests**

`tests/test_keys.py`:
```python
import pytest
from pynput.keyboard import Key

from ds4mapper.keys import resolve


def test_single_char_resolves_to_itself():
    assert resolve("x") == "x"


def test_single_char_v_resolves_to_itself():
    assert resolve("v") == "v"


def test_enter_resolves_to_key():
    assert resolve("enter") == Key.enter


def test_tab_resolves_to_key():
    assert resolve("tab") == Key.tab


def test_up_resolves_to_key():
    assert resolve("up") == Key.up


def test_down_resolves_to_key():
    assert resolve("down") == Key.down


def test_left_resolves_to_key():
    assert resolve("left") == Key.left


def test_right_resolves_to_key():
    assert resolve("right") == Key.right


def test_space_resolves_to_key():
    assert resolve("space") == Key.space


def test_esc_resolves_to_key():
    assert resolve("esc") == Key.esc


def test_shift_resolves_to_key():
    assert resolve("shift") == Key.shift


def test_ctrl_resolves_to_key():
    assert resolve("ctrl") == Key.ctrl


def test_alt_resolves_to_key():
    assert resolve("alt") == Key.alt


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError, match="unknown key"):
        resolve("foo")


def test_empty_string_raises_value_error():
    with pytest.raises(ValueError, match="unknown key"):
        resolve("")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_keys.py -v
```
Expected: `ModuleNotFoundError` or `ImportError` — `keys.py` doesn't exist yet.

- [ ] **Step 3: Implement `ds4mapper/keys.py`**

```python
from pynput.keyboard import Key

_SPECIAL: dict[str, Key] = {
    "enter": Key.enter,
    "tab": Key.tab,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "space": Key.space,
    "esc": Key.esc,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "alt": Key.alt,
}


def resolve(name: str) -> Key | str:
    if name in _SPECIAL:
        return _SPECIAL[name]
    if len(name) == 1:
        return name
    raise ValueError(f"unknown key: {name!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_keys.py -v
```
Expected: all 15 tests PASS.

- [ ] **Step 5: Format and commit**

```bash
ruff format .
git add ds4mapper/keys.py tests/test_keys.py
git commit -m "feat: add key name resolver"
```

---

## Task 3: `profiles.py` + `test_profiles.py`

**Files:**
- Create: `ds4mapper/profiles.py`
- Create: `tests/test_profiles.py`

**Interfaces:**
- Consumes: `resolve(name)` from `ds4mapper.keys`
- Produces:
  - `Profile` dataclass with fields: `name: str`, `description: str`, `buttons: dict[int, Key | str]`, `axes: dict[int, tuple[Key | str, Key | str]]`, `triggers: dict[int, Key | str]`
  - `load_profile(name: str) -> Profile` — reads `profiles/<name>.toml`, validates, resolves keys
  - `list_profiles() -> list[str]` — sorted profile names from `profiles/` dir

- [ ] **Step 1: Write failing tests**

`tests/test_profiles.py`:
```python
import textwrap
from pathlib import Path

import pytest
from pynput.keyboard import Key

from ds4mapper.profiles import Profile, list_profiles, load_profile


def _write_toml(tmp_path: Path, content: str) -> Path:
    d = tmp_path / "profiles"
    d.mkdir()
    (d / "test.toml").write_text(textwrap.dedent(content))
    return d


def test_load_valid_profile(tmp_path, monkeypatch):
    profiles_dir = _write_toml(
        tmp_path,
        """
        name = "test"
        description = "A test profile"

        [buttons]
        0 = "x"
        6 = "enter"

        [axes]
        0 = ["f", "h"]

        [triggers]
        4 = "tab"
        """,
    )
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", profiles_dir)

    profile = load_profile("test")

    assert isinstance(profile, Profile)
    assert profile.name == "test"
    assert profile.description == "A test profile"
    assert profile.buttons[0] == "x"
    assert profile.buttons[6] == Key.enter
    assert profile.axes[0] == ("f", "h")
    assert profile.triggers[4] == Key.tab


def test_load_profile_unknown_key_raises(tmp_path, monkeypatch):
    profiles_dir = _write_toml(
        tmp_path,
        """
        name = "bad"
        description = "Bad profile"

        [buttons]
        0 = "notakey"

        [axes]

        [triggers]
        """,
    )
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", profiles_dir)

    with pytest.raises(ValueError, match="unknown key"):
        load_profile("bad")


def test_load_profile_missing_buttons_section_raises(tmp_path, monkeypatch):
    profiles_dir = _write_toml(
        tmp_path,
        """
        name = "bad"
        description = "Missing section"

        [axes]
        [triggers]
        """,
    )
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", profiles_dir)

    with pytest.raises(ValueError, match="missing.*buttons"):
        load_profile("bad")


def test_load_profile_not_found_raises(tmp_path, monkeypatch):
    d = tmp_path / "profiles"
    d.mkdir()
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", d)

    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent")


def test_list_profiles_returns_sorted_names(tmp_path, monkeypatch):
    d = tmp_path / "profiles"
    d.mkdir()
    for name in ("zebra", "alpha", "middle"):
        (d / f"{name}.toml").write_text("")
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", d)

    assert list_profiles() == ["alpha", "middle", "zebra"]


def test_list_profiles_ignores_non_toml_files(tmp_path, monkeypatch):
    d = tmp_path / "profiles"
    d.mkdir()
    (d / "valid.toml").write_text("")
    (d / "ignored.txt").write_text("")
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", d)

    assert list_profiles() == ["valid"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_profiles.py -v
```
Expected: `ImportError` — `profiles.py` doesn't exist yet.

- [ ] **Step 3: Implement `ds4mapper/profiles.py`**

```python
import tomllib
from dataclasses import dataclass
from pathlib import Path

from pynput.keyboard import Key

from ds4mapper.keys import resolve

PROFILES_DIR = Path(__file__).parent.parent / "profiles"


@dataclass
class Profile:
    name: str
    description: str
    buttons: dict[int, Key | str]
    axes: dict[int, tuple[Key | str, Key | str]]
    triggers: dict[int, Key | str]


def load_profile(name: str) -> Profile:
    path = PROFILES_DIR / f"{name}.toml"
    if not path.exists():
        raise FileNotFoundError(f"profile not found: {name!r}")

    with path.open("rb") as f:
        data = tomllib.load(f)

    if "buttons" not in data:
        raise ValueError("profile missing required section: buttons")
    if "axes" not in data:
        raise ValueError("profile missing required section: axes")
    if "triggers" not in data:
        raise ValueError("profile missing required section: triggers")

    buttons = {int(k): resolve(v) for k, v in data["buttons"].items()}
    axes = {
        int(k): (resolve(v[0]), resolve(v[1]))
        for k, v in data["axes"].items()
    }
    triggers = {int(k): resolve(v) for k, v in data["triggers"].items()}

    return Profile(
        name=data.get("name", name),
        description=data.get("description", ""),
        buttons=buttons,
        axes=axes,
        triggers=triggers,
    )


def list_profiles() -> list[str]:
    return sorted(p.stem for p in PROFILES_DIR.glob("*.toml"))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_profiles.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Format and commit**

```bash
ruff format .
git add ds4mapper/profiles.py tests/test_profiles.py
git commit -m "feat: add Profile dataclass and TOML loader"
```

---

## Task 4: `mapper.py` + `test_mapper.py`

**Files:**
- Create: `ds4mapper/mapper.py`
- Create: `tests/test_mapper.py`

**Interfaces:**
- Consumes: `Profile` from `ds4mapper.profiles`
- Produces: `MapperThread(get_profile, on_event, keyboard)` — `threading.Thread` subclass
  - `get_profile: Callable[[], Profile]` — called each event loop iteration (allows live swap)
  - `on_event: Callable[[str, str, bool], None]` — called with `(label, key_repr, pressed)` on press and release
  - `keyboard` — injected `pynput.keyboard.Controller` (injectable for testing)
  - `stop() -> None` — signals thread to exit
  - `_process_event(event) -> None` — processes a single pygame event (testable without threading)

- [ ] **Step 1: Write failing tests**

`tests/test_mapper.py`:
```python
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

import ds4mapper.mapper as mapper_module
from ds4mapper.profiles import Profile


@pytest.fixture(autouse=True)
def stub_pygame():
    fake_pygame = MagicMock()
    fake_pygame.JOYBUTTONDOWN = 1
    fake_pygame.JOYBUTTONUP = 2
    fake_pygame.JOYAXISMOTION = 3
    fake_pygame.JOYHATMOTION = 4
    with patch.dict("sys.modules", {"pygame": fake_pygame}):
        import importlib
        importlib.reload(mapper_module)
        yield fake_pygame


def _make_profile(**overrides):
    defaults = dict(
        name="test",
        description="",
        buttons={0: "x", 9: "q"},
        axes={0: ("f", "h"), 1: ("t", "g")},
        triggers={4: "tab"},
    )
    defaults.update(overrides)
    return Profile(**defaults)


def _btn_event(event_type, button, pygame_mock):
    e = SimpleNamespace(type=event_type, button=button)
    return e


def _axis_event(axis, value, pygame_mock):
    return SimpleNamespace(type=pygame_mock.JOYAXISMOTION, axis=axis, value=value)


def test_button_down_fires_press(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    on_event = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, on_event, keyboard)

    t._process_event(_btn_event(stub_pygame.JOYBUTTONDOWN, 0, stub_pygame))

    keyboard.press.assert_called_once_with("x")


def test_button_up_fires_release(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_btn_event(stub_pygame.JOYBUTTONUP, 0, stub_pygame))

    keyboard.release.assert_called_once_with("x")


def test_unmapped_button_ignored(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_btn_event(stub_pygame.JOYBUTTONDOWN, 99, stub_pygame))

    keyboard.press.assert_not_called()


def test_profile_swap_uses_new_profile(stub_pygame):
    profile_a = _make_profile(buttons={0: "x"})
    profile_b = _make_profile(buttons={0: "z"})
    current = [profile_a]
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: current[0], MagicMock(), keyboard)

    t._process_event(_btn_event(stub_pygame.JOYBUTTONDOWN, 0, stub_pygame))
    current[0] = profile_b
    t._process_event(_btn_event(stub_pygame.JOYBUTTONDOWN, 0, stub_pygame))

    assert keyboard.press.call_args_list == [call("x"), call("z")]


def test_axis_past_deadzone_fires_press(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_axis_event(0, 0.9, stub_pygame))  # positive past deadzone

    keyboard.press.assert_called_once_with("h")


def test_axis_returns_inside_deadzone_fires_release(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_axis_event(0, 0.9, stub_pygame))   # press
    t._process_event(_axis_event(0, 0.1, stub_pygame))   # release

    keyboard.press.assert_called_once_with("h")
    keyboard.release.assert_called_once_with("h")


def test_trigger_past_threshold_fires_press(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_axis_event(4, 0.0, stub_pygame))  # past TRIGGER_DEADZONE (-0.5)

    keyboard.press.assert_called_once_with("tab")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_mapper.py -v
```
Expected: `ImportError` — `mapper.py` doesn't exist yet.

- [ ] **Step 3: Implement `ds4mapper/mapper.py`**

```python
import threading
from collections.abc import Callable

import pygame
from pynput.keyboard import Controller, Key

from ds4mapper.profiles import Profile

DEADZONE = 0.4
TRIGGER_DEADZONE = -0.5


class MapperThread(threading.Thread):
    def __init__(
        self,
        get_profile: Callable[[], Profile],
        on_event: Callable[[str, str, bool], None],
        keyboard: Controller | None = None,
    ) -> None:
        super().__init__(daemon=True)
        self._get_profile = get_profile
        self._on_event = on_event
        self._keyboard = keyboard or Controller()
        self._stop_event = threading.Event()
        self._axis_active: dict[tuple[int, int], bool] = {}
        self._trigger_active: dict[int, bool] = {}

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            for event in pygame.event.get():
                self._process_event(event)

    def _process_event(self, event: object) -> None:
        profile = self._get_profile()

        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
            key = profile.buttons.get(event.button)
            if key is None:
                return
            pressed = event.type == pygame.JOYBUTTONDOWN
            if pressed:
                self._keyboard.press(key)
            else:
                self._keyboard.release(key)
            self._on_event(f"button:{event.button}", repr(key), pressed)

        elif event.type == pygame.JOYAXISMOTION:
            axis, value = event.axis, event.value
            if axis in profile.axes:
                neg_key, pos_key = profile.axes[axis]
                self._update_axis(axis, -1, value < -DEADZONE, neg_key)
                self._update_axis(axis, +1, value > DEADZONE, pos_key)
            elif axis in profile.triggers:
                key = profile.triggers[axis]
                was = self._trigger_active.get(axis, False)
                now = value > TRIGGER_DEADZONE
                if now and not was:
                    self._keyboard.press(key)
                    self._on_event(f"trigger:{axis}", repr(key), True)
                elif was and not now:
                    self._keyboard.release(key)
                    self._on_event(f"trigger:{axis}", repr(key), False)
                self._trigger_active[axis] = now

    def _update_axis(self, axis: int, direction: int, is_active: bool, key: Key | str) -> None:
        key_id = (axis, direction)
        was = self._axis_active.get(key_id, False)
        label = f"axis:{axis}:{'+' if direction > 0 else '-'}"
        if is_active and not was:
            self._keyboard.press(key)
            self._on_event(label, repr(key), True)
        elif was and not is_active:
            self._keyboard.release(key)
            self._on_event(label, repr(key), False)
        self._axis_active[key_id] = is_active
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_mapper.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 6: Format and commit**

```bash
ruff format .
git add ds4mapper/mapper.py tests/test_mapper.py
git commit -m "feat: add MapperThread with pygame event loop"
```

---

## Task 5: `cli.py`

**Files:**
- Create: `ds4mapper/cli.py`

**Interfaces:**
- Consumes: `Profile`, `load_profile`, `list_profiles` from `ds4mapper.profiles`; `MapperThread` from `ds4mapper.mapper`
- Produces: `run(joy: pygame.joystick.Joystick, initial_profile: Profile) -> None`

No automated tests — verified manually by running the app.

- [ ] **Step 1: Implement `ds4mapper/cli.py`**

```python
import threading
from collections import deque

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.patch_stdout import patch_stdout
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from ds4mapper.mapper import MapperThread
from ds4mapper.profiles import Profile, list_profiles, load_profile

console = Console()
_RECENT_MAX = 5


def _build_layout(
    profile: Profile,
    controller_name: str,
    active: set[str],
    recent: deque[tuple[str, str]],
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="body"),
    )

    header_text = Text()
    header_text.append(f"Profile: ", style="bold")
    header_text.append(profile.name, style="cyan bold")
    if profile.description:
        header_text.append(f"  —  {profile.description}", style="dim")
    header_text.append(f"\nController: {controller_name}", style="dim")
    layout["header"].update(Panel(header_text, title="DS4 Mapper"))

    active_text = Text(" ".join(f"[{a}]" for a in sorted(active)) or "—", style="green bold")
    active_panel = Panel(active_text, title="Active")

    recent_text = Text()
    for i, (label, key) in enumerate(reversed(recent)):
        style = "white" if i == 0 else "dim"
        recent_text.append(f"{label:<14} → {key}\n", style=style)
    recent_panel = Panel(recent_text or Text("—"), title="Last Press")

    layout["body"].update(Columns([active_panel, recent_panel]))
    return layout


def run(joy: object, initial_profile: Profile) -> None:
    lock = threading.Lock()
    _current: list[Profile] = [initial_profile]
    active: set[str] = set()
    recent: deque[tuple[str, str]] = deque(maxlen=_RECENT_MAX)

    def get_profile() -> Profile:
        with lock:
            return _current[0]

    def on_event(label: str, key_repr: str, pressed: bool) -> None:
        if pressed:
            active.add(label)
            recent.appendleft((label, key_repr))
        else:
            active.discard(label)

    controller_name = joy.get_name() if hasattr(joy, "get_name") else "Unknown"

    mapper = MapperThread(get_profile, on_event)
    mapper.start()

    class _ProfileCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            parts = text.split()
            if not parts or (len(parts) == 1 and not text.endswith(" ")):
                prefix = parts[0] if parts else ""
                for cmd in ("switch", "list", "current", "reload", "help", "quit", "exit"):
                    if cmd.startswith(prefix):
                        yield Completion(cmd, start_position=-len(prefix))
            elif parts[0] == "switch":
                prefix = parts[1] if len(parts) > 1 and not text.endswith(" ") else ""
                for name in list_profiles():
                    if name.startswith(prefix):
                        yield Completion(name, start_position=-len(prefix))

    session: PromptSession = PromptSession(completer=_ProfileCompleter())

    with patch_stdout():
        with Live(
            _build_layout(_current[0], controller_name, active, recent),
            console=console,
            refresh_per_second=30,
        ) as live:
            while True:
                live.update(_build_layout(_current[0], controller_name, active, recent))

                try:
                    raw = session.prompt("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if not raw:
                    continue

                parts = raw.split()
                cmd = parts[0].lower()

                if cmd in ("quit", "exit"):
                    break
                elif cmd == "help":
                    console.print(
                        "[bold]Commands:[/] list  switch <name>  current  reload  help  quit"
                    )
                elif cmd == "list":
                    names = list_profiles()
                    console.print("  ".join(names) if names else "(none)")
                elif cmd == "current":
                    p = get_profile()
                    console.print(f"[cyan]{p.name}[/]  {p.description}")
                elif cmd == "reload":
                    p = get_profile()
                    try:
                        new = load_profile(p.name)
                        with lock:
                            _current[0] = new
                        console.print(f"[green]reloaded[/] {p.name}")
                    except Exception as exc:
                        console.print(f"[red]error:[/] {exc}")
                elif cmd == "switch":
                    if len(parts) < 2:
                        console.print("[red]usage:[/] switch <name>")
                    else:
                        name = parts[1]
                        try:
                            new = load_profile(name)
                            with lock:
                                _current[0] = new
                            console.print(f"[green]switched to[/] {name}")
                        except FileNotFoundError:
                            console.print(f"[red]profile not found:[/] {name}")
                        except ValueError as exc:
                            console.print(f"[red]invalid profile:[/] {exc}")
                else:
                    console.print(f"[red]unknown command:[/] {cmd!r}  — type [bold]help[/]")

    mapper.stop()
    mapper.join(timeout=2)
```

- [ ] **Step 2: Format and commit**

```bash
ruff format .
ruff check .
git add ds4mapper/cli.py
git commit -m "feat: add Rich Live + prompt_toolkit CLI"
```

---

## Task 6: `__main__.py` + Cleanup + PR

**Files:**
- Modify: `ds4mapper/__main__.py`

**Interfaces:**
- Consumes: `run` from `ds4mapper.cli`; `load_profile` from `ds4mapper.profiles`
- Produces: working `python -m ds4mapper` and `python -m ds4mapper --discover` commands

- [ ] **Step 1: Implement `ds4mapper/__main__.py`**

```python
import argparse
import os
import sys
import time

os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

import pygame

from ds4mapper.cli import run
from ds4mapper.profiles import load_profile


def _init_pygame() -> pygame.joystick.Joystick:
    pygame.init()
    pygame.display.set_caption("DS4 Mapper")
    pygame.display.set_mode((220, 40))
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No controller detected. Connect the DS4 via Bluetooth and try again.")
        sys.exit(1)

    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Connected: {joy.get_name()}")
    return joy


def _discover(joy: pygame.joystick.Joystick) -> None:
    print("\nDiscover mode — press every button and move every stick/trigger.")
    print("Ctrl-C to quit.\n")
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.JOYBUTTONDOWN:
                print(f"  BUTTON DOWN  index={event.button}")
            elif event.type == pygame.JOYBUTTONUP:
                print(f"  BUTTON UP    index={event.button}")
            elif event.type == pygame.JOYHATMOTION:
                print(f"  HAT          value={event.value}")
            elif event.type == pygame.JOYAXISMOTION:
                print(f"  AXIS         index={event.axis}  value={event.value:.3f}")
        time.sleep(0.016)


def main() -> None:
    parser = argparse.ArgumentParser(description="DS4 → Keyboard Mapper")
    parser.add_argument("--discover", action="store_true",
                        help="Print raw events to verify button/axis indices")
    parser.add_argument("--profile", default="default",
                        help="Profile name to load on startup (default: default)")
    args = parser.parse_args()

    joy = _init_pygame()
    try:
        if args.discover:
            _discover(joy)
        else:
            profile = load_profile(args.profile)
            run(joy, profile)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 3: Format and lint**

```bash
ruff format .
ruff check .
```
Expected: no errors.

- [ ] **Step 4: Syntax check all files**

```bash
python -m py_compile ds4mapper/__init__.py ds4mapper/__main__.py ds4mapper/keys.py ds4mapper/profiles.py ds4mapper/mapper.py ds4mapper/cli.py
```
Expected: no output (clean).

- [ ] **Step 5: Commit and push branch**

```bash
ruff format .
git add ds4mapper/__main__.py
git commit -m "feat: wire up entry point with --profile flag"
git push -u origin feat/profile-system
```

- [ ] **Step 6: Open PR**

```bash
gh pr create --title "feat: profiles + Rich/prompt_toolkit CLI" --body "$(cat <<'EOF'
## Summary

- Replaces `ds4_mapper.py` with `ds4mapper` package
- TOML-based profiles in `profiles/` — switch at runtime without restart
- `switch <name>`, `list`, `reload`, `current`, `help`, `quit` commands
- Rich Live display with active buttons and recent presses
- prompt_toolkit input with tab-completion on profile names
- Full unit test coverage for key resolution, profile loading, and mapper event handling

## Test plan
- [ ] `pytest tests/ -v` — all tests pass
- [ ] `ruff format --check . && ruff check .` — clean
- [ ] `python -m ds4mapper` — mapper starts, Rich display renders, commands work
- [ ] `python -m ds4mapper --discover` — prints raw events
- [ ] `switch default` tab-completes and loads profile
EOF
)"
```
