import argparse
import os
import sys
import time

os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

import pygame
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ds4mapper.cli import run
from ds4mapper.profiles import load_profile

_console = Console()


def _init_pygame() -> pygame.joystick.Joystick:
    pygame.init()
    pygame.display.set_caption("DS4 Mapper")
    pygame.display.set_mode((220, 40))
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        timeout = 30
        deadline = time.monotonic() + timeout
        while pygame.joystick.get_count() == 0:
            remaining = int(deadline - time.monotonic())
            if remaining <= 0:
                print("\rNo controller found. Connect the DS4 via Bluetooth and try again.")
                sys.exit(1)
            print(
                f"\rNo controller detected. Waiting for DS4... {remaining}s  ", end="", flush=True
            )
            pygame.event.pump()
            time.sleep(1)
        print()  # newline after countdown

    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Connected: {joy.get_name()}")
    return joy


# Each line is a list of (style, text) segments; all render to exactly 61 chars.
# Layout: dpad(13) + gap(6) + touchpad(13) + gap(6) + face-buttons(13) = 51 inner chars.
_ART_LINES: list[list[tuple[str, str]]] = [
    [("dim", "          ╭──╮                                 ╭──╮          ")],
    [("dim", "  L2 ──────"), ("cyan", "┤  ├"), ("dim", "──── L1                   R1 ────"), ("cyan", "┤  ├"), ("dim", "──── R2  ")],
    [("cyan", "  ╭────────┴──┴─────────────────────────────────┴──┴──────╮  ")],
    [("cyan", "  │  "), ("white", "      ▲      "), ("cyan", "      "), ("dim", "╔═══════════╗"), ("cyan", "      "), ("yellow", "      △      "), ("cyan", "  │  ")],
    [("cyan", "  │  "), ("white", "   ◄  ╋  ►   "), ("cyan", "  "), ("dim", "SHR"), ("cyan", " "), ("dim", "║ TOUCHPAD  ║"), ("cyan", " "), ("dim", "OPT"), ("cyan", "  "), ("cyan", "   "), ("magenta", "□"), ("cyan", "     "), ("red", "○"), ("cyan", "   "), ("cyan", "  │  ")],
    [("cyan", "  │  "), ("white", "      ▼      "), ("cyan", "      "), ("dim", "╚═══════════╝"), ("cyan", "      "), ("blue", "      ✕      "), ("cyan", "  │  ")],
    [("cyan", "  │  "), ("cyan", "                                                   "), ("cyan", "  │  ")],
    [("cyan", "  │  "), ("dim", "       ╭───╮"), ("cyan", "             ⊛             "), ("dim", "╭───╮       "), ("cyan", "  │  ")],
    [("cyan", "  │  "), ("dim", "       │ L │"), ("cyan", "                           "), ("dim", "│ R │       "), ("cyan", "  │  ")],
    [("cyan", "  │  "), ("dim", "       ╰───╯"), ("cyan", "                           "), ("dim", "╰───╯       "), ("cyan", "  │  ")],
    [("cyan", "  ╰──╮                                                 ╭──╯  ")],
    [("cyan", "     ╰─────────────────────────────────────────────────╯     ")],
]


def _splash(controller_name: str, profile_name: str) -> None:
    body = Text(justify="center", no_wrap=True)
    body.append("◆ DS4 MAPPER\n", style="bold cyan")
    body.append("DualShock 4 → Keyboard\n\n", style="dim")
    for segments in _ART_LINES:
        for style, chunk in segments:
            body.append(chunk, style=style)
        body.append("\n")
    body.append("\n")
    body.append("Controller  ", style="dim")
    body.append(controller_name, style="cyan bold")
    body.append("   Profile  ", style="dim")
    body.append(profile_name, style="green bold")
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

    _console.print(Panel(Align.center(body), border_style="cyan", padding=(0, 2)))
    _console.print()


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
    parser.add_argument(
        "--discover", action="store_true", help="Print raw events to verify button/axis indices"
    )
    parser.add_argument(
        "--profile", default="default", help="Profile name to load on startup (default: default)"
    )
    args = parser.parse_args()

    joy = _init_pygame()
    try:
        if args.discover:
            _splash(joy.get_name(), "discover mode")
            _discover(joy)
        else:
            profile = load_profile(args.profile)
            _splash(joy.get_name(), profile.name)
            run(joy, profile, args.profile)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
