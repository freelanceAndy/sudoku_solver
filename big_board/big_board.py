from pathlib import Path, PurePath

display_dir = Path(__file__).parent 
board_path = display_dir / 'board.txt'
numbers_dir = display_dir / 'numbers'
board = open(board_path, 'r').read().split("\n")
big_cells = {str(child.name).split('.')[0]:open(child, 'r').read() for child in numbers_dir.iterdir()}

def print_board(puzzle_cells, no_hints=False):
   puzzle_lookup = {cell._id:cell for cell in puzzle_cells}
   puzzle_str = ""
   last_cell_id = None
   last_line_number = None
   for line_number, char_number, char in iterate_board(board):
      if line_number != last_line_number and last_line_number != None:
         puzzle_str += '\n'
      last_line_number = line_number
      if char != ' ':
         puzzle_str += char
         continue
      cell_row, cell_col, big_rows = get_cell_id(puzzle_cells, line_number, char_number)
      cell_id = f"{cell_row}{cell_col}"
      if cell_id == last_cell_id:
         continue
      cell = puzzle_lookup[cell_id]
      glyph = get_glyph(cell, no_hints)
      glyph_chunk = get_glyph_chunk(line_number, big_rows, glyph)
      puzzle_str += glyph_chunk
      last_cell_id = cell_id
   print(puzzle_str)

def iterate_board(board):
   for line_number, line in enumerate(board):
      for char_number, char, in enumerate(line):
         yield (line_number, char_number, char)

def get_cell_id(puzzle_cells, line_number, char_number):
   cell_row, big_rows = row_lookup[line_number]
   cell_col = col_lookup[char_number]
   return (cell_row, cell_col, big_rows)

def get_glyph(cell, no_hints):
   if cell.value:
      glyph = big_cells[cell.value]
   elif no_hints:
      glyph = big_cells['no_hints']
   else:
      chars_to_replace = ''.join(cell.impossible_values)
      trans = str.maketrans(chars_to_replace, ''.join([' ' for i in range(len(chars_to_replace))]))
      glyph = str.translate(big_cells['empty'], trans)
   return glyph

def get_glyph_chunk(line_number, big_rows, glyph):
   glyph_rows = glyph.split("\n")
   for rel_row, row in enumerate(big_rows):
      if row != line_number:
         continue
      return glyph_rows[rel_row]

row_lookup = {}
for i in range(38):
   if   i in (1,2,3):
      row_lookup[i] = [1,[1,2,3]]
   elif i in (5,6,7):
      row_lookup[i] = [2,[5,6,7]]
   elif i in (9,10,11):
      row_lookup[i] = [3,[9,10,11]]
   elif i in (13,14,15):
      row_lookup[i] = [4,[13,14,15]]
   elif i in (17,18,19):
      row_lookup[i] = [5,[17,18,19]]
   elif i in (21,22,23):
      row_lookup[i] = [6,[21,22,23]]
   elif i in (25,26,27):
      row_lookup[i] = [7,[25,26,27]]
   elif i in (29,30,31):
      row_lookup[i] = [8,[29,30,31]]
   elif i in (33,34,35):
      row_lookup[i] = [9,[33,34,35]]

col_lookup = {}
for i in range(74):
   if    1 <= i <= 7:
      col_lookup[i] = 1
   elif  9 <= i <= 15:
      col_lookup[i] = 2
   elif 17 <= i <= 23:
      col_lookup[i] = 3
   elif 25 <= i <= 31:
      col_lookup[i] = 4
   elif 33 <= i <= 39:
      col_lookup[i] = 5
   elif 41 <= i <= 47:
      col_lookup[i] = 6
   elif 49 <= i <= 55:
      col_lookup[i] = 7
   elif 57 <= i <= 63:
      col_lookup[i] = 8
   elif 65 <= i <= 71:
      col_lookup[i] = 9

