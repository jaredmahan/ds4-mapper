from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import ds4mapper.mapper as mapper_module
from ds4mapper.profiles import Profile


@pytest.fixture(autouse=True)
def stub_pygame():
    fake_pygame = MagicMock()
    fake_pygame.JOYBUTTONDOWN = 1
    fake_pygame.JOYBUTTONUP = 2
    fake_pygame.JOYAXISMOTION = 3
    fake_pygame.JOYHATMOTION = 4
    with patch.dict("sys.modules", {"pygame": fake_pygame}):
        import importlib

        importlib.reload(mapper_module)
        yield fake_pygame


def _make_profile(**overrides):
    defaults = dict(
        name="test",
        description="",
        buttons={0: "x", 9: "q"},
        axes={0: ("f", "h"), 1: ("t", "g")},
        triggers={4: "tab"},
    )
    defaults.update(overrides)
    return Profile(**defaults)


def _btn_event(event_type, button, pygame_mock):
    e = SimpleNamespace(type=event_type, button=button)
    return e


def _axis_event(axis, value, pygame_mock):
    return SimpleNamespace(type=pygame_mock.JOYAXISMOTION, axis=axis, value=value)


def test_button_down_fires_press(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    on_event = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, on_event, keyboard)

    t._process_event(_btn_event(stub_pygame.JOYBUTTONDOWN, 0, stub_pygame))

    keyboard.press.assert_called_once_with("x")


def test_button_up_fires_release(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_btn_event(stub_pygame.JOYBUTTONDOWN, 0, stub_pygame))
    t._process_event(_btn_event(stub_pygame.JOYBUTTONUP, 0, stub_pygame))

    keyboard.press.assert_called_once_with("x")
    keyboard.release.assert_called_once_with("x")


def test_unmapped_button_ignored(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_btn_event(stub_pygame.JOYBUTTONDOWN, 99, stub_pygame))

    keyboard.press.assert_not_called()


def test_profile_swap_uses_new_profile(stub_pygame):
    profile_a = _make_profile(buttons={0: "x"})
    profile_b = _make_profile(buttons={0: "z"})
    current = [profile_a]
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: current[0], MagicMock(), keyboard)

    t._process_event(_btn_event(stub_pygame.JOYBUTTONDOWN, 0, stub_pygame))
    current[0] = profile_b
    t._process_event(_btn_event(stub_pygame.JOYBUTTONUP, 0, stub_pygame))

    keyboard.press.assert_called_once_with("x")
    keyboard.release.assert_called_once_with("x")


def test_axis_past_deadzone_fires_press(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_axis_event(0, 0.9, stub_pygame))  # positive past deadzone

    keyboard.press.assert_called_once_with("h")


def test_axis_returns_inside_deadzone_fires_release(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_axis_event(0, 0.9, stub_pygame))  # press
    t._process_event(_axis_event(0, 0.1, stub_pygame))  # release

    keyboard.press.assert_called_once_with("h")
    keyboard.release.assert_called_once_with("h")


def test_trigger_past_threshold_fires_press(stub_pygame):
    profile = _make_profile()
    keyboard = MagicMock()
    t = mapper_module.MapperThread(lambda: profile, MagicMock(), keyboard)

    t._process_event(_axis_event(4, 0.0, stub_pygame))  # past TRIGGER_DEADZONE (-0.5)

    keyboard.press.assert_called_once_with("tab")
