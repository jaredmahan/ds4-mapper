import copy
import threading
from collections import deque

import pygame
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Input, RichLog, Static

from ds4mapper.keys import resolve
from ds4mapper.mapper import DEADZONE, TRIGGER_DEADZONE, MapperThread
from ds4mapper.profiles import PROFILES_DIR, Profile, list_profiles, load_profile, save_profile

# Each row is [(style, text), ...]; all must render to exactly 61 chars.
_ART_LINES: list[list[tuple[str, str]]] = [
    [("cyan", "    ╭──╮                                 ╭──╮         ")],
    [
        ("dim", "  L2 ──────"),
        ("cyan", "┤  ├"),
        ("dim", "──── L1                   R1 ────"),
        ("cyan", "┤  ├"),
        ("dim", "──── R2  "),
    ],
    [("cyan", "  ╭────────┴──┴─────────────────────────────────┴──┴──────╮  ")],
    [
        ("cyan", "  │  "),
        ("white", "      ↑      "),
        ("cyan", "      "),
        ("dim", "╔═══════════╗"),
        ("cyan", "      "),
        ("yellow", "      △      "),
        ("cyan", "  │  "),
    ],
    [
        ("cyan", "  │  "),
        ("white", "   ◄  +  ►   "),
        ("cyan", "  "),
        ("dim", "shr"),
        ("cyan", " "),
        ("dim", "║ TOUCHPAD  ║"),
        ("cyan", " "),
        ("dim", "opt"),
        ("cyan", "  "),
        ("cyan", "   "),
        ("magenta", "□"),
        ("cyan", "     "),
        ("red", "○"),
        ("cyan", "   "),
        ("cyan", "  │  "),
    ],
    [
        ("cyan", "  │  "),
        ("white", "      ↓      "),
        ("cyan", "      "),
        ("dim", "╚═══════════╝"),
        ("cyan", "      "),
        ("blue", "      ✕      "),
        ("cyan", "  │  "),
    ],
    [
        ("cyan", "  │  "),
        ("cyan", "                                                   "),
        ("cyan", "  │  "),
    ],
    [
        ("cyan", "  │  "),
        ("dim", "       ╭───╮"),
        ("cyan", "             ⊛             "),
        ("dim", "╭───╮       "),
        ("cyan", "  │  "),
    ],
    [
        ("cyan", "  │  "),
        ("dim", "       │ L │"),
        ("cyan", "                           "),
        ("dim", "│ R │       "),
        ("cyan", "  │  "),
    ],
    [
        ("cyan", "  │  "),
        ("dim", "       ╰───╯"),
        ("cyan", "                           "),
        ("dim", "╰───╯       "),
        ("cyan", "  │  "),
    ],
    [("cyan", "  ╰──╮                                                 ╭──╯  ")],
    [("cyan", "   ╰─────────────────────────────────────────────────╯     ")],
]


_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

_TRIGGER_AXES: frozenset[int] = frozenset({4, 5})

_TEXTUAL_SPECIAL: dict[str, str] = {
    "enter": "enter",
    "tab": "tab",
    "space": "space",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "escape": "esc",
    "shift": "shift",
    "ctrl": "ctrl",
    "alt": "alt",
}


def _textual_key_to_profile(event: events.Key) -> str | None:
    """Convert a Textual Key event to a profile key string, or None if not capturable."""
    if event.character and len(event.character) == 1 and event.character.isprintable():
        return event.character
    return _TEXTUAL_SPECIAL.get(event.key)


