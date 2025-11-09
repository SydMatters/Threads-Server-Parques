from dataclasses import dataclass, field

from square import Square
from token import Token

@dataclass
class Board:
  #grid[row][column]
  grid: list[list[Square]] = field(default_factory=lambda: [[Square() for _ in range(23)] for _ in range(4)])
  jail: list[list[Token]] = field(default_factory=lambda: [[Token(id=j, color=i, in_jail=True) for j in range(4)] for i in range(4)])
  
  def __post_init__(self):
    for i in range(4):
      for j in range(24):
        if j in [4, 11, 16]:
          self.grid[i][j].set_safe_square()
  
  def exit_jail(self, token: Token):
    token.in_jail = False
    self.jail[token.color][token.id] = None
  
  def go_to_jail(self, token: Token):
    token.in_jail = True
    self.jail[token.color][token.id] = token
    
  #Position format: [row, column, space]
  def remove_token_from_board(self, position: list):
    self.grid[position[0]][position[1]].spaces[position[2]] = None
    
  def if_send_token_to_jail(self, moving_token_pos: list, replacing_token_pos: list):
    moving_token = self.grid[moving_token_pos[0]][moving_token_pos[1]].spaces[moving_token_pos[2]]
    replacing_token = self.grid[replacing_token_pos[0]][replacing_token_pos[1]].spaces[replacing_token_pos[2]]
    
    if moving_token.color != replacing_token.color:
      self.go_to_jail(replacing_token)
      self.remove_token_from_board(replacing_token_pos)

    self.grid[replacing_token_pos[0]][replacing_token_pos[1]].spaces[replacing_token_pos[2]] = moving_token
    
  def place_token_on_exit(self, token: Token):
    available_space = self.grid[token.color][4].check_space()
    if(available_space is not None):
      self.grid[token.color][4].spaces[available_space] = token
  
  def place_token_on_board(self, token: Token, position: list):
    available_space = self.grid[position[0]][position[1]].check_space()
    if(available_space is not None):
      self.grid[position[0]][position[1]].spaces[available_space] = token
      self.grid[token.x][token.y].spaces.remove(token)
      
      if(position[0] != token.x):
        token.made_step((16-token.y)+position[1])
      else:
        token.made_step(position[1]-token.y)
      token.x = position[0]
      token.y = position[1]
    
  def finish_line(self, token: Token):
    token.in_goal = True
    self.grid[token.x][token.y].spaces.remove(token)
  
      
  
  
  
    