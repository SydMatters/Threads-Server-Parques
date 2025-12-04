from dataclasses import dataclass, field

from model.dice import Dice
from model.token import Token

@dataclass
class Player:
  name: str
  color: int
  tokens: list[Token] = field(default_factory=list)

  def __post_init__(self):
    self.tokens = [Token(i, self.color) for i in range(4)]
    
  def roll_dice(self, dice: Dice) -> int:
    return dice.roll_multiple()
