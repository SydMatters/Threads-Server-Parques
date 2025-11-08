from rich import print as pprint
import numpy as np

class square:
    def __init__(self, column):
        self.column = column
        self.spaces = [None, None]
        self.safe_square = False
                
    def set_spaces(self, ficha, space_number):
        self.spaces[space_number] = ficha
    
    def set_safe_square(self):
        if self.column == 4 or self.column == 11 or  self.column == 16:
            self.safe_square = True
        
    def is_first_space_occupied(self):
        if self.spaces[0] is None:
            return False
        else:
            return True
        
    def is_second_space_occupied(self):
        if self.spaces[1] is None:
            return False
        else:
            return True

    def __repr__(self):
        first_space_status = self.is_first_space_occupied()
        second_space_status = self.is_second_space_occupied()
        if first_space_status == False and second_space_status == False:
            return f"ninguno de los espacios esta ocupado, Es una casilla segura?: {self.safe_square}"
        elif first_space_status == True and second_space_status == False:
            return f"el primer espacio esta ocupado por una ficha de {self.spaces[0]}, el segundo espacio esta libre, Es una casilla segura?: {self.safe_square}"
        else:
            return f"ambos espacios estan ocupados por fichas de {self.spaces[0]} y {self.spaces[1]}, Es una casilla segura?: {self.safe_square}"

class token:
    def __init__(self, color, token_number):
        self.color = color
        self.token_number = token_number
        self.steps = 0
    
    def set_steps(self, steps):
        self.steps = steps
    
    def raise_steps(self, steps):
        self.steps += steps

    def __repr__(self):
        if self.color == 0:
            color = "verde"
        elif self.color == 1:
            color = "azul"
        elif self.color == 2:
            color = "amarillo"
        else:
            color = "rojo"
        return f"color: {color}"

def generate_random_number():
    rng= np.random.default_rng()
    return rng.integers(0, 6)

def generate_board():
    board = [[None for _ in range(24)] for _ in range(4)]
    i = 0
    j = 0
    while i < 4:
        j = 0
        while j <= 23:
            square_instance = square(j)
            square_instance.set_safe_square()
            board[i][j] = square_instance
            j += 1
        i += 1
    return board

def generate_jail():
    jail = [[None for _ in range(4)] for _ in range(4)]
    return jail

board = generate_board()
jail = generate_jail()

def remove_token_from_board(position: list):
    row = position[0]
    column = position[1]
    space = position[2]
    if space == 1:
        jail[board[row][column].spaces[0].color][board[row][column].spaces[0].token_number] = board[row][column].spaces[0]
        board[row][column].set_spaces(None, 0)
    else:
        jail[board[row][column].spaces[1].color][board[row][column].spaces[1].token_number] = board[row][column].spaces[1]
        board[row][column].set_spaces(None, 1)

def remove_token_from_square(position: list):
    row = position[0]
    column = position[1]
    space = position[2]
    if space == 1:
        board[row][column].set_spaces(None, 0)
    else:
        board[row][column].set_spaces(None, 1)

def decide_send_token_to_jail(position_of_moving_token: list,position_of_replacing_token: list):
    row_of_moving_token = position_of_moving_token[0]
    column_of_moving_token = position_of_moving_token[1]
    space_of_moving_token = position_of_moving_token[2]
    row_of_replacing_token = position_of_replacing_token[0]
    column_of_replacing_token = position_of_replacing_token[1]
    try:
        if space_of_moving_token == 1:
            if board[row_of_moving_token][column_of_moving_token].spaces[0].color != board[row_of_replacing_token][column_of_replacing_token].spaces[1].color:
                remove_token_from_board([row_of_replacing_token, column_of_replacing_token, 1])
                board[row_of_replacing_token][column_of_replacing_token].set_spaces(board[row_of_moving_token][column_of_moving_token].spaces[0])
            else:
                board[row_of_replacing_token][column_of_replacing_token].set_spaces(board[row_of_moving_token][column_of_moving_token].spaces[0])
        else:
            if board[row_of_moving_token][column_of_moving_token].spaces[1].color != board[row_of_replacing_token][column_of_replacing_token].spaces[0].color:
                remove_token_from_board([row_of_replacing_token, column_of_replacing_token, 2])
                board[row_of_replacing_token][column_of_replacing_token].set_spaces(board[row_of_moving_token][column_of_moving_token].spaces[1], 0)
            else:
                board[row_of_replacing_token][column_of_replacing_token].set_spaces(board[row_of_moving_token][column_of_moving_token].spaces[1], 1)
    except AttributeError:
        print("No es posible comer la ficha propia")
    
