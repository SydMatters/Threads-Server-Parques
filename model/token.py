from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Token:
    id: int
    color: int
    x: Optional[int] = None
    y: Optional[int] = None
    steps: int = 0
    in_jail: bool = True
    in_goal: bool = False

    def made_step(self, steps: int) -> None:
        self.steps += steps