class SplashScreen(Screen[None]):
    DEFAULT_CSS = """
    SplashScreen {
        align: center middle;
    }
    SplashScreen #hint {
        margin-top: 1;
        text-align: center;
    }
    """

    _frame: int = 0

    def __init__(self, controller_name: str, profile_name: str) -> None:
        super().__init__()
        self._controller_name = controller_name
        self._profile_name = profile_name

    def _build_panel(self) -> Panel:
        body = Text(justify="center", no_wrap=True)
        body.append("◆ DS4 MAPPER\n", style="bold cyan")
        body.append("DualShock 4 → Keyboard\n\n", style="dim")
        for segments in _ART_LINES:
            for style, chunk in segments:
                body.append(chunk, style=style)
            body.append("\n")
        body.append("\n")
        body.append("Controller  ", style="dim")
        body.append(self._controller_name, style="cyan bold")
        body.append("   Profile  ", style="dim")
        body.append(self._profile_name, style="green bold")
        body.append("\n\n")
        body.append("list", style="bold white")
        body.append("  ·  ", style="dim")
        body.append("switch <name>", style="bold white")
        body.append("  ·  ", style="dim")
        body.append("current", style="bold white")
        body.append("  ·  ", style="dim")
        body.append("reload", style="bold white")
        body.append("  ·  ", style="dim")
        body.append("quit", style="bold white")
        return Panel(Align.center(body), border_style="cyan", padding=(0, 2))

    def compose(self) -> ComposeResult:
        yield Static(self._build_panel(), id="art")
        yield Static("", id="hint")

    def _tick_spinner(self) -> None:
        frame = _SPINNER_FRAMES[self._frame % len(_SPINNER_FRAMES)]
        self._frame += 1
        self.query_one("#hint", Static).update(f"[cyan]{frame}[/] [dim]Loading…[/]")

    def _do_dismiss(self) -> None:
        self.dismiss()

    def on_mount(self) -> None:
        self.set_timer(3.0, self._do_dismiss)
        self.set_interval(0.08, self._tick_spinner)


