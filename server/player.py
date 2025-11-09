from dataclasses import dataclass, field
from token import Token

from server.dice import Dice

@dataclass
class Player:
  name: str
  color: str
  tokens: list[Token] = field(default_factory=list)

  def __post_init__(self):
    self.tokens = [Token(i, self.color) for i in range(4)]
    
  def roll_dice(self, dice: Dice) -> int:
    return dice.roll()
