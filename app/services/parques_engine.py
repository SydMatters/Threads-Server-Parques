from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from model.board import Board
from model.dice import Dice
from model.player import Player
from model.token import Token


COLORS = ["verde", "azul", "amarillo", "rojo"]


def color_index_from_name(name: str) -> int:
    lname = name.lower()
    aliases = {
        "green": "verde",
        "blue": "azul",
        "yellow": "amarillo",
        "red": "rojo",
    }
    lname = aliases.get(lname, lname)
    for idx, color in enumerate(COLORS):
        if lname.startswith(color):
            return idx
    # default sequential assignment handled in engine
    return 0


@dataclass
class ParquesEngine:
    """Lightweight Parqués rules engine for REST orchestration."""

    board: Board = field(default_factory=Board)
    dice: Dice = field(default_factory=Dice)
    players: List[Player] = field(default_factory=list)
    started: bool = False
    turn_index: int = 0
    last_roll: List[int] | None = None
    winner: Optional[str] = None
    rolls_in_turn: int = 0
    consecutive_doubles: int = 0

    def add_player(self, name: str, color_idx: Optional[int] = None) -> None:
        if self.started:
            raise ValueError("Game already started")
        if len(self.players) >= 4:
            raise ValueError("Game is full")
        if any(p.name == name for p in self.players):
            return

        if color_idx is None:
            color_idx = len(self.players) % len(COLORS)

        used_colors = {p.color for p in self.players}
        if color_idx in used_colors:
            raise ValueError("Color already taken")

        player = Player(name=name, color=color_idx)
        self.players.append(player)

    def start(self) -> None:
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to start")
        self.started = True
        self.turn_index = 0
        self.rolls_in_turn = 0
        self.consecutive_doubles = 0

    @property
    def current_player(self) -> Player:
        return self.players[self.turn_index % len(self.players)]

    def next_turn(self, reset_last_roll: bool = True) -> None:
        self.turn_index = (self.turn_index + 1) % len(self.players)
        self.rolls_in_turn = 0
        self.consecutive_doubles = 0
        if reset_last_roll:
            self.last_roll = None

    def _all_tokens_in_jail(self, player: Player) -> bool:
        return all(t.in_jail for t in player.tokens)

    def _release_from_jail(self, player: Player) -> bool:
        """Place one jailed token on the exit if possible."""
        jailed = [t for t in player.tokens if t.in_jail]
        if not jailed:
            return False
        token = jailed[0]
        placed = self.board.place_token_on_exit(token)
        return placed

    def _farthest_token(self, player: Player) -> Optional[Token]:
        on_board = [t for t in player.tokens if not t.in_jail and not t.in_goal and t.steps >= 0]
        if not on_board:
            return None
        return max(on_board, key=lambda t: t.steps)

    def roll_for_current_player(self) -> List[int]:
        if not self.started:
            raise ValueError("Game not started")
        player = self.current_player
        self.rolls_in_turn += 1
        self.last_roll = player.roll_dice(self.dice)
        is_double = len(self.last_roll) == 2 and self.last_roll[0] == self.last_roll[1]
        if is_double:
            self.consecutive_doubles += 1
            # Si todas las fichas están en cárcel, sacar una; si no, el jugador puede decidir (no auto-liberamos)
            if self._all_tokens_in_jail(player):
                self._release_from_jail(player)
            if self.consecutive_doubles >= 3:
                token = self._farthest_token(player)
                if token:
                    self.board.go_to_jail(token)
                self.next_turn(reset_last_roll=False)
        else:
            self.consecutive_doubles = 0
            # If all tokens are jailed, allow up to 3 tries; on 3rd failure pass turn
            if self._all_tokens_in_jail(player) and self.rolls_in_turn >= 3:
                self.next_turn(reset_last_roll=False)
        return self.last_roll

    def _can_exit_jail(self, roll: List[int]) -> bool:
        return len(roll) == 2 and roll[0] == roll[1]

    def _all_tokens_at_goal(self, player: Player) -> bool:
        return all(t.in_goal for t in player.tokens)

    def _move_steps(self, token: Token, steps: int) -> bool:
        # Simplified forward movement on a single track; wrap to next row after column 16
        if token.in_goal:
            return False

        if token.in_jail:
            if not self._can_exit_jail(self.last_roll or []):
                return False
            exited = self.board.place_token_on_exit(token)
            return exited

        # Compute destination position (row, column)
        row, col = token.x, token.y
        if row is None or col is None:
            return False

        new_row, new_col = row, col + steps
        # Wrap track across rows after column 16, simplified
        while new_col > 23:
            new_col -= 24
        moved = self.board.move_token(token, [new_row, new_col])
        if moved:
            token.made_step(steps)
        if moved and token.steps >= 96:
            token.in_goal = True
            self.board.finish_line(token)
        return moved

    def move_token(self, player_name: str, tokens: int | list[int], steps: Optional[int] = None) -> bool:
        if not self.started:
            raise ValueError("Game not started")
        if player_name != self.current_player.name:
            raise ValueError("Not this player's turn")
        token_list = [tokens] if isinstance(tokens, int) else tokens
        if not token_list:
            raise ValueError("No tokens specified")
        for token_id in token_list:
            if token_id < 0 or token_id > 3:
                raise ValueError("Invalid token")

        player = next((p for p in self.players if p.name == player_name), None)
        if not player:
            raise ValueError("Player not found")

        if len(token_list) == 1:
            token_id = token_list[0]
            if steps is None:
                if not self.last_roll:
                    raise ValueError("Roll dice first")
                steps = sum(self.last_roll)
            token = player.tokens[token_id]
            if token.in_jail and not self._can_exit_jail(self.last_roll or []):
                raise ValueError("La ficha está en la cárcel, necesitas doble para moverla")
            moved = self._move_steps(token, steps)
        else:
            for token_id in token_list:
                token = player.tokens[token_id]
                if steps is None:
                    if not self.last_roll:
                        raise ValueError("Roll dice first")
                    steps = self.last_roll[token_id]
                if token.in_jail and not self._can_exit_jail(self.last_roll or []):
                    raise ValueError("La ficha está en la cárcel, necesitas doble para moverla")
                moved = self._move_steps(token, steps)

        if moved and self._all_tokens_at_goal(player):
            self.winner = player.name

        is_double = self.last_roll and len(self.last_roll) == 2 and self.last_roll[0] == self.last_roll[1]
        if self.consecutive_doubles >= 3:
            # already handled in roll; ensure counters reset and move turn on
            self.next_turn()
        elif not is_double:
            self.next_turn()
        return moved

    def state(self) -> Dict:
        return {
            "players": [
                {
                    "name": p.name,
                    "color": COLORS[p.color],
                    "tokens": [
                        {
                            "id": t.id,
                            "x": t.x,
                            "y": t.y,
                            "steps": t.steps,
                            "in_jail": t.in_jail,
                            "in_goal": t.in_goal,
                        }
                        for t in p.tokens
                    ],
                }
                for p in self.players
            ],
            "turn": self.current_player.name if self.players else None,
            "last_roll": self.last_roll,
            "winner": self.winner,
        }