def move_forward_through_board(position: list):
    row = position[0]
    column = position[1]
    space = position[2]
    dice_result = generate_random_number()
    if column + dice_result <= 16 and check_space([row, column + dice_result]) == 1:
        board[row][column+dice_result].set_spaces(board[row][column].spaces[space], 0)
    elif column + dice_result <= 16 and check_space([row, column + dice_result]) == 2:
        decide_send_token_to_jail([row, column, space], [row, column + dice_result])
    elif column + dice_result > 16 and row < 3 and board[row][column].steps < 64 and check_space([row+1, dice_result+column-16]) == 1:
        board[row+1][dice_result+column-16].set_spaces(board[row][column].spaces[space], 0)
    elif column + dice_result > 16 and row < 3 and board[row][column].steps < 64 and check_space([row+1, dice_result+column-16]) == 2:
        decide_send_token_to_jail([row, column, space], [row+1, dice_result+column-16])
    elif column + dice_result > 16 and row == 3 and board[row][column].steps < 64 and check_space([0, dice_result+column-16]) == 1:
        board[0][dice_result+column-16].set_spaces(board[row][column].spaces[space], 0)
    elif column + dice_result > 16 and row == 3 and board[row][column].steps < 64 and check_space([0, dice_result+column-16]) == 2:
        decide_send_token_to_jail([row, column, space], [0, dice_result+column-16])
    elif column + dice_result > 16 and board[row][column].steps >= 64:
        board[row][column + dice_result].set_spaces(board[row][column].spaces[space], 0)
    elif column > 16 and  column + dice_result < 23:
        board[row][column + dice_result].set_spaces(board[row][column].spaces[space], 0)
    elif column > 16 and column + dice_result >= 23: 
        print("Haz ganado")
    board[row][column].set_spaces(None, space)

def initialize_jail():
    i = 0
    while i <= 3:
        j = 0
        while j <= 3:
            jail[i][j] = token(i,j)
            j+=1
        i+=1

def escape_from_jail(position_of_token_in_jail: list):
    row = position_of_token_in_jail[0]
    column = position_of_token_in_jail[1]
    first_dice = generate_random_number()
    second_dice = generate_random_number()
    if first_dice == second_dice:
        released_token = jail[row][column]
        jail[row][column] = None
        return released_token
    else:
        return False
    
def check_space(position: list):
    square_under_check = board[position[0]][position[1]]
    if square_under_check.is_first_space_occupied() == True:
        if square_under_check.is_second_space_occupied() == True:
            return 0
        else:
            return 2
    else:
        return 1

def liberate_token(released_token: token):
    check_result = check_space([released_token.color, 0])
    if  check_result == 0:
        print("No es posible liberar la ficha en este momento")
    elif check_result == 1:
        board[released_token.color][0].set_spaces(released_token, 0)
    else:
        board[released_token.color][0].set_spaces(released_token, 1)

def main(): 
    initialize_jail()
    result_escape_from_jail = False
    while result_escape_from_jail == False:
        result_escape_from_jail = escape_from_jail([3,0])
        if result_escape_from_jail != False:
            liberate_token(result_escape_from_jail)
    move_forward_through_board([3, 0, 0])
    pprint(board[3])

if __name__ == "__main__":
    main()