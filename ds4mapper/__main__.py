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
            _discover(joy)
        else:
            profile = load_profile(args.profile)
            run(joy, profile, args.profile)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
