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