class EditScreen(Screen[None]):
    DEFAULT_CSS = """
    EditScreen { layout: vertical; }
    #edit-header {
        height: 3;
        border: solid cyan;
        padding: 0 1;
        content-align: left middle;
    }
    #edit-log { border: solid grey; }
    #edit-status {
        height: 3;
        border: solid yellow;
        padding: 0 1;
        content-align: left middle;
    }
    Input { dock: bottom; }
    """

    _IDLE = "idle"
    _WAITING = "waiting"

    def __init__(self, profile: Profile, stem: str) -> None:
        super().__init__()
        self._profile = copy.deepcopy(profile)
        self._stem = stem
        self._state = self._IDLE
        self._pending: str | None = None
        self._dirty = False

    def compose(self) -> ComposeResult:
        yield Static("", id="edit-header")
        yield RichLog(id="edit-log", markup=True, highlight=True)
        yield Static("", id="edit-status")
        yield Input(
            placeholder="save [name]  ·  delete <input>  ·  name <text>  ·  desc <text>  ·  cancel",
            id="edit-cmd",
        )

    def on_mount(self) -> None:
        self._refresh_header()
        self._refresh_log()
        self._refresh_status()
        self.query_one("#edit-cmd", Input).focus()

    def _refresh_header(self) -> None:
        marker = "  [yellow bold]*[/]" if self._dirty else ""
        desc = f"  [dim]{self._profile.description}[/]" if self._profile.description else ""
        self.query_one("#edit-header", Static).update(
            f"[dim]Editing:[/] [bold cyan]{self._profile.name}[/]{desc}{marker}"
            f"  [dim]│[/]  [dim]{self._stem}.toml[/]"
        )

    def _refresh_log(self) -> None:
        log = self.query_one("#edit-log", RichLog)
        log.clear()
        for line in _profile_lines(self._profile):
            log.write(line)
        if not (self._profile.buttons or self._profile.axes or self._profile.triggers):
            log.write("[dim](no mappings yet — press a DS4 button, stick, or trigger)[/]")

    def _refresh_status(self) -> None:
        status = self.query_one("#edit-status", Static)
        if self._state == self._IDLE:
            status.update("[dim]Press a DS4 button, stick, or trigger to assign a key.[/]")
        else:
            ds4_name = _event_label(self._pending)
            status.update(
                f"[bold cyan]{ds4_name}[/]  →  "
                f"[dim]press the keyboard key to assign[/]  [dim](Esc = cancel)[/]"
            )

    def receive_ds4(self, label: str) -> None:
        if self._state != self._IDLE:
            return
        self._pending = label
        self._state = self._WAITING
        self._refresh_status()
        self.query_one("#edit-cmd", Input).blur()

    def on_key(self, event: events.Key) -> None:
        if self._state != self._WAITING:
            return
        if event.key == "escape":
            self._state = self._IDLE
            self._pending = None
            self._refresh_status()
            self.query_one("#edit-cmd", Input).focus()
            event.stop()
            return
        key_str = _textual_key_to_profile(event)
        if key_str is None:
            return
        event.stop()
        try:
            self._apply_mapping(self._pending, key_str)
        except ValueError as exc:
            self.query_one("#edit-log", RichLog).write(f"[red]Cannot map:[/] {exc}")
        self._pending = None
        self._state = self._IDLE
        self._dirty = True
        self._refresh_header()
        self._refresh_log()
        self._refresh_status()
        self.query_one("#edit-cmd", Input).focus()

    def _apply_mapping(self, ds4_label: str, key_str: str) -> None:
        resolved = resolve(key_str)
        parts = ds4_label.split(":")
        kind, idx = parts[0], int(parts[1])
        if kind == "button":
            self._profile.buttons[idx] = resolved
        elif kind == "trigger":
            self._profile.triggers[idx] = resolved
        elif kind == "axis":
            direction = parts[2]
            if idx in self._profile.axes:
                neg, pos = self._profile.axes[idx]
                self._profile.axes[idx] = (resolved, pos) if direction == "-" else (neg, resolved)
            else:
                self._profile.axes[idx] = (resolved, "?") if direction == "-" else ("?", resolved)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value.strip()
        log = self.query_one("#edit-log", RichLog)
        event.input.clear()
        if not line:
            return
        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("cancel", "quit", "exit"):
            self.dismiss()
        elif cmd == "save":
            stem = parts[1] if len(parts) >= 2 else self._stem
            partial = [
                idx
                for idx, (neg, pos) in self._profile.axes.items()
                if "?" in (_key_label(neg), _key_label(pos))
            ]
            if partial:
                log.write(
                    f"[yellow]Note:[/] {len(partial)} axis mapping(s) only have one direction set"
                    " — assign both directions or they will be skipped on save."
                )
            try:
                save_profile(self._profile, stem)
            except Exception as exc:  # noqa: BLE001
                log.write(f"[red]Error:[/] {exc}")
                return
            self._stem = stem
            self._dirty = False
            self._refresh_header()
            log.write(f"[green]Saved[/] → [cyan]{stem}.toml[/]")
        elif cmd == "delete":
            if len(parts) < 2:
                log.write("[red]usage:[/] delete button:<n> · axis:<n> · trigger:<n>")
                return
            self._delete_mapping(parts[1], log)
        elif cmd == "name":
            if len(parts) < 2:
                log.write("[red]usage:[/] name <new-profile-name>")
                return
            self._profile.name = " ".join(parts[1:])
            self._dirty = True
            self._refresh_header()
        elif cmd == "desc":
            self._profile.description = " ".join(parts[1:]) if len(parts) >= 2 else ""
            self._dirty = True
            self._refresh_header()
        else:
            log.write(
                f"Unknown: [bold]{cmd!r}[/]  — "
                "[bold]save[/]  [bold]delete[/]  [bold]name[/]  [bold]desc[/]  [bold]cancel[/]"
            )

    def _delete_mapping(self, label: str, log: RichLog) -> None:
        parts = label.split(":")
        if len(parts) < 2:
            log.write(f"[red]Invalid:[/] {label!r} — use button:<n>, axis:<n>, trigger:<n>")
            return
        kind = parts[0]
        try:
            idx = int(parts[1])
        except ValueError:
            log.write(f"[red]Invalid index:[/] {parts[1]!r}")
            return
        removed = False
        if kind == "button":
            removed = self._profile.buttons.pop(idx, None) is not None
        elif kind == "trigger":
            removed = self._profile.triggers.pop(idx, None) is not None
        elif kind == "axis":
            removed = self._profile.axes.pop(idx, None) is not None
        else:
            log.write(f"[red]Unknown type:[/] {kind!r} — use button, axis, or trigger")
            return
        if removed:
            self._dirty = True
            self._refresh_header()
            self._refresh_log()
        else:
            log.write(f"[dim]Not mapped:[/] {kind} {idx}")


