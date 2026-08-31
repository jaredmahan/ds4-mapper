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
    header_text.append("Profile: ", style="bold")
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
