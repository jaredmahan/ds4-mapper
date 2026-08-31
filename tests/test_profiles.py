import textwrap
from pathlib import Path

import pytest
from pynput.keyboard import Key

from ds4mapper.profiles import Profile, list_profiles, load_profile


def _write_toml(tmp_path: Path, content: str, filename: str = "test.toml") -> Path:
    d = tmp_path / "profiles"
    d.mkdir()
    (d / filename).write_text(textwrap.dedent(content))
    return d


def test_load_valid_profile(tmp_path, monkeypatch):
    profiles_dir = _write_toml(
        tmp_path,
        """
        name = "test"
        description = "A test profile"

        [buttons]
        0 = "x"
        6 = "enter"

        [axes]
        0 = ["f", "h"]

        [triggers]
        4 = "tab"
        """,
    )
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", profiles_dir)

    profile = load_profile("test")

    assert isinstance(profile, Profile)
    assert profile.name == "test"
    assert profile.description == "A test profile"
    assert profile.buttons[0] == "x"
    assert profile.buttons[6] == Key.enter
    assert profile.axes[0] == ("f", "h")
    assert profile.triggers[4] == Key.tab


def test_load_profile_unknown_key_raises(tmp_path, monkeypatch):
    profiles_dir = _write_toml(
        tmp_path,
        """
        name = "bad"
        description = "Bad profile"

        [buttons]
        0 = "notakey"

        [axes]

        [triggers]
        """,
        "bad.toml",
    )
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", profiles_dir)

    with pytest.raises(ValueError, match="unknown key"):
        load_profile("bad")


def test_load_profile_missing_buttons_section_raises(tmp_path, monkeypatch):
    profiles_dir = _write_toml(
        tmp_path,
        """
        name = "bad"
        description = "Missing section"

        [axes]
        [triggers]
        """,
        "bad.toml",
    )
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", profiles_dir)

    with pytest.raises(ValueError, match="missing.*buttons"):
        load_profile("bad")


def test_load_profile_not_found_raises(tmp_path, monkeypatch):
    d = tmp_path / "profiles"
    d.mkdir()
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", d)

    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent")


def test_list_profiles_returns_sorted_names(tmp_path, monkeypatch):
    d = tmp_path / "profiles"
    d.mkdir()
    for name in ("zebra", "alpha", "middle"):
        (d / f"{name}.toml").write_text("")
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", d)

    assert list_profiles() == ["alpha", "middle", "zebra"]


def test_list_profiles_ignores_non_toml_files(tmp_path, monkeypatch):
    d = tmp_path / "profiles"
    d.mkdir()
    (d / "valid.toml").write_text("")
    (d / "ignored.txt").write_text("")
    monkeypatch.setattr("ds4mapper.profiles.PROFILES_DIR", d)

    assert list_profiles() == ["valid"]