_RECENT_MAX = 5

_DS4_BUTTON_NAMES: dict[int, str] = {
    0: "Cross ✕",
    1: "Circle ○",
    2: "Square □",
    3: "Triangle △",
    4: "L1",
    5: "R1",
    6: "L2",
    7: "R2",
    8: "Share",
    9: "Options",
    10: "L3",
    11: "D-pad ↑",
    12: "D-pad ↓",
    13: "D-pad ←",
    14: "D-pad →",
}

_DS4_AXIS_NAMES: dict[int, str] = {
    0: "Left X",
    1: "Left Y",
    2: "Right X",
    3: "Right Y",
}

_DS4_TRIGGER_NAMES: dict[int, str] = {
    4: "L2",
    5: "R2",
}

_SEP_RICH = "  [dim]│[/]  "

_BUTTON_GROUPS: list[tuple[str, list[int]]] = [
    ("Face", [0, 1, 2, 3]),
    ("Shoulder", [4, 5, 6, 7]),
    ("D-pad", [11, 12, 13, 14]),
    ("Other", [8, 9, 10]),
]
_GROUPED_BUTTON_INDICES: set[int] = {i for _, idxs in _BUTTON_GROUPS for i in idxs}


def _key_label(k: object) -> str:
    return k if isinstance(k, str) else k.name  # type: ignore[union-attr]


def _event_label(raw: str) -> str:
    """Convert a raw mapper label (e.g. 'button:0') to a human-readable DS4 name."""
    parts = raw.split(":")
    kind = parts[0]
    if kind == "button" and len(parts) == 2:
        idx = int(parts[1])
        return _DS4_BUTTON_NAMES.get(idx, f"Button {idx}")
    if kind == "axis" and len(parts) == 3:
        idx = int(parts[1])
        hw = _DS4_AXIS_NAMES.get(idx, f"Axis {idx}")
        arrow = "→" if parts[2] == "+" else "←"
        return f"{hw} {arrow}"
    if kind == "trigger" and len(parts) == 2:
        idx = int(parts[1])
        return _DS4_TRIGGER_NAMES.get(idx, f"Trigger {idx}")
    return raw


def _into_columns(rich_cells: list[str], plain_cells: list[str], cols: int = 3) -> list[str]:
    """Pack (rich, plain) cell pairs into rows of `cols`, filling top-to-bottom per column."""
    if not rich_cells:
        return []
    n = len(rich_cells)
    num_rows = (n + cols - 1) // cols
    cell_w = max(len(p) for p in plain_cells)
    rows = []
    for r in range(num_rows):
        col_rich, col_plain = [], []
        for c in range(cols):
            idx = c * num_rows + r
            if idx < n:
                col_rich.append(rich_cells[idx])
                col_plain.append(plain_cells[idx])
        row = ""
        for j, (rich, plain) in enumerate(zip(col_rich, col_plain)):
            if j == len(col_rich) - 1:
                row += rich
            else:
                row += rich + " " * (cell_w - len(plain)) + _SEP_RICH
        rows.append(row)
    return rows


