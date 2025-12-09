from dataclasses import dataclass, field
from typing import Optional

from model.square import Square
from model.token import Token


@dataclass
class Board:
    """Board with 4 tracks and 24 columns (0-indexed)."""

    grid: list[list[Square]] = field(
        default_factory=lambda: [[Square() for _ in range(24)] for _ in range(4)]
    )
    jail: list[list[Token | None]] = field(
        default_factory=lambda: [[Token(id=j, color=i, in_jail=True) for j in range(4)] for i in range(4)]
    )

    def __post_init__(self) -> None:
        for i in range(4):
            for j in range(24):
                if j in [4, 11, 16]:
                    self.grid[i][j].set_safe_square()

    def exit_jail(self, token: Token) -> None:
        token.in_jail = False
        self.jail[token.color][token.id] = None

    def go_to_jail(self, token: Token) -> None:
        token.in_jail = True
        self.jail[token.color][token.id] = token
        if token.x is not None and token.y is not None:
            try:
                idx = self.grid[token.x][token.y].spaces.index(token)
                self.grid[token.x][token.y].spaces[idx] = None
            except ValueError:
                pass
        token.x = None
        token.y = None

    def remove_token_from_board(self, position: list[int]) -> None:
        self.grid[position[0]][position[1]].spaces[position[2]] = None

    def if_send_token_to_jail(self, moving_token_pos: list[int], replacing_token_pos: list[int]) -> None:
        moving_token = self.grid[moving_token_pos[0]][moving_token_pos[1]].spaces[moving_token_pos[2]]
        replacing_token = self.grid[replacing_token_pos[0]][replacing_token_pos[1]].spaces[replacing_token_pos[2]]

        if moving_token is None or replacing_token is None:
            return

        if moving_token.color != replacing_token.color:
            self.go_to_jail(replacing_token)
            self.remove_token_from_board(replacing_token_pos)

        self.grid[replacing_token_pos[0]][replacing_token_pos[1]].spaces[replacing_token_pos[2]] = moving_token

    def place_token_on_exit(self, token: Token) -> bool:
        available_space = self.grid[token.color][4].check_space()
        if available_space is not None:
            self.grid[token.color][4].spaces[available_space] = token
            token.in_jail = False
            token.x = token.color
            token.y = 4
            return True
        return False

    def place_token_on_board(self, token: Token, position: list[int]) -> bool:
        available_space = self.grid[position[0]][position[1]].check_space()
        if available_space is None:
            return False

        self.grid[position[0]][position[1]].spaces[available_space] = token
        # remove from previous position
        if token.x is not None and token.y is not None:
            try:
                current_space_idx = self.grid[token.x][token.y].spaces.index(token)
                self.grid[token.x][token.y].spaces[current_space_idx] = None
            except ValueError:
                pass

        # compute steps advanced when prior position is known
        if token.x is not None and token.y is not None:
            if position[0] != token.x:
                token.made_step((16 - token.y) + position[1])
            else:
                token.made_step(position[1] - token.y)
        token.x = position[0]
        token.y = position[1]
        return True

    def finish_line(self, token: Token) -> None:
        token.in_goal = True
        if token.x is not None and token.y is not None:
            space_idx = self.grid[token.x][token.y].spaces.index(token)
            self.grid[token.x][token.y].spaces[space_idx] = None

    def move_token(self, token: Token, new_position: list[int]) -> bool:
        """Moves a token and handles capture; new_position = [row, column]."""
        if token.in_goal:
            return False
        current_space_idx: Optional[int] = None
        if token.x is not None and token.y is not None:
            try:
                current_space_idx = self.grid[token.x][token.y].spaces.index(token)
            except ValueError:
                current_space_idx = None

        square = self.grid[new_position[0]][new_position[1]]
        occupying_tokens = [t for t in square.spaces if t is not None]
        if occupying_tokens and square.safe:
            # cannot capture on safe squares
            return False
        if occupying_tokens:
            # capture the first occupying token
            self.go_to_jail(occupying_tokens[0])
            idx_to_clear = square.spaces.index(occupying_tokens[0])
            square.spaces[idx_to_clear] = None

        target_space = square.check_space()
        if target_space is None:
            return False

        if current_space_idx is not None:
            self.grid[token.x][token.y].spaces[current_space_idx] = None

        square.spaces[target_space] = token
        token.x, token.y = new_position
        return True
