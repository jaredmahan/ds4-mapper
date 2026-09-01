import tomllib
from dataclasses import dataclass
from pathlib import Path

from pynput.keyboard import Key

from ds4mapper.keys import resolve

PROFILES_DIR = Path(__file__).parent / "profiles"


@dataclass
class Profile:
    name: str
    description: str
    buttons: dict[int, Key | str]
    axes: dict[int, tuple[Key | str, Key | str]]
    triggers: dict[int, Key | str]


def load_profile(name: str) -> Profile:
    path = PROFILES_DIR / f"{name}.toml"
    if not path.exists():
        raise FileNotFoundError(f"profile not found: {name!r}")

    with path.open("rb") as f:
        data = tomllib.load(f)

    if "buttons" not in data:
        raise ValueError("profile missing required section: buttons")
    if "axes" not in data:
        raise ValueError("profile missing required section: axes")
    if "triggers" not in data:
        raise ValueError("profile missing required section: triggers")

    buttons = {int(k): resolve(v) for k, v in data["buttons"].items()}
    axes = {int(k): (resolve(v[0]), resolve(v[1])) for k, v in data["axes"].items()}
    triggers = {int(k): resolve(v) for k, v in data["triggers"].items()}

    return Profile(
        name=data.get("name", name),
        description=data.get("description", ""),
        buttons=buttons,
        axes=axes,
        triggers=triggers,
    )


def list_profiles() -> list[str]:
    return sorted(p.stem for p in PROFILES_DIR.glob("*.toml"))


def key_to_toml(k: Key | str) -> str:
    """Serialize a pynput key back to its TOML string form."""
    return k if isinstance(k, str) else k.name


def save_profile(p: Profile, stem: str) -> None:
    """Write a Profile to PROFILES_DIR/<stem>.toml."""
    path = PROFILES_DIR / f"{stem}.toml"
    lines: list[str] = [f'name = "{p.name}"']
    if p.description:
        lines.append(f'description = "{p.description}"')
    lines += ["", "[buttons]"]
    for idx in sorted(p.buttons):
        lines.append(f'{idx:<2} = "{key_to_toml(p.buttons[idx])}"')
    lines += ["", "[axes]"]
    for idx in sorted(p.axes):
        neg = key_to_toml(p.axes[idx][0])
        pos = key_to_toml(p.axes[idx][1])
        if "?" not in (neg, pos):
            lines.append(f'{idx:<2} = ["{neg}", "{pos}"]')
    lines += ["", "[triggers]"]
    for idx in sorted(p.triggers):
        lines.append(f'{idx:<2} = "{key_to_toml(p.triggers[idx])}"')
    path.write_text("\n".join(lines) + "\n")