def _profile_lines(p: Profile) -> list[str]:
    header = f"[bold cyan]{p.name}[/]"
    if p.description:
        header += f"  [dim]{p.description}[/]"
    lines = [header, ""]

    if p.buttons:
        lines.append("[dim]Buttons[/]")
        # Sort by group order so column-major fill keeps each group in its own column.
        order = [idx for _, idxs in _BUTTON_GROUPS for idx in idxs if idx in p.buttons]
        order += sorted(i for i in p.buttons if i not in _GROUPED_BUTTON_INDICES)
        rich_cells, plain_cells = [], []
        for idx in order:
            hw = _DS4_BUTTON_NAMES.get(idx, f"Button {idx}")
            key = _key_label(p.buttons[idx])
            plain_cells.append(f"  {hw:<13}→  {key}")
            rich_cells.append(f"  [dim]{hw:<13}[/]→  [bold]{key}[/]")
        lines.extend(_into_columns(rich_cells, plain_cells))
        lines.append("")

    if p.axes:
        lines.append("[dim]Axes[/]")
        rich_cells, plain_cells = [], []
        for idx in sorted(p.axes):
            hw = _DS4_AXIS_NAMES.get(idx, f"Axis {idx}")
            neg, pos = _key_label(p.axes[idx][0]), _key_label(p.axes[idx][1])
            plain_cells.append(f"  {hw:<9}{neg} ←·→ {pos}")
            rich_cells.append(f"  [dim]{hw:<9}[/][bold]{neg}[/] [dim]←·→[/] [bold]{pos}[/]")
        lines.extend(_into_columns(rich_cells, plain_cells))
        lines.append("")

    if p.triggers:
        lines.append("[dim]Triggers[/]")
        rich_cells, plain_cells = [], []
        for idx in sorted(p.triggers):
            hw = _DS4_TRIGGER_NAMES.get(idx, f"Trigger {idx}")
            key = _key_label(p.triggers[idx])
            plain_cells.append(f"  {hw:<5}→  {key}")
            rich_cells.append(f"  [dim]{hw:<5}[/]→  [bold]{key}[/]")
        lines.extend(_into_columns(rich_cells, plain_cells))

    return lines


