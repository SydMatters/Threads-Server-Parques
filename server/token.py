from dataclasses import dataclass, field

@dataclass
class Token:
  id: int
  color: str
  x: int = 0
  y: int = 0
  steps: int = 0
  in_jail: bool = True
  in_goal: bool = False
  
  def made_step(self, steps: int):
    self.steps += steps
  