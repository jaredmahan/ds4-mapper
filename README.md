# DS4 Mapper

Maps a DualShock 4 controller to keyboard inputs system-wide, so you can play browser games with a controller. Profiles are hot-swappable at runtime without restarting.

## Requirements

- Python 3.11+
- A DualShock 4 connected via Bluetooth

**macOS:** Grant Accessibility permission to your terminal in **System Settings → Privacy & Security → Accessibility** (required for keyboard injection).

## Install

```bash
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
| `help` | Show command list |
| `quit` / `exit` | Stop |

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

Copy `ds4mapper/profiles/default.toml` to create a new profile, then `switch <name>` to load it without restarting.
