import sys
import math
import atexit
import argparse
from enum import Enum
from itertools import chain, combinations

Entity = Enum('Entity', 'row col blk')
all_values = set([str(i) for i in range(1,10)])

class SudokuSolver:

   def __init__(self):
      parser = argparse.ArgumentParser()
      parser.add_argument('--puzzle-file-path', type=str, required=True)
      parser.add_argument('--display-unsolved-puzzle', action='store_true')
      parser.add_argument('--silent', action='store_false')
      parser.add_argument('--cell', action='append', default=[], help="debug helper. eg. '--cell 15 --cell 16'")
      params = parser.parse_args()
      self.verbose = params.silent if True else False
      self.solve_puzzle(params)

   def solve_puzzle(self, params):
      self.import_puzzle(params.puzzle_file_path, params.display_unsolved_puzzle)
      self.loops = 0
      self.loop_limit = 15
      atexit.register(self.print_puzzle)
      atexit.register(self.validate_board)
      atexit.register(self.solution_status)
      atexit.register(self.print_specific_cell_info, params.cell)
      while self.puzzle_unsolved() and self.loops < self.loop_limit:
         self.loop_count()
         self.set_impossible_values()
         self.set_values()

   def import_puzzle(self, puzzle_file_path, display_unsolved_puzzle):
      file_str = open(puzzle_file_path,'r').read().strip()
      self.puzzle = [self.SudokuCell(char, idx, self.verbose) for idx, char in enumerate(file_str)]
      self.print_puzzle()
      if display_unsolved_puzzle:
         exit()

   class SudokuCell:

      def __init__(self, value, idx, verbose):
         if value == '_':
            value = None
         self._value = value
         self.set_coordinates(idx)
         if self._value:
            self.impossible_values = all_values - set([self._value])
         else:
            self.impossible_values = set()
         self.verbose = verbose

      def set_coordinates(self, idx) -> int:
         self.row = math.ceil((idx+1)/9)
         self.col = int(str(idx/9).split('.')[-1][0])+1
         self.blk = {1: {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3},
                     2: {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3},
                     3: {1:1, 2:1, 3:1, 4:2, 5:2, 6:2, 7:3, 8:3, 9:3},
                     4: {1:4, 2:4, 3:4, 4:5, 5:5, 6:5, 7:6, 8:6, 9:6},
                     5: {1:4, 2:4, 3:4, 4:5, 5:5, 6:5, 7:6, 8:6, 9:6},
                     6: {1:4, 2:4, 3:4, 4:5, 5:5, 6:5, 7:6, 8:6, 9:6},
                     7: {1:7, 2:7, 3:7, 4:8, 5:8, 6:8, 7:9, 8:9, 9:9},
                     8: {1:7, 2:7, 3:7, 4:8, 5:8, 6:8, 7:9, 8:9, 9:9},
                     9: {1:7, 2:7, 3:7, 4:8, 5:8, 6:8, 7:9, 8:9, 9:9}}[self.row][self.col]
         self.id = f"r{self.row}c{self.col}_b{self.blk}"
         self._id = f"{self.row}{self.col}"

      def ent(self, entity_id):
         if entity_id is Entity.row:
            return self.row
         elif entity_id is Entity.col:
            return self.col
         elif entity_id is Entity.blk:
            return self.blk

      @property
      def value(self):
         return self._value

      @value.setter
      def value(self, submitted_value) -> str:
         if (submitted_value in self.impossible_values) or (submitted_value not in all_values):
            raise ValueError(f"value: {submitted_value} is not possible")
         self._value = submitted_value
         self.impossible_values = all_values - set([self._value])

      def possible_values(self):
         if self._value:
            return set([self._value])
         else:
            return all_values - self.impossible_values

      def add_impossible_value(self, impossible_value, message=None, func=None):
         if impossible_value not in self.impossible_values:
            self.impossible_values.add(impossible_value)
            if message and self.verbose:
               print(f"\tIMPOSSIBLE: r{self.row}c{self.col}: {impossible_value} ({message})")
            if func and self.verbose:
               func() # prints puzzle

   def puzzle_unsolved(self):
      self.unsolved_cell_count = len([cell for cell in self.puzzle if cell.value is None])
      if self.unsolved_cell_count == 0 and self.verbose:
         print("Complete!")
      return 0 != self.unsolved_cell_count

   def loop_count(self):
      self.loops += 1
      if self.loops > self.loop_limit:
         sys.exit(f"...Puzzle unsolved")
      self.solution_status()

   def solution_status(self):
      if self.verbose:
         remaining_cell_msg = f" Remaining Cells: {self.unsolved_cell_count}"
         print(f"Current Loop: {self.loops} (loop_limit={self.loop_limit}){remaining_cell_msg}")

   def set_impossible_values(self):
      for cell in self.puzzle:
         if cell.value:
            continue
         self.impossible_in_entity(cell, self.get_ent(cell.row, Entity.row), Entity.row)
         self.impossible_in_entity(cell, self.get_ent(cell.col, Entity.col), Entity.col)
         self.impossible_in_entity(cell, self.get_ent(cell.blk, Entity.blk), Entity.blk)

      for entity_type in Entity:
         for ent_id in range(1,10):
            entity = self.get_ent(ent_id, entity_type)
            empty_cells = [c for c in entity if c.value is None]
            for grp, other_cells in self.get_powerset(empty_cells):
               self.shared_hidden_values(grp, other_cells)
               self.shared_naked_values(grp, other_cells)

      for blk in set([cell.blk for cell in self.puzzle]):
         self.check_vector_beyond_blk(blk)
         self.check_subvectors_within_blk(blk)

   def get_ent(self, entity_id, entity_type, empty_only=False):
      return [cell for cell in self.puzzle if (cell.ent(entity_type) == entity_id and ((empty_only and cell.value is None) or not empty_only))]
 
   def impossible_in_entity(self, cell, entity, entity_type):
      for other_cell in entity:
         if (other_cell.value is None):
            continue
         else:
            cell.add_impossible_value(other_cell.value, entity_type.name)

   def shared_hidden_values(self, grp, other_cells):
      # For strategy explanation, see https://www.learn-sudoku.com/hidden-pairs.html
      grp_size = {2:"double", 3:"triple", 4:"quadruple"}
      outside_values = set.union(*[cell.possible_values() for cell in other_cells])
      for combo in combinations(grp, 2):
         value_intersection = set.intersection(*[cell.possible_values() - outside_values for cell in combo])
         if len(value_intersection) >= len(grp):
            shared_hidden_group = [c for c in combo]
            last_grp_members = [c for c in grp if c not in combo]
            if last_grp_members:
               last_grp_member = last_grp_members[0]
               last_mbr_intersect = value_intersection.intersection(last_grp_member.possible_values())
               if len(last_mbr_intersect) >= len(value_intersection)-1:
                  shared_hidden_group.append(last_grp_member)
            for cell in shared_hidden_group:
               for value in outside_values:
                  cell.add_impossible_value(value, f"hidden_{grp_size[len(grp)]}")

   def shared_naked_values(self, grp, other_cells):
      # For strategy explanation, see: https://www.learn-sudoku.com/naked-pairs.html
      grp_size = {2:"double", 3:"triple", 4:"quadruple"}
      value_union = set.union(*[cell.possible_values() for cell in grp])
      outside_values = set.union(*[cell.possible_values() for cell in other_cells])
      for c in other_cells:
         if c.possible_values().issubset(value_union):
            return # catch you on the flipside, grp.
      if len(value_union) == len(grp):
         for cell in other_cells:
            for value in value_union:
               cell.add_impossible_value(value, f"naked_{grp_size[len(grp)]}")

   def get_powerset(self, empty_cells):
      for grp in self.powerset(empty_cells):
         if len(grp) in (0,1) or len(grp) > 4 or len(grp) == len(empty_cells):
            continue
         other_cells = [c for c in empty_cells if c not in grp]
         yield (grp, other_cells)

   def powerset(self, iterable):
      s = list(iterable)
      return chain.from_iterable(combinations(s, r) for r in range(len(s)+1)) 

   def check_vector_beyond_blk(self, blk):
      all_blk_cells = self.get_ent(blk, Entity.blk)
      solved_blk_values = set([c.value for c in all_blk_cells if c.value])
      blk_cells_without_values = [c for c in all_blk_cells if c.value is None]
      if len(blk_cells_without_values) == 0:
         return
      for entity_type in [Entity.row, Entity.col]:
         e_range = set([c.ent(entity_type) for c in all_blk_cells if c.value is None])
         empty_vectors_possibilities = {v:set([]) for v in e_range}
         for c in blk_cells_without_values:
            empty_vectors_possibilities[c.ent(entity_type)].update(c.possible_values())
         for vector,possibilities in empty_vectors_possibilities.items():
            other_possibilities = set()
            for other_vect,other_pos in empty_vectors_possibilities.items():
               if other_vect != vector:
                  other_possibilities.update(other_pos)

            difference = possibilities - other_possibilities 
            cells_in_vector_beyond_blk = [c for c in self.get_ent(vector, entity_type, empty_only=True) if c.blk != blk] 
            for value in difference:
               for c in cells_in_vector_beyond_blk:
                  c.add_impossible_value(value, message='vector_beyond_blk')

   def check_subvectors_within_blk(self, blk):
      all_blk_cells = self.get_ent(blk, Entity.blk)
      solved_blk_values = set([c.value for c in all_blk_cells if c.value])
      blk_cells_without_values = [c for c in all_blk_cells if c.value is None]
      if len(blk_cells_without_values) == 0:
         return
      for entity_type in [Entity.row, Entity.col]:
         e_range = set([c.ent(entity_type) for c in all_blk_cells if c.value is None])
         empty_vectors_possibilities = {v:[set(),[]] for v in e_range}
         for c in blk_cells_without_values:
            empty_vectors_possibilities[c.ent(entity_type)][0].update(c.possible_values())
            empty_vectors_possibilities[c.ent(entity_type)][1].append(c)

         for vector,possibilities in empty_vectors_possibilities.items():
            other_possibilities = set()
            for other_vect,other_pos in empty_vectors_possibilities.items():
               if other_vect != vector:
                  other_possibilities.update(other_pos[0])
            values_possible_in_v_not_other = possibilities[0] - other_possibilities
            number_possiblities_equals_number_cells = len(values_possible_in_v_not_other) == len(possibilities[1])
            impossible_in_vector = possibilities[0] - values_possible_in_v_not_other
            if number_possiblities_equals_number_cells:
               for impossible_value in impossible_in_vector:
                  for c in possibilities[1]:
                     c.add_impossible_value(impossible_value, message='vectors_within_blk')

   def set_values(self):
      for cell in self.puzzle:
         if cell.value:
            continue
         for entity_type in Entity:
            self.solve_for_values_with_only_one_cell_left(cell, entity_type)
            self.solve_for_cells_with_only_one_value_left(cell, entity_type)

   def solve_for_values_with_only_one_cell_left(self, cell, entity_type):
      entity_cells = self.get_ent(cell.ent(entity_type), entity_type)
      unsolved_cells = [c for c in entity_cells if c.value is None]
      entity_values = set([c.value for c in entity_cells if c.value]) 
      missing_values = all_values - entity_values
      for missing_value in missing_values:
         cells_possibly_containing_missing_values = [c for c in unsolved_cells if missing_value in c.possible_values()]
         if len(cells_possibly_containing_missing_values) != 1:
            continue
         c = next(iter(cells_possibly_containing_missing_values))
         c.value = missing_value
         if self.verbose:
            print(f"\tSOLVED: {entity_type.name}:{cell.ent(entity_type)} r{c.row}c{c.col} = {c.value} (only_one_cell_left)")

   def solve_for_cells_with_only_one_value_left(self, cell, entity_type):
      entity_cells = self.get_ent(cell.ent(entity_type), entity_type)
      entity_values = set([c.value for c in entity_cells if c.value]) 
      unsolved_cells = [c for c in entity_cells if c.value is None]
      missing_values = all_values - entity_values
      for c in unsolved_cells:
         if len(c.possible_values()) == 1:
            c.value = c.possible_values().pop()
            if self.verbose:
               print(f"\tSOLVED: {entity_type.name}:{cell.ent(entity_type)} r{c.row}c{c.col} = {c.value} (only_one_value_left)")

   def print_puzzle(self):
      # This is borrowed code from:
      """https://tio.run/##dY9dSsQwEMff9xQhsJA0g9Tt7nZd8Ca@pB/gQre2pcr2TTyBQgdBEEVF8eMInmYuUrOpKX1QmGQy//nNP0nR1KdnedB15XGmt1Gi2Q6a9U41yq5J5WQNEcSQQLrWqhSliLwAYgmJVKniJzmfFNUmr4UQlfA4YUt4TfhC@Ep4y6UdMfINmyaM2qtR4l6g9h3jAf3sA7WX1H4TfhI@cSl/5Udr@UH4RfhsZNXLd1Z@I3wnvDfyNL3QmdjkxXktpJQHVVpkOk4N6zPT7jrhA1sC810cATsENnflDNjKnXtsASy0mG@xmeX9vyJwfF@uRvsw3l8xwAPwn@fC8qF7z9KRoQPmI6vQ8uPf7WH5Aw"""
      q=lambda x,y:x+y+x+y+x
      r=lambda a,b,c,d,e:a+q(q(b*3,c),d)+e+"\n"
      print_input = tuple([0 if x==None else int(x) for x in [c.value for c in self.puzzle]])
      print(((r(*"╔═╤╦╗")+q(q("║ %d │ %d │ %d "*3+"║\n",r(*"╟─┼╫╢")),r(*"╠═╪╬╣"))+r(*"╚═╧╩╝"))%print_input).replace(*"0 "))

   def print_specific_cell_info(self, cell_ids):
      for cell in self.puzzle:
         if f"{cell.row}{cell.col}" in cell_ids:
            print(f"cell_info: {cell.id} possible: {cell.possible_values()}")

   def validate_board(self):
      valid = True
      for entity_type in Entity:
         ent_ids = set([c.ent(entity_type) for c in self.puzzle])
         all_of_ent_type = [self.get_ent(ent_id, entity_type) for ent_id in ent_ids]
         for ent in all_of_ent_type:
            for cell in ent:
               if cell.value is None:
                  continue
               ent_cells_with_value = [c for c in ent if c.value == cell.value and c.id != cell.id]
               if len(ent_cells_with_value) != 0:
                  ex_c = ent_cells_with_value[0]
                  print(f" ! THIS SOLUTION IS INCORRECT ! {ex_c.id}={ex_c.value} {cell.id}={cell.value}")
                  valid = False
      if valid and self.verbose:
         print("Board Values Are Valid.")

if __name__ == '__main__':
   SudokuSolver()
