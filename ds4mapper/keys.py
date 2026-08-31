from pynput.keyboard import Key

_SPECIAL: dict[str, Key] = {
    "enter": Key.enter,
    "tab": Key.tab,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "space": Key.space,
    "esc": Key.esc,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "alt": Key.alt,
}


def resolve(name: str) -> Key | str:
    if name in _SPECIAL:
        return _SPECIAL[name]
    if len(name) == 1:
        return name
    raise ValueError(f"unknown key: {name!r}")
