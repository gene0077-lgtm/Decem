# Snake Game

A simple terminal-based implementation of the classic Snake game written in pure Python using the built-in `curses` module.

## Features

- Play directly in the terminal, no external dependencies required.
- Uses classic WASD or arrow keys for movement.
- Adjustable board size and game speed via command-line options.
- Keeps track of your score as you gobble up apples.

## Requirements

- Python 3.8 or newer.
- A terminal that supports the `curses` library (works out of the box on macOS, Linux, and WSL. For Windows, run inside the Windows Terminal with Python 3.8+ which bundles `windows-curses`).

## Getting Started

1. **Clone the repository** (already done if you're reading this).
2. **Run the game**:

   ```bash
   python3 -m snake_game
   ```

   Optional arguments:

   ```bash
   python3 -m snake_game --width 40 --height 20 --speed 12
   ```

   - `--width` / `--height` control the board dimensions.
   - `--speed` controls the number of frames per second.

3. **Controls**

   - Arrow keys **or** WASD to move.
   - `p` to pause / resume.
   - `q` to quit the game immediately.

Enjoy reliving the retro arcade fun!
