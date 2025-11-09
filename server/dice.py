from dataclasses import dataclass
from random import random

@dataclass
class Dice:
  sides: int = 6

  def roll(self) -> int:
    return random.randint(1, self.sides)
