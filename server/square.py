from dataclasses import dataclass, field

@dataclass
class Square:
  spaces: list = field(default_factory=lambda: [None for _ in range(4)])
  safe: bool = False
  exit: bool = False
  blocked: bool = False
  
  def set_safe_square(self):
    self.safe = True
    
  def set_blocked_square(self):
    self.blocked = True
    
  def check_space(self) -> int | None:
    if self.spaces[0] is not None:
      if self.spaces[1] is not None:
        if self.spaces[2] is not None:
          if self.spaces[3] is not None:
            return None
          else:
            return 3
        else:
          return 2
      else:
        return 1
    else:
      return 0
