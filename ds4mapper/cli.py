import threading
import time
from collections import deque

import pygame
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from ds4mapper.mapper import MapperThread
from ds4mapper.profiles import Profile, list_profiles, load_profile

_RECENT_MAX = 5
_console = Console()


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


def _build_layout(
    profile: Profile,
    controller_name: str,
    active: set[str],
    recent: list[str],
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="body"),
    )

    header_text = Text()
    header_text.append("Profile: ", style="bold")
    header_text.append(profile.name, style="cyan bold")
    if profile.description:
        header_text.append(f"  —  {profile.description}", style="dim")
    header_text.append(f"\nController: {controller_name}", style="dim")
    layout["header"].update(Panel(header_text, title="DS4 Mapper"))

    active_text = Text(" ".join(f"[{a}]" for a in sorted(active)) or "—", style="green bold")
    active_panel = Panel(active_text, title="Active")

    recent_text = Text()
    for i, entry in enumerate(recent):
        style = "white" if i == 0 else "dim"
        recent_text.append(f"{entry}\n", style=style)
    recent_panel = Panel(recent_text or Text("—"), title="Last Press")

    layout["body"].update(Columns([active_panel, recent_panel]))
    return layout


def run(joy: object, initial_profile: Profile, initial_stem: str = "default") -> None:
    lock = threading.Lock()
    _current: list = [initial_profile, initial_stem]  # [Profile, stem]
    active: set[str] = set()
    recent: deque[str] = deque(maxlen=_RECENT_MAX)
    _quit = threading.Event()

    def get_profile() -> Profile:
        with lock:
            return _current[0]

    controller_name = joy.get_name() if hasattr(joy, "get_name") else "Unknown"

    def print_status() -> None:
        with lock:
            p = _current[0]
            act = set(active)
            rec = list(recent)
        _console.print(_build_layout(p, controller_name, act, rec))

    def on_event(label: str, key_repr: str, pressed: bool) -> None:
        with lock:
            if pressed:
                active.add(label)
                recent.appendleft(f"{label} → {key_repr}")
            else:
                active.discard(label)
        print_status()

    mapper = MapperThread(get_profile, on_event)
    mapper.start()

    session: PromptSession = PromptSession(
        completer=_ProfileCompleter(),
        history=InMemoryHistory(),
    )

    def input_loop() -> None:
        print_status()
        while not _quit.is_set():
            try:
                line = session.prompt("> ")
            except (EOFError, KeyboardInterrupt):
                _quit.set()
                return
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()
            if cmd == "list":
                _console.print(", ".join(list_profiles()) or "(none)")
            elif cmd == "switch":
                if len(parts) < 2:
                    _console.print("usage: switch <name>")
                else:
                    name = parts[1]
                    try:
                        p = load_profile(name)
                        with lock:
                            _current[0] = p
                            _current[1] = name
                        _console.print(f"Switched to: [cyan bold]{p.name}[/]")
                        print_status()
                    except (FileNotFoundError, ValueError, KeyError, IndexError, TypeError) as exc:
                        _console.print(f"[red]Error:[/] {exc}")
            elif cmd == "current":
                print_status()
            elif cmd == "reload":
                with lock:
                    stem = _current[1]
                try:
                    p = load_profile(stem)
                    with lock:
                        _current[0] = p
                    _console.print(f"Reloaded: [cyan bold]{p.name}[/]")
                    print_status()
                except (FileNotFoundError, ValueError, KeyError, IndexError, TypeError) as exc:
                    _console.print(f"[red]Error:[/] {exc}")
            elif cmd == "status":
                print_status()
            elif cmd in ("help", "?"):
                _console.print(
                    "Commands: [bold]list[/]  [bold]switch <name>[/]  "
                    "[bold]current[/]  [bold]status[/]  [bold]reload[/]  "
                    "[bold]help[/]  [bold]quit[/]"
                )
            elif cmd in ("quit", "exit"):
                _quit.set()
                return
            else:
                _console.print(f"Unknown command: [bold]{cmd!r}[/]  (type 'help')")

    input_thread = threading.Thread(target=input_loop, daemon=True)
    input_thread.start()

    try:
        # macOS requires pygame.event.get() on the main thread (AppKit constraint).
        while not _quit.is_set():
            for event in pygame.event.get():
                mapper.feed(event)
            time.sleep(1 / 30)
    finally:
        _quit.set()
        mapper.stop()
        mapper.join(timeout=2)
        mapper.release_all()
