#!/opt/homebrew/bin/python3
"""
DS4 → Keyboard Mapper

Reads a DualShock 4 controller over Bluetooth and injects system-wide keypresses
so a browser game can be played with the controller.

Usage:
    python3 ds4_mapper.py            # Run the mapper
    python3 ds4_mapper.py --discover # Print raw events to verify button/axis indices

Requirements:
    pip install pygame-ce pynput
    System Settings → Privacy & Security → Accessibility → enable Terminal (or iTerm2)
"""

import argparse
import os
import sys
import time

os.environ['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS'] = '1'

import pygame
from pynput.keyboard import Controller, Key

DEADZONE = 0.4
TRIGGER_DEADZONE = -0.5

BUTTON_MAP = {
    0: 'x',        # Cross
    1: 'z',        # Circle
    2: 's',        # Square
    3: 'a',        # Triangle
    6: Key.enter,  # Options / START
    4: 'v',        # Share  / SELECT
    9: 'q',        # L1
    10: 'e',       # R1
    11: Key.up,    # D-pad up
    12: Key.down,  # D-pad down
    13: Key.left,  # D-pad left
    14: Key.right, # D-pad right
}

HAT_CHECKS = {
    Key.up:    lambda h: h[1] ==  1,
    Key.down:  lambda h: h[1] == -1,
    Key.left:  lambda h: h[0] == -1,
    Key.right: lambda h: h[0] ==  1,
}

AXIS_MAP = {
    0: ('f', 'h'),
    1: ('t', 'g'),
    2: ('j', 'l'),
    3: ('i', 'k'),
}

TRIGGER_MAP = {
    4: Key.tab,
    5: 'r',
}


def init_pygame():
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


def discover_mode(joy):
    print("\nDiscover mode — press every button and move every stick/trigger.")
    print("Ctrl-C to quit.\n")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.JOYBUTTONDOWN:
                key = BUTTON_MAP.get(event.button, '(unmapped)')
                print(f"  BUTTON DOWN  index={event.button}  key={key}")
            elif event.type == pygame.JOYBUTTONUP:
                key = BUTTON_MAP.get(event.button, '(unmapped)')
                print(f"  BUTTON UP    index={event.button}  key={key}")
            elif event.type == pygame.JOYHATMOTION:
                print(f"  HAT          value={event.value}")
            elif event.type == pygame.JOYAXISMOTION:
                neg_key = AXIS_MAP.get(event.axis, (None, None))[0]
                pos_key = AXIS_MAP.get(event.axis, (None, None))[1]
                trig_key = TRIGGER_MAP.get(event.axis)
                if trig_key:
                    label = f"key={trig_key}"
                elif neg_key:
                    label = f"neg={neg_key}  pos={pos_key}"
                else:
                    label = "(unmapped)"
                print(f"  AXIS         index={event.axis}  value={event.value:.3f}  {label}")
        time.sleep(0.016)


def run(joy):
    keyboard = Controller()
    axis_active    = {}
    trigger_active = {}
    prev_hat = (0, 0)

    print("\nMapper active — click your game/text field, then use the controller.")
    print("Ctrl-C to stop.\n")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            elif event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
                key = BUTTON_MAP.get(event.button)
                if key is not None:
                    if event.type == pygame.JOYBUTTONDOWN:
                        try:
                            keyboard.press(key)
                            print(f"pressed: {key}", flush=True)
                        except Exception as e:
                            print(f"press failed: {e}", flush=True)
                    else:
                        keyboard.release(key)

            elif event.type == pygame.JOYHATMOTION:
                new_hat = event.value
                for key, check in HAT_CHECKS.items():
                    was = check(prev_hat)
                    now = check(new_hat)
                    if now and not was:
                        keyboard.press(key)
                    elif was and not now:
                        keyboard.release(key)
                prev_hat = new_hat

            elif event.type == pygame.JOYAXISMOTION:
                axis, value = event.axis, event.value
                if axis in AXIS_MAP:
                    neg_key, pos_key = AXIS_MAP[axis]
                    _update_axis(keyboard, axis_active, axis, -1, value < -DEADZONE, neg_key)
                    _update_axis(keyboard, axis_active, axis, +1, value >  DEADZONE, pos_key)
                elif axis in TRIGGER_MAP:
                    key = TRIGGER_MAP[axis]
                    was = trigger_active.get(axis, False)
                    now = value > TRIGGER_DEADZONE
                    if now and not was:
                        keyboard.press(key)
                    elif was and not now:
                        keyboard.release(key)
                    trigger_active[axis] = now

        time.sleep(0.008)


def _update_axis(keyboard, state, axis, direction, is_active, key):
    key_id = (axis, direction)
    was = state.get(key_id, False)
    if is_active and not was:
        keyboard.press(key)
    elif was and not is_active:
        keyboard.release(key)
    state[key_id] = is_active


def main():
    parser = argparse.ArgumentParser(description="DS4 → Keyboard Mapper")
    parser.add_argument("--discover", action="store_true",
                        help="Print raw events to verify button/axis indices")
    args = parser.parse_args()

    joy = init_pygame()
    try:
        if args.discover:
            discover_mode(joy)
        else:
            run(joy)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
