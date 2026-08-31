import pytest
from pynput.keyboard import Key

from ds4mapper.keys import resolve


def test_single_char_resolves_to_itself():
    assert resolve("x") == "x"


def test_single_char_v_resolves_to_itself():
    assert resolve("v") == "v"


def test_enter_resolves_to_key():
    assert resolve("enter") == Key.enter


def test_tab_resolves_to_key():
    assert resolve("tab") == Key.tab


def test_up_resolves_to_key():
    assert resolve("up") == Key.up


def test_down_resolves_to_key():
    assert resolve("down") == Key.down


def test_left_resolves_to_key():
    assert resolve("left") == Key.left


def test_right_resolves_to_key():
    assert resolve("right") == Key.right


def test_space_resolves_to_key():
    assert resolve("space") == Key.space


def test_esc_resolves_to_key():
    assert resolve("esc") == Key.esc


def test_shift_resolves_to_key():
    assert resolve("shift") == Key.shift


def test_ctrl_resolves_to_key():
    assert resolve("ctrl") == Key.ctrl


def test_alt_resolves_to_key():
    assert resolve("alt") == Key.alt


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError, match="unknown key"):
        resolve("foo")


def test_empty_string_raises_value_error():
    with pytest.raises(ValueError, match="unknown key"):
        resolve("")
