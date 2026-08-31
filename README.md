# DS4 Mapper

Maps a DualShock 4 controller to keyboard inputs system-wide, so you can play browser games with a controller.

## Requirements

- Python 3
- [pygame-ce](https://pypi.org/project/pygame-ce/)
- [pynput](https://pypi.org/project/pynput/)

```
pip install pygame-ce pynput
```

**macOS:** Grant Accessibility permission to your terminal in **System Settings → Privacy & Security → Accessibility**.

## Usage

Connect your DS4 via Bluetooth, then run:

```
python3 ds4_mapper.py
```

Click into your game or browser window and use the controller. Press `Ctrl-C` to stop.

### Discover Mode

If buttons aren't registering correctly, use discover mode to print the raw index for each button, stick, and trigger:

```
python3 ds4_mapper.py --discover
```

## Button Mapping

| Button | Key |
|--------|-----|
| Cross | `x` |
| Circle | `z` |
| Square | `s` |
| Triangle | `a` |
| Share | `v` |
| Options / START | `Enter` |
| L1 | `q` |
| R1 | `e` |
| D-pad Up | `↑` |
| D-pad Down | `↓` |
| D-pad Left | `←` |
| D-pad Right | `→` |

## Stick & Trigger Mapping

| Input | Negative | Positive |
|-------|----------|----------|
| Left Stick X | `f` | `h` |
| Left Stick Y | `t` | `g` |
| Right Stick X | `j` | `l` |
| Right Stick Y | `i` | `k` |
| L2 | — | `Tab` |
| R2 | — | `r` |