class MapperApp(App[None]):
    CSS = """
    Screen { layout: vertical; }

    #info {
        height: 3;
        border: solid cyan;
        padding: 0 1;
        content-align: left middle;
    }

    #panels {
        layout: horizontal;
        height: 9;
    }

    #active-pane {
        border: solid green;
        width: 1fr;
        padding: 0 1;
    }

    #recent-pane {
        border: solid yellow;
        width: 1fr;
        padding: 0 1;
    }

    #log {
        border: solid grey;
    }

    Input {
        dock: bottom;
    }
    """

    def __init__(
        self,
        joy: object,
        initial_profile: Profile,
        initial_stem: str = "default",
    ) -> None:
        super().__init__()
        self._current: list = [initial_profile, initial_stem]
        self._lock = threading.Lock()
        self._active: set[str] = set()
        self._recent: deque[str] = deque(maxlen=_RECENT_MAX)
        self._mapper: MapperThread | None = None
        self._edit_axis_state: dict[tuple[int, int], bool] = {}
        self.controller_name = joy.get_name() if hasattr(joy, "get_name") else "Unknown"

    def compose(self) -> ComposeResult:
        yield Static("", id="info")
        with Horizontal(id="panels"):
            yield Static("[bold]Active[/]\n[dim]—[/]", id="active-pane")
            yield Static("[bold]Last Press[/]\n[dim]—[/]", id="recent-pane")
        yield RichLog(id="log", markup=True, highlight=True)
        yield Input(placeholder="> ", id="cmd")

    def on_mount(self) -> None:
        self.push_screen(
            SplashScreen(self.controller_name, self._current[0].name),
            self._after_splash,
        )
        self._refresh_info()
        log = self.query_one("#log", RichLog)
        log.write("[bold cyan]Welcome to DS4-Mapper.[/]")
        log.write("The default profile is loaded. To change it, use [bold]switch <name>[/].")
        log.write("Below are a list of commands:")
        for line in [
            "[bold]list[/]             — print all available profile names",
            "[bold]switch [cyan]<name>[/][/]    — load and activate a different profile",
            "[bold]current[/]          — refresh the active-keys and recent-press panels",
            "[bold]reload[/]           — re-read the current profile file from disk",
            "[bold]view [cyan][<name>][/][/]     — show button/axis/trigger mappings for a profile",
            "[bold]edit [cyan][<name>][/][/]     — interactively edit a profile's key mappings",
            "[bold]new [cyan]<name>[/][/]      — create a new empty profile",
            "[bold]help[/]             — show this command reference",
            "[bold]quit[/]             — stop mapping and exit",
        ]:
            log.write(line)

        def on_event(label: str, key_repr: str, pressed: bool) -> None:
            display = _event_label(label)
            with self._lock:
                if pressed:
                    self._active.add(label)
                    self._recent.appendleft(f"{display} → {key_repr}")
                else:
                    self._active.discard(label)
            self.call_from_thread(self._refresh_panels)

        self._mapper = MapperThread(self._get_profile, on_event)
        self._mapper.start()
        # macOS requires pygame.event.get() on the main thread (AppKit constraint).
        # Textual's set_interval callbacks run in the asyncio event loop on the main thread.
        self.set_interval(1 / 30, self._pump_pygame)

    def _after_splash(self, _: None) -> None:
        self.query_one("#cmd", Input).focus()

    def _pump_pygame(self) -> None:
        for event in pygame.event.get():
            if self._mapper:
                self._mapper.feed(event)
            screen = self.screen
            if not isinstance(screen, EditScreen):
                continue
            if event.type == pygame.JOYBUTTONDOWN:
                screen.receive_ds4(f"button:{event.button}")
            elif event.type == pygame.JOYAXISMOTION:
                axis, value = event.axis, event.value
                if axis in _TRIGGER_AXES:
                    was = self._edit_axis_state.get((axis, 0), False)
                    now = value > TRIGGER_DEADZONE
                    if now and not was:
                        screen.receive_ds4(f"trigger:{axis}")
                    self._edit_axis_state[(axis, 0)] = now
                else:
                    for direction, sign in ((1, "+"), (-1, "-")):
                        was = self._edit_axis_state.get((axis, direction), False)
                        now = (value > DEADZONE) if direction > 0 else (value < -DEADZONE)
                        if now and not was:
                            screen.receive_ds4(f"axis:{axis}:{sign}")
                        self._edit_axis_state[(axis, direction)] = now

    def _get_profile(self) -> Profile:
        with self._lock:
            return self._current[0]

    def _refresh_info(self) -> None:
        with self._lock:
            p = self._current[0]
        desc = f" [dim]-[/] {p.description}" if p.description else ""
        self.query_one("#info", Static).update(
            f"[dim]Profile:[/] [bold cyan]{p.name}[/]{desc}"
            f"   [dim]│[/]   [dim]{self.controller_name}[/]"
        )

    def _refresh_panels(self) -> None:
        with self._lock:
            act = set(self._active)
            rec = list(self._recent)

        active_lines = (
            "\n".join(f"[bold green]{_event_label(a)}[/]" for a in sorted(act))
            if act
            else "[dim]—[/]"
        )
        recent_lines = "\n".join(rec) if rec else "[dim]—[/]"

        self.query_one("#active-pane", Static).update(f"[bold]Active[/]\n{active_lines}")
        self.query_one("#recent-pane", Static).update(f"[bold]Last Press[/]\n{recent_lines}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value.strip()
        log = self.query_one("#log", RichLog)
        event.input.clear()

        if not line:
            return

        parts = line.split()
        cmd = parts[0].lower()

        log.write("")
        log.write(f"[bold]> {line}[/]")

        if cmd == "list":
            names = list_profiles()
            log.write(", ".join(names) if names else "(none)")
        elif cmd == "switch":
            if len(parts) < 2:
                log.write("[red]usage:[/] switch [bold]<name>[/]")
            else:
                name = parts[1]
                try:
                    p = load_profile(name)
                    with self._lock:
                        self._current[0] = p
                        self._current[1] = name
                    log.write(f"Switched to [cyan bold]{p.name}[/]")
                    self._refresh_info()
                except (FileNotFoundError, ValueError, KeyError, IndexError, TypeError) as exc:
                    log.write(f"[red]Error:[/] {exc}")
        elif cmd == "view":
            if len(parts) >= 2:
                try:
                    p = load_profile(parts[1])
                except (FileNotFoundError, ValueError, KeyError, IndexError, TypeError) as exc:
                    log.write(f"[red]Error:[/] {exc}")
                    return
            else:
                with self._lock:
                    p = self._current[0]
            for entry in _profile_lines(p):
                log.write(entry)
        elif cmd in ("current", "status"):
            self._refresh_panels()
        elif cmd == "reload":
            with self._lock:
                stem = self._current[1]
            try:
                p = load_profile(stem)
                with self._lock:
                    self._current[0] = p
                log.write(f"Reloaded [cyan bold]{p.name}[/]")
                self._refresh_info()
            except (FileNotFoundError, ValueError, KeyError, IndexError, TypeError) as exc:
                log.write(f"[red]Error:[/] {exc}")
        elif cmd == "edit":
            stem = parts[1] if len(parts) >= 2 else self._current[1]
            try:
                p = load_profile(stem)
            except (FileNotFoundError, ValueError, KeyError, IndexError, TypeError) as exc:
                log.write(f"[red]Error:[/] {exc}")
                return
            if self._mapper:
                self._mapper.suspended = True

            def _after_edit(_: None) -> None:
                if self._mapper:
                    self._mapper.suspended = False
                self._refresh_info()

            self.push_screen(EditScreen(p, stem), _after_edit)
        elif cmd == "new":
            if len(parts) < 2:
                log.write("[red]usage:[/] new [bold]<stem>[/]")
                return
            stem = parts[1]
            if (PROFILES_DIR / f"{stem}.toml").exists():
                log.write(
                    f"[red]Error:[/] profile [cyan]{stem!r}[/] already exists"
                    " — use [bold]edit[/] to modify it"
                )
                return
            p = Profile(name=stem, description="", buttons={}, axes={}, triggers={})
            if self._mapper:
                self._mapper.suspended = True

            def _after_new(_: None) -> None:
                if self._mapper:
                    self._mapper.suspended = False

            self.push_screen(EditScreen(p, stem), _after_new)
        elif cmd in ("help", "?"):
            for entry in [
                "[bold]list[/]             — print all available profile names",
                "[bold]switch [cyan]<name>[/][/]    — load and activate a different profile",
                "[bold]current[/]          — refresh the active-keys and recent-press panels",
                "[bold]reload[/]           — re-read the current profile file from disk",
                "[bold]view [cyan][<name>][/][/]     — show mappings for a profile",
                "[bold]edit [cyan][<name>][/][/]     — interactively edit a profile's key mappings",
                "[bold]new [cyan]<name>[/][/]      — create a new empty profile",
                "[bold]help[/]             — show this command reference",
                "[bold]quit[/]             — stop mapping and exit",
            ]:
                log.write(entry)
        elif cmd in ("quit", "exit"):
            self.exit()
        else:
            log.write(f"Unknown: [bold]{cmd!r}[/]  — type [bold]help[/]")

    def on_unmount(self) -> None:
        if self._mapper:
            self._mapper.stop()
            self._mapper.join(timeout=2)
            self._mapper.release_all()


def run(joy: object, initial_profile: Profile, initial_stem: str = "default") -> None:
    MapperApp(joy, initial_profile, initial_stem).run()
