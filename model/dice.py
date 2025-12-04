from dataclasses import dataclass
from random import randint

@dataclass
class Dice:
  sides: int = 6

  def roll(self) -> int:
    return randint(1, self.sides)

  def roll_multiple(self, number_of_dice: int = 2) -> list[int]:
    return [self.roll() for _ in range(number_of_dice)]
