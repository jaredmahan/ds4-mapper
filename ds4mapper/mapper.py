import queue
import sys
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
        self._event_queue: queue.Queue = queue.Queue()
        self._axis_active: dict[tuple[int, int], bool] = {}
        self._trigger_active: dict[int, bool] = {}
        self._pressed_keys: dict[str, Key | str] = {}
        self._suspended = False

    @property
    def suspended(self) -> bool:
        return self._suspended

    @suspended.setter
    def suspended(self, value: bool) -> None:
        self._suspended = value

    def feed(self, event: object) -> None:
        """Called from the main thread to deliver a pygame event."""
        self._event_queue.put(event)

    def stop(self) -> None:
        self._stop_event.set()

    def release_all(self) -> None:
        """Release all currently pressed keys."""
        for key in list(self._pressed_keys.values()):
            try:
                self._keyboard.release(key)
            except Exception:
                pass
        self._pressed_keys.clear()

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self._event_queue.get(timeout=0.016)
            except queue.Empty:
                continue
            self._process_event(event)

    def _process_event(self, event: object) -> None:
        profile = self._get_profile()

        if event.type == pygame.JOYBUTTONDOWN:
            key = profile.buttons.get(event.button)
            if key is None:
                return
            if not self._suspended:
                try:
                    self._keyboard.press(key)
                except Exception as exc:  # noqa: BLE001
                    print(f"[mapper] press failed: {exc}", file=sys.stderr)
            self._pressed_keys[f"btn:{event.button}"] = key
            self._on_event(f"button:{event.button}", repr(key), True)

        elif event.type == pygame.JOYBUTTONUP:
            slot = f"btn:{event.button}"
            key = self._pressed_keys.pop(slot, None)
            if key is None:
                return
            if not self._suspended:
                try:
                    self._keyboard.release(key)
                except Exception as exc:  # noqa: BLE001
                    print(f"[mapper] release failed: {exc}", file=sys.stderr)
            self._on_event(f"button:{event.button}", repr(key), False)

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
                    if not self._suspended:
                        try:
                            self._keyboard.press(key)
                        except Exception as exc:  # noqa: BLE001
                            print(f"[mapper] press failed: {exc}", file=sys.stderr)
                    self._pressed_keys[f"trigger:{axis}"] = key
                    self._on_event(f"trigger:{axis}", repr(key), True)
                elif was and not now:
                    pressed_key = self._pressed_keys.pop(f"trigger:{axis}", key)
                    if not self._suspended:
                        try:
                            self._keyboard.release(pressed_key)
                        except Exception as exc:  # noqa: BLE001
                            print(f"[mapper] release failed: {exc}", file=sys.stderr)
                    self._on_event(f"trigger:{axis}", repr(pressed_key), False)
                self._trigger_active[axis] = now

        elif event.type == pygame.JOYHATMOTION:
            pass

    def _update_axis(self, axis: int, direction: int, is_active: bool, key: Key | str) -> None:
        key_id = (axis, direction)
        was = self._axis_active.get(key_id, False)
        label = f"axis:{axis}:{'+' if direction > 0 else '-'}"
        if is_active and not was:
            if not self._suspended:
                try:
                    self._keyboard.press(key)
                except Exception as exc:  # noqa: BLE001
                    print(f"[mapper] press failed: {exc}", file=sys.stderr)
            self._pressed_keys[f"axis:{axis}:{direction}"] = key
            self._on_event(label, repr(key), True)
        elif was and not is_active:
            pressed_key = self._pressed_keys.pop(f"axis:{axis}:{direction}", key)
            if not self._suspended:
                try:
                    self._keyboard.release(pressed_key)
                except Exception as exc:  # noqa: BLE001
                    print(f"[mapper] release failed: {exc}", file=sys.stderr)
            self._on_event(label, repr(pressed_key), False)
        self._axis_active[key_id] = is_active
