# DS4 Mapper

Maps a DualShock 4 controller to keyboard inputs system-wide, so you can play browser games with a controller. Profiles are hot-swappable at runtime without restarting.

## Requirements

- Python 3.11+
- A DualShock 4 connected via Bluetooth

**macOS:** Grant Accessibility permission to your terminal in **System Settings → Privacy & Security → Accessibility** (required for keyboard injection).

## Install

From PyPI:

```bash
pip install ds4-mapper
```

Or from source (development mode):

```bash
git clone https://github.com/jaredmahan/ds4-mapper.git
cd ds4-mapper
pip install -e ".[dev]"
```

## Usage

Connect your DS4 via Bluetooth, then run:

```bash
ds4-mapper
```

Or without installing:

```bash
python -m ds4mapper
```

### Options

```
--profile NAME    Profile to load on startup (default: default)
--discover        Print raw button/axis indices — useful for building new profiles
```

### Discover Mode

If a button isn't registering, use discover mode to see the raw event index:

```bash
ds4-mapper --discover
```

## CLI Commands

Once the mapper is running, type commands at the `>` prompt:

| Command | Effect |
|---------|--------|
| `list` | Show available profiles |
| `switch <name>` | Load a profile (Tab-completes) |
| `current` | Show the active profile name |
| `reload` | Reload the current profile from disk |
| `view [<name>]` | Show button/axis/trigger mappings for a profile |
| `edit [<name>]` | Open the profile editor for an existing profile |
| `new <name>` | Create a new profile in the editor |
| `help` | Show command list |
| `quit` / `exit` | Stop |

## Profile Editor

`edit` and `new` open an interactive editor screen where you can map controller inputs to keyboard keys:

1. **Press a DS4 button, stick, or trigger** — the editor enters *waiting* mode and prompts for a key.
2. **Press the keyboard key** you want it mapped to — the mapping is recorded.
3. Repeat for each input you want to map.

You can also type commands in the editor's input field:

| Command | Effect |
|---------|--------|
| `save [stem]` | Save to disk (optional custom filename) |
| `delete <input>` | Remove a mapping (e.g. `delete Cross`) |
| `name <text>` | Set the profile display name |
| `desc <text>` | Set the profile description |
| `cancel` | Discard changes and return to the main screen |

Keyboard injection is suspended while the editor is open so controller inputs don't fire game actions.

## Profiles

Profiles live in `ds4mapper/profiles/`. Each is a TOML file:

```toml
name = "default"
description = "Standard browser game layout"

[buttons]
0 = "x"      # Cross
1 = "z"      # Circle
2 = "s"      # Square
3 = "a"      # Triangle
4 = "v"      # Share
6 = "enter"  # Options / START
9 = "q"      # L1
10 = "e"     # R1
11 = "up"
12 = "down"
13 = "left"
14 = "right"

[axes]
0 = ["f", "h"]   # Left Stick X (neg, pos)
1 = ["t", "g"]   # Left Stick Y
2 = ["j", "l"]   # Right Stick X
3 = ["i", "k"]   # Right Stick Y

[triggers]
4 = "tab"    # L2
5 = "r"      # R2
```

Special key names: `enter`, `tab`, `up`, `down`, `left`, `right`, `space`, `esc`, `shift`, `ctrl`, `alt`. Single characters are used directly.

Profiles can be created or edited from the CLI with `new` and `edit`, or by copying and editing TOML files directly.

## Publishing to PyPI

This project uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) via GitHub Actions. To release a new version:

1. Bump `version` in `pyproject.toml`.
2. Create a GitHub release — the `publish.yml` workflow builds and uploads the distribution automatically.
