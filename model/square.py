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
    """Returns the first free space index or None if full."""
    for idx, space in enumerate(self.spaces):
      if space is None:
        return idx
    return None
