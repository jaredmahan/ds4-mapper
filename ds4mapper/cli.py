import threading
from collections import deque

import pygame
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, RichLog, Static

from ds4mapper.mapper import MapperThread
from ds4mapper.profiles import Profile, list_profiles, load_profile

_RECENT_MAX = 5


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
        self.controller_name = joy.get_name() if hasattr(joy, "get_name") else "Unknown"

    def compose(self) -> ComposeResult:
        yield Static("", id="info")
        with Horizontal(id="panels"):
            yield Static("[bold]Active[/]\n[dim]—[/]", id="active-pane")
            yield Static("[bold]Last Press[/]\n[dim]—[/]", id="recent-pane")
        yield RichLog(id="log", markup=True, highlight=True)
        yield Input(placeholder="> ", id="cmd")

    def on_mount(self) -> None:
        self.query_one("#cmd", Input).focus()
        self._refresh_info()

        def on_event(label: str, key_repr: str, pressed: bool) -> None:
            with self._lock:
                if pressed:
                    self._active.add(label)
                    self._recent.appendleft(f"{label} → {key_repr}")
                else:
                    self._active.discard(label)
            self.call_from_thread(self._refresh_panels)

        self._mapper = MapperThread(self._get_profile, on_event)
        self._mapper.start()
        # macOS requires pygame.event.get() on the main thread (AppKit constraint).
        # Textual's set_interval callbacks run in the asyncio event loop on the main thread.
        self.set_interval(1 / 30, self._pump_pygame)

    def _pump_pygame(self) -> None:
        for event in pygame.event.get():
            if self._mapper:
                self._mapper.feed(event)

    def _get_profile(self) -> Profile:
        with self._lock:
            return self._current[0]

    def _refresh_info(self) -> None:
        with self._lock:
            p = self._current[0]
        desc = f"  [dim]—[/]  {p.description}" if p.description else ""
        self.query_one("#info", Static).update(
            f"[bold cyan]{p.name}[/]{desc}   [dim]│[/]   [dim]{self.controller_name}[/]"
        )

    def _refresh_panels(self) -> None:
        with self._lock:
            act = set(self._active)
            rec = list(self._recent)

        active_lines = "\n".join(f"[bold green]{a}[/]" for a in sorted(act)) if act else "[dim]—[/]"
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
        elif cmd in ("help", "?"):
            log.write(
                "Commands: [bold]list[/]  [bold]switch <name>[/]  "
                "[bold]status[/]  [bold]reload[/]  [bold]quit[/]"
            )
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
