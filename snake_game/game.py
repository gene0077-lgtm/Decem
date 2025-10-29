from __future__ import annotations

import argparse
import curses
import random
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Deque, Iterable, Optional, Set


@dataclass(frozen=True)
class Point:
    x: int
    y: int

    def translate(self, dx: int, dy: int) -> "Point":
        return Point(self.x + dx, self.y + dy)


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self) -> tuple[int, int]:
        return self.value

    def is_opposite(self, other: "Direction") -> bool:
        dx, dy = self.delta
        ox, oy = other.delta
        return dx == -ox and dy == -oy


class GameState(Enum):
    RUNNING = auto()
    COLLISION = auto()
    WIN = auto()


class SnakeGame:
    """Terminal-based implementation of the classic Snake game."""

    board_offset_y: int = 2
    board_offset_x: int = 2

    def __init__(self, width: int = 30, height: int = 18, speed: int = 10) -> None:
        if width < 10 or height < 10:
            raise ValueError("Width and height must be at least 10.")
        if speed < 1 or speed > 30:
            raise ValueError("Speed must be between 1 and 30 frames per second.")

        self.width = width
        self.height = height
        self.speed = speed

        self.frame_delay = 1.0 / float(speed)

        self.snake: Deque[Point] = deque()
        self.snake_positions: Set[Point] = set()
        self.direction: Direction = Direction.RIGHT
        self.next_direction: Direction = Direction.RIGHT
        self.food: Optional[Point] = None
        self.score: int = 0
        self.paused: bool = False
        self.quit_requested: bool = False
        self.needs_redraw: bool = True

    # ------------------------- Public API -------------------------
    def run(self) -> None:
        curses.wrapper(self._curses_main)

    # ----------------------- Internal logic -----------------------
    def _curses_main(self, stdscr: "curses.window") -> None:
        self._initialise_curses(stdscr)
        self._reset_game()
        self._draw(stdscr, status_message="Use arrow keys or WASD to move.")

        last_update = 0.0
        while not self.quit_requested:
            start_loop = time.time()
            self._process_input(stdscr)

            if self.quit_requested:
                break

            now = time.time()
            if not self.paused and now - last_update >= self.frame_delay:
                state = self._update()
                last_update = now
                self._draw(stdscr)

                if state in (GameState.COLLISION, GameState.WIN):
                    message = (
                        f"You win! Score: {self.score}." if state is GameState.WIN else f"Game over! Score: {self.score}."
                    )
                    if not self._handle_game_end(stdscr, message):
                        break
                    last_update = time.time()
                    continue
            elif self.needs_redraw:
                self._draw(stdscr)

            self.needs_redraw = False

            elapsed = time.time() - start_loop
            sleep_for = max(0.0, min(self.frame_delay / 2, 0.016 - elapsed))
            if sleep_for > 0:
                time.sleep(sleep_for)

    def _initialise_curses(self, stdscr: "curses.window") -> None:
        curses.noecho()
        curses.cbreak()
        stdscr.nodelay(True)
        stdscr.keypad(True)
        try:
            curses.curs_set(0)
        except curses.error:
            pass

    def _reset_game(self) -> None:
        mid_x = self.width // 2
        mid_y = self.height // 2
        self.snake = deque(
            [
                Point(mid_x, mid_y),
                Point(mid_x - 1, mid_y),
                Point(mid_x - 2, mid_y),
            ]
        )
        self.snake_positions = set(self.snake)
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.score = 0
        self.paused = False
        self.quit_requested = False
        self.needs_redraw = True
        self._spawn_food()

    def _process_input(self, stdscr: "curses.window") -> None:
        try:
            while True:
                key = stdscr.getch()
                if key == -1:
                    break

                if key == curses.KEY_RESIZE:
                    self.needs_redraw = True
                    continue

                self._handle_key(key)
        except curses.error:
            # Some terminals raise a spurious error when resizing rapidly.
            return

    def _handle_key(self, key: int) -> None:
        direction_map = {
            curses.KEY_UP: Direction.UP,
            curses.KEY_DOWN: Direction.DOWN,
            curses.KEY_LEFT: Direction.LEFT,
            curses.KEY_RIGHT: Direction.RIGHT,
            ord("w"): Direction.UP,
            ord("W"): Direction.UP,
            ord("s"): Direction.DOWN,
            ord("S"): Direction.DOWN,
            ord("a"): Direction.LEFT,
            ord("A"): Direction.LEFT,
            ord("d"): Direction.RIGHT,
            ord("D"): Direction.RIGHT,
        }

        if key in direction_map:
            new_direction = direction_map[key]
            if not new_direction.is_opposite(self.direction) and new_direction != self.direction:
                self.next_direction = new_direction
                self.needs_redraw = True
            return

        if key in (ord("p"), ord("P")):
            self.paused = not self.paused
            self.needs_redraw = True
            return

        if key in (ord("q"), ord("Q")):
            self.quit_requested = True
            return

    def _update(self) -> GameState:
        if self.food is None:
            return GameState.WIN

        self.direction = self.next_direction
        head = self.snake[0]
        dx, dy = self.direction.delta
        new_head = head.translate(dx, dy)

        # Check walls
        if not (0 <= new_head.x < self.width and 0 <= new_head.y < self.height):
            return GameState.COLLISION

        growing = new_head == self.food
        tail = self.snake[-1]

        if new_head in self.snake_positions and not (not growing and new_head == tail):
            return GameState.COLLISION

        if not growing:
            self.snake.pop()
            self.snake_positions.remove(tail)

        self.snake.appendleft(new_head)
        self.snake_positions.add(new_head)

        if growing:
            self.score += 1
            self._spawn_food()
            if self.food is None:
                return GameState.WIN

        self.needs_redraw = True
        return GameState.RUNNING

    def _spawn_food(self) -> None:
        empty_cells = [
            Point(x, y)
            for y in range(self.height)
            for x in range(self.width)
            if Point(x, y) not in self.snake_positions
        ]
        self.food = random.choice(empty_cells) if empty_cells else None

    # --------------------------- Rendering ---------------------------
    def _draw(self, stdscr: "curses.window", status_message: Optional[str] = None) -> None:
        if not self._ensure_window_size(stdscr):
            return

        stdscr.erase()

        scoreboard = f" Score: {self.score} "
        length_info = f" Length: {len(self.snake)} "
        self._safe_addstr(stdscr, 0, 2, scoreboard, curses.A_REVERSE)
        self._safe_addstr(stdscr, 0, len(scoreboard) + 4, length_info)

        if self.paused:
            status_message = "Paused - press 'p' to resume."

        if status_message:
            self._safe_addstr(stdscr, 1, 2, status_message)

        self._draw_border(stdscr)
        self._draw_snake_and_food(stdscr)
        controls = "Controls: Arrow keys/WASD move | P pause | Q quit"
        max_y, max_x = stdscr.getmaxyx()
        self._safe_addstr(stdscr, max_y - 1, 2, controls)

        stdscr.refresh()

    def _draw_border(self, stdscr: "curses.window") -> None:
        top = self.board_offset_y - 1
        left = self.board_offset_x - 1
        bottom = top + self.height + 1
        right = left + self.width + 1

        for x in range(left, right + 1):
            self._safe_addch(stdscr, top, x, "#")
            self._safe_addch(stdscr, bottom, x, "#")

        for y in range(top + 1, bottom):
            self._safe_addch(stdscr, y, left, "#")
            self._safe_addch(stdscr, y, right, "#")

    def _draw_snake_and_food(self, stdscr: "curses.window") -> None:
        for index, segment in enumerate(self.snake):
            char = "@" if index == 0 else "O"
            y = self.board_offset_y + segment.y
            x = self.board_offset_x + segment.x
            self._safe_addch(stdscr, y, x, char)

        if self.food is not None:
            y = self.board_offset_y + self.food.y
            x = self.board_offset_x + self.food.x
            self._safe_addch(stdscr, y, x, "*")

    def _handle_game_end(self, stdscr: "curses.window", message: str) -> bool:
        prompt = f"{message} Press 'r' to play again or 'q' to quit."
        self._draw(stdscr, status_message=prompt)
        stdscr.nodelay(False)
        try:
            while True:
                key = stdscr.getch()
                if key in (ord("q"), ord("Q")):
                    self.quit_requested = True
                    stdscr.nodelay(True)
                    return False
                if key in (ord("r"), ord("R")):
                    stdscr.nodelay(True)
                    self._reset_game()
                    self._draw(stdscr)
                    return True
        finally:
            stdscr.nodelay(True)

    def _ensure_window_size(self, stdscr: "curses.window") -> bool:
        max_y, max_x = stdscr.getmaxyx()
        required_rows = self.board_offset_y + self.height + 3
        required_cols = self.board_offset_x + self.width + 3

        if max_y < required_rows or max_x < required_cols:
            stdscr.erase()
            warning = (
                f"Terminal too small. Need at least {required_cols}x{required_rows}, "
                f"current size is {max_x}x{max_y}."
            )
            self._safe_addstr(stdscr, max_y // 2, max(0, (max_x - len(warning)) // 2), warning)
            stdscr.refresh()
            time.sleep(0.4)
            return False
        return True

    def _safe_addstr(self, stdscr: "curses.window", y: int, x: int, text: str, attr: int = 0) -> None:
        max_y, max_x = stdscr.getmaxyx()
        if 0 <= y < max_y and x < max_x:
            truncated = text[: max(0, max_x - x)]
            if truncated:
                try:
                    stdscr.addstr(y, x, truncated, attr)
                except curses.error:
                    pass

    def _safe_addch(self, stdscr: "curses.window", y: int, x: int, char: str) -> None:
        max_y, max_x = stdscr.getmaxyx()
        if 0 <= y < max_y and 0 <= x < max_x:
            try:
                stdscr.addch(y, x, char)
            except curses.error:
                pass


# --------------------------- CLI Entrypoint ---------------------------

def _positive_int(value: str) -> int:
    try:
        ivalue = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Expected integer, received '{value}'.") from exc
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return ivalue


def parse_arguments(args: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play the classic Snake game in your terminal.")
    parser.add_argument("--width", type=_positive_int, default=30, help="Board width in cells (min 10).")
    parser.add_argument("--height", type=_positive_int, default=18, help="Board height in cells (min 10).")
    parser.add_argument(
        "--speed",
        type=_positive_int,
        default=10,
        help="Game speed in frames per second (1-30).",
    )
    parsed = parser.parse_args(args=args)
    if parsed.width < 10 or parsed.height < 10:
        parser.error("Width and height must both be at least 10.")
    if parsed.speed < 1 or parsed.speed > 30:
        parser.error("Speed must be between 1 and 30 frames per second.")
    return parsed


def main() -> None:
    options = parse_arguments()
    game = SnakeGame(width=options.width, height=options.height, speed=options.speed)
    game.run()


if __name__ == "__main__":
    main()
