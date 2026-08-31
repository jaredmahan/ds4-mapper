import threading
import time
from collections import deque

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.columns import Columns
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from ds4mapper.mapper import MapperThread
from ds4mapper.profiles import Profile, list_profiles, load_profile

_RECENT_MAX = 5


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

    def on_event(label: str, key_repr: str, pressed: bool) -> None:
        with lock:
            if pressed:
                active.add(label)
                recent.appendleft(f"{label} → {key_repr}")
            else:
                active.discard(label)

    controller_name = joy.get_name() if hasattr(joy, "get_name") else "Unknown"

    mapper = MapperThread(get_profile, on_event)
    mapper.start()

    session: PromptSession = PromptSession(
        completer=_ProfileCompleter(),
        history=InMemoryHistory(),
    )

    def input_loop() -> None:
        with patch_stdout():
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
                    print(", ".join(list_profiles()) or "(none)")
                elif cmd == "switch":
                    if len(parts) < 2:
                        print("usage: switch <name>")
                    else:
                        name = parts[1]
                        try:
                            p = load_profile(name)
                            with lock:
                                _current[0] = p
                                _current[1] = name
                            print(f"Switched to: {p.name}")
                        except (
                            FileNotFoundError,
                            ValueError,
                            KeyError,
                            IndexError,
                            TypeError,
                        ) as exc:
                            print(f"Error: {exc}")
                elif cmd == "current":
                    with lock:
                        p = _current[0]
                    print(f"Profile: {p.name} — {p.description}")
                elif cmd == "reload":
                    with lock:
                        stem = _current[1]
                    try:
                        p = load_profile(stem)
                        with lock:
                            _current[0] = p
                        print(f"Reloaded: {p.name}")
                    except (
                        FileNotFoundError,
                        ValueError,
                        KeyError,
                        IndexError,
                        TypeError,
                    ) as exc:
                        print(f"Error: {exc}")
                elif cmd in ("help", "?"):
                    print("Commands: list  switch <name>  current  reload  help  quit")
                elif cmd in ("quit", "exit"):
                    _quit.set()
                    return
                else:
                    print(f"Unknown command: {cmd!r}  (type 'help')")

    input_thread = threading.Thread(target=input_loop, daemon=True)
    input_thread.start()

    try:
        with Live(refresh_per_second=30, screen=False) as live:
            while not _quit.is_set():
                with lock:
                    profile_snap = _current[0]
                    active_snap = set(active)
                    recent_snap = list(recent)
                live.update(_build_layout(profile_snap, controller_name, active_snap, recent_snap))
                time.sleep(1 / 30)
    finally:
        _quit.set()
        mapper.stop()
        mapper.join(timeout=2)
        mapper.release_all()
