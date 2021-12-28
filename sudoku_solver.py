import sys
import math
import argparse
from enum import Enum
from big_board import big_board
from itertools import chain, combinations
from collections import defaultdict

Entity = Enum('Entity', 'row col blk')
all_values = set([str(i) for i in range(1, 10)])


class SudokuSolver:

    def __init__(self, args=[]):
        argv = args if args else sys.argv[1::]
        parser = argparse.ArgumentParser(argv)
        parser.add_argument('--puzzle-file-path', type=str, required=True)
        parser.add_argument('--display-unsolved-puzzle', action='store_true')
        parser.add_argument('--silent', action='store_true')
        parser.parse_args(argv, self)

        self.import_puzzle()
        if self.display_unsolved_puzzle is False:
            self.solve_puzzle()

    class PuzzleSolved(Exception):
        pass

    def solve_puzzle(self):
        try:
            self.loops = 0
            self.progress_made = True
            while self.making_progress():
                self.set_impossible_values()
                self.set_values()
        except self.PuzzleSolved:
            self.print_progress()
        self.validate_board()
        print(self)

    def making_progress(self):
        self.loops += 1
        self.print_progress()
        enter_loop = self.progress_made
        self.progress_made = False
        return enter_loop

    def print_progress(self):
        if not self.silent:
            print(f"Current Loop: {self.loops}  Remaining Cells: {self.unsolved_cell_count}")

    def import_puzzle(self):
        self.puzzle = []
        self.puzzle_by_id = {}
        self.puzzle_by_row = defaultdict(list)
        self.puzzle_by_col = defaultdict(list)
        self.puzzle_by_blk = defaultdict(list)
        self.puzzle_ent = {Entity.row: self.puzzle_by_row, Entity.col: self.puzzle_by_col, Entity.blk: self.puzzle_by_blk}
        self.unsolved_cell_count = 0

        file_str = open(self.puzzle_file_path, 'r').read().strip()
        for idx, char in enumerate(file_str):
            cell = self.SudokuCell(char, idx)
            self.puzzle.append(cell)
            self.puzzle_by_id[f"{cell.row}{cell.col}"] = cell
            self.puzzle_by_row[cell.row].append(cell)
            self.puzzle_by_col[cell.col].append(cell)
            self.puzzle_by_blk[cell.blk].append(cell)
            if not cell.value:
                self.unsolved_cell_count += 1
        print(self.small_board())

    class SudokuCell:

        def __init__(self, value, idx):
            if value == '_':
                value = None
            self._value = value
            self.set_coordinates(idx)
            if self._value:
                self.impossible_values = all_values - set([self._value])
            else:
                self.impossible_values = set()

        def set_coordinates(self, idx) -> int:
            self.row = math.ceil((idx + 1) / 9)
            self.col = int(str(idx / 9).split('.')[-1][0]) + 1
            blk_col_1 = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3, 9: 3}
            blk_col_2 = {1: 4, 2: 4, 3: 4, 4: 5, 5: 5, 6: 5, 7: 6, 8: 6, 9: 6}
            blk_col_3 = {1: 7, 2: 7, 3: 7, 4: 8, 5: 8, 6: 8, 7: 9, 8: 9, 9: 9}
            blk_lookup = {1: blk_col_1,
                          2: blk_col_1,
                          3: blk_col_1,
                          4: blk_col_2,
                          5: blk_col_2,
                          6: blk_col_2,
                          7: blk_col_3,
                          8: blk_col_3,
                          9: blk_col_3}
            self.blk = blk_lookup[self.row][self.col]
            self.id = f"r{self.row}c{self.col}_b{self.blk}"

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

    def set_impossible_values(self):
        for cell in self.puzzle:
            if cell.value:
                continue
            self.impossible_in_entity(cell, self.get_ent(cell.row, Entity.row), Entity.row)
            self.impossible_in_entity(cell, self.get_ent(cell.col, Entity.col), Entity.col)
            self.impossible_in_entity(cell, self.get_ent(cell.blk, Entity.blk), Entity.blk)
            self.x_wing(cell)

        for entity_type in Entity:
            for ent_id in range(1, 10):
                entity = self.get_ent(ent_id, entity_type)
                empty_cells = [c for c in entity if c.value is None]
                for grp, other_cells in self.get_powerset(empty_cells):
                    self.shared_hidden_values(grp, other_cells)
                    self.shared_naked_values(grp, other_cells)

        for blk in set([cell.blk for cell in self.puzzle]):
            self.check_vector_beyond_blk(blk)
            self.check_subvectors_within_blk(blk)

    def get_ent(self, entity_id, entity_type, empty_only=False):
        return [cell for cell in self.puzzle_ent[entity_type][entity_id] if ((empty_only and cell.value is None) or not empty_only)]

    def impossible_in_entity(self, cell, entity, entity_type):
        for other_cell in entity:
            if (other_cell.value is None):
                continue
            else:
                self.assign_cell_impossible_value(cell, other_cell.value, entity_type.name)

    def assign_cell_impossible_value(self, cell, impossible_value, message=None, print_board=False):
        if impossible_value not in cell.impossible_values:
            cell.impossible_values.add(impossible_value)
            self.progress_made = True
            if message and not self.silent:
                print(f"\tIMPOSSIBLE: r{cell.row}c{cell.col} != {impossible_value} ({message})")
            if print_board and not self.silent:
                print(self)  # To help develop new logic to solve harder puzzles

    def x_wing(self, cell):
        if cell.value or 9 in (cell.row, cell.col):
            return
        for value_intersection, x_list, outer_empty_cells in self.x_sets(cell):
            message = f"x_wing: {sorted([c.id for c in x_list])}"
            for c in outer_empty_cells:
                self.assign_cell_impossible_value(c, value_intersection, message)

    def x_sets(self, top_left):
        empty_cells_in_col = (c for c in self.get_ent(top_left.col, Entity.col, empty_only=True) if c.row > top_left.row)
        empty_cells_in_row = [c for c in self.get_ent(top_left.row, Entity.row, empty_only=True) if c.col > top_left.col]
        for bottom_left in empty_cells_in_col:
            for top_right in empty_cells_in_row:
                bottom_right = self.puzzle_by_id[f"{bottom_left.row}{top_right.col}"]
                if bottom_right.value:
                    continue
                x_list = sorted([top_left, bottom_left, top_right, bottom_right], key=lambda x: len(x.possible_values()))
                if len(x_list[0].possible_values()) != 2:
                    continue
                if len(x_list[1].possible_values()) != 2:
                    continue
                if x_list[0].row is not x_list[1].row and x_list[0].col is not x_list[1].col:
                    continue
                value_intersection = set.intersection(*[c.possible_values() for c in x_list])
                if len(value_intersection) != 1:
                    continue
                value_intersection = value_intersection.pop()
                x_ids = [c.id for c in x_list]

                rows_candidates = [c for c in self.get_ent(top_left.row, Entity.row, empty_only=True) if c.id not in x_ids and value_intersection in c.possible_values()]
                [rows_candidates.append(c) for c in self.get_ent(bottom_left.row, Entity.row, empty_only=True) if c.id not in x_ids and value_intersection in c.possible_values()]
                cols_candidates = [c for c in self.get_ent(top_left.col, Entity.col, empty_only=True) if c.id not in x_ids and value_intersection in c.possible_values()]
                [cols_candidates.append(c) for c in self.get_ent(bottom_right.col, Entity.col, empty_only=True) if c.id not in x_ids and value_intersection in c.possible_values()]

                if not cols_candidates and rows_candidates:
                    yield (value_intersection, x_list, rows_candidates)
                elif not rows_candidates and cols_candidates:
                    yield (value_intersection, x_list, cols_candidates)

    def shared_hidden_values(self, grp, other_cells):
        # For strategy explanation, see https://www.learn-sudoku.com/hidden-pairs.html
        grp_size = {2: "double", 3: "triple", 4: "quadruple"}
        if len(other_cells) == 0:
            outside_values = set()
        else:
            outside_values = set.union(*[cell.possible_values() for cell in other_cells])
        for combo in combinations(grp, 2):
            value_intersection = set.intersection(*[cell.possible_values() - outside_values for cell in combo])
            if len(value_intersection) >= len(grp):
                shared_hidden_group = [c for c in combo]
                last_grp_members = [c for c in grp if c not in combo]
                for c in last_grp_members:
                    mbr_intersect = value_intersection.intersection(c.possible_values())
                    if len(mbr_intersect) >= len(value_intersection) - 1:
                        shared_hidden_group.append(c)
                for cell in shared_hidden_group:
                    for value in outside_values:
                        self.assign_cell_impossible_value(cell, value, f"hidden_{grp_size[len(shared_hidden_group)]}")

    def shared_naked_values(self, grp, other_cells):
        # For strategy explanation, see: https://www.learn-sudoku.com/naked-pairs.html
        grp_size = {2: "double", 3: "triple", 4: "quadruple"}
        value_union = set.union(*[cell.possible_values() for cell in grp])
        for c in other_cells:
            if c.possible_values().issubset(value_union):
                return  # a future set will include this other_cell as a grp member
        if len(value_union) == len(grp):
            for cell in other_cells:
                for value in value_union:
                    self.assign_cell_impossible_value(cell, value, f"naked_{grp_size[len(grp)]}")

    def get_powerset(self, empty_cells):
        for grp in self.powerset(empty_cells):
            if len(grp) not in (2, 3, 4):
                continue
            other_cells = [c for c in empty_cells if c not in grp]
            yield (grp, other_cells)

    def powerset(self, iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

    def check_vector_beyond_blk(self, blk):
        all_blk_cells = self.get_ent(blk, Entity.blk)
        solved_blk_values = set([c.value for c in all_blk_cells if c.value])
        blk_cells_without_values = [c for c in all_blk_cells if c.value is None]
        if len(blk_cells_without_values) == 0:
            return
        for entity_type in [Entity.row, Entity.col]:
            e_range = set([c.ent(entity_type) for c in all_blk_cells if c.value is None])
            empty_vectors_possibilities = {v: set([]) for v in e_range}
            for c in blk_cells_without_values:
                empty_vectors_possibilities[c.ent(entity_type)].update(c.possible_values())
            for vector, possibilities in empty_vectors_possibilities.items():
                other_possibilities = set()
                for other_vect, other_pos in empty_vectors_possibilities.items():
                    if other_vect != vector:
                        other_possibilities.update(other_pos)
                difference = possibilities - other_possibilities
                cells_in_vector_beyond_blk = [c for c in self.get_ent(vector, entity_type, empty_only=True) if c.blk != blk]
                for value in difference:
                    for c in cells_in_vector_beyond_blk:
                        self.assign_cell_impossible_value(c, value, message='vector_beyond_blk')

    def check_subvectors_within_blk(self, blk):
        all_blk_cells = self.get_ent(blk, Entity.blk)
        solved_blk_values = set([c.value for c in all_blk_cells if c.value])
        blk_cells_without_values = [c for c in all_blk_cells if c.value is None]
        if len(blk_cells_without_values) == 0:
            return
        for entity_type in [Entity.row, Entity.col]:
            e_range = set([c.ent(entity_type) for c in all_blk_cells if c.value is None])
            empty_vectors_possibilities = {v: [set(), []] for v in e_range}
            for c in blk_cells_without_values:
                empty_vectors_possibilities[c.ent(entity_type)][0].update(c.possible_values())
                empty_vectors_possibilities[c.ent(entity_type)][1].append(c)
            for vector, possibilities in empty_vectors_possibilities.items():
                other_possibilities = set()
                for other_vect, other_pos in empty_vectors_possibilities.items():
                    if other_vect != vector:
                        other_possibilities.update(other_pos[0])
                values_possible_in_v_not_other = possibilities[0] - other_possibilities
                number_possiblities_equals_number_cells = len(values_possible_in_v_not_other) == len(possibilities[1])
                impossible_in_vector = possibilities[0] - values_possible_in_v_not_other
                if number_possiblities_equals_number_cells:
                    for impossible_value in impossible_in_vector:
                        for c in possibilities[1]:
                            self.assign_cell_impossible_value(c, impossible_value, message='vectors_within_blk')

    def set_values(self):
        for cell in self.puzzle:
            if cell.value:
                continue
            for entity_type in Entity:
                self.solve_for_values_with_only_one_cell_left(cell, entity_type)
                self.solve_for_cells_with_only_one_value_left(cell, entity_type)

    def assign_cell_value(self, cell, value, msg=None):
        cell.value = value
        if not self.silent:
            print(msg)
        self.unsolved_cell_count -= 1
        self.progress_made = True
        if self.puzzle_solved():
            raise self.PuzzleSolved

    def puzzle_solved(self):
        return self.unsolved_cell_count == 0

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
            msg = f"\tSOLVED: r{c.row}c{c.col} = {missing_value} (only_one_cell_left in {entity_type.name}:{cell.ent(entity_type)})"
            self.assign_cell_value(c, missing_value, msg)

    def solve_for_cells_with_only_one_value_left(self, cell, entity_type):
        entity_cells = self.get_ent(cell.ent(entity_type), entity_type)
        entity_values = set([c.value for c in entity_cells if c.value])
        unsolved_cells = [c for c in entity_cells if c.value is None]
        missing_values = all_values - entity_values
        for c in unsolved_cells:
            if len(c.possible_values()) == 1:
                remaining_value = c.possible_values().pop()
                msg = f"\tSOLVED: r{c.row}c{c.col} = {remaining_value} (only_one_value_left {entity_type.name}:{cell.ent(entity_type)})"
                self.assign_cell_value(c, remaining_value, msg)

    def __str__(self):
        if not self.puzzle_solved():
            return big_board.render(self.puzzle)
        else:
            return self.small_board()

    def small_board(self):
        # This is borrowed code from:
        """https://tio.run/##dY9dSsQwEMff9xQhsJA0g9Tt7nZd8Ca@pB/gQre2pcr2TTyBQgdBEEVF8eMInmYuUrOpKX1QmGQy//nNP0nR1KdnedB15XGmt1Gi2Q6a9U41yq5J5WQNEcSQQLrWqhSliLwAYgmJVKniJzmfFNUmr4UQlfA4YUt4TfhC@Ep4y6UdMfINmyaM2qtR4l6g9h3jAf3sA7WX1H4TfhI@cSl/5Udr@UH4RfhsZNXLd1Z@I3wnvDfyNL3QmdjkxXktpJQHVVpkOk4N6zPT7jrhA1sC810cATsENnflDNjKnXtsASy0mG@xmeX9vyJwfF@uRvsw3l8xwAPwn@fC8qF7z9KRoQPmI6vQ8uPf7WH5Aw"""
        def q(x, y): return x + y + x + y + x
        def r(a, b, c, d, e): return a + q(q(b * 3, c), d) + e + "\n"
        print_input = tuple([0 if x is None else int(x) for x in [c.value for c in self.puzzle]])
        return ((r(*"╔═╤╦╗") + q(q("║ %d │ %d │ %d " * 3 + "║\n", r(*"╟─┼╫╢")), r(*"╠═╪╬╣")) + r(*"╚═╧╩╝")) % print_input).replace(*"0 ").strip()

    def validate_board(self):
        self.valid_board = True
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
                        self.valid_board = False
        if self.valid_board and not self.silent:
            print("Board Values Are Valid.")


if __name__ == '__main__':
    SudokuSolver()
