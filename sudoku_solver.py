import sys
import math
import argparse
import inspect
from enum import Enum
from big_board import big_board
from functools import wraps
from itertools import chain, combinations
from collections import defaultdict
from collections.abc import Callable
from typing import Any


def solver(func: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method as a solver that can be disabled from the CLI."""

    @wraps(func)
    def wrapper(self: "SudokuSolver", *args: Any, **kwargs: Any) -> Any:
        if func.__name__ in self.disabled_solvers:
            return None

        return func(self, *args, **kwargs)

    wrapper._is_solver = True  # type: ignore[attr-defined]
    return wrapper


HouseType = Enum("House", "row col blk")
ALL_VALUES = set(["1", "2", "3", "4", "5", "6", "7", "8", "9"])


class House:
    _instances = {}

    def __new__(
        cls,
        house_type: HouseType,
        house_id: int,
        *args,
        **kwargs,
    ):
        key = (house_type, house_id)

        if key not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[key] = instance
            instance._initialized = False

        return cls._instances[key]

    def __init__(
        self,
        house_type: HouseType,
        house_id: int,
        cell: SudokuCell,
    ):
        if not self._initialized:
            self._initialized = True
            self.house_type = house_type
            self.house_id = house_id
            self.solved_cells = set()
            self.unsolved_cells = set()
            self.unsolved_values = ALL_VALUES.copy()

        self.update_manifest(cell)

    @property
    def id_(self) -> str:
        return f"{self.house_type.value}_{self.house_id}"

    def __repr__(self) -> str:
        return self.id_

    def update_manifest(self, cell: SudokuCell) -> None:

        if cell.value:
            self.unsolved_cells.discard(cell)
            self.solved_cells.add(cell)
            self.unsolved_values.discard(cell.value)
        else:
            self.unsolved_cells.add(cell)


class SudokuCell:

    def __init__(self, value, idx):
        if value == "_":
            value = None
            self.is_given = False
        else:
            self.is_given = True
        self._value = value  # bypasses the value.setter function on purpose here
        self.set_coordinates(idx)
        self.row = House(house_type=HouseType.row, house_id=self.row_id, cell=self)
        self.column = House(house_type=HouseType.col, house_id=self.col_id, cell=self)
        self.block = House(house_type=HouseType.blk, house_id=self.block_id, cell=self)
        self.impossible_values = ALL_VALUES - {self._value} if self._value else set()
        if self._value:
            self.mark_solved_in_houses()

    def set_coordinates(self, idx):
        self.row_id = math.ceil((idx + 1) / 9)
        self.col_id = int(str(idx / 9).split(".")[-1][0]) + 1
        blk_col_1 = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3, 9: 3}
        blk_col_2 = {1: 4, 2: 4, 3: 4, 4: 5, 5: 5, 6: 5, 7: 6, 8: 6, 9: 6}
        blk_col_3 = {1: 7, 2: 7, 3: 7, 4: 8, 5: 8, 6: 8, 7: 9, 8: 9, 9: 9}
        blk_lookup = {
            1: blk_col_1,
            2: blk_col_1,
            3: blk_col_1,
            4: blk_col_2,
            5: blk_col_2,
            6: blk_col_2,
            7: blk_col_3,
            8: blk_col_3,
            9: blk_col_3,
        }
        self.block_id = blk_lookup[self.row_id][self.col_id]
        self.id_ = f"r{self.row_id}c{self.col_id}_b{self.block_id}"

    def get_house_id(self, house_type: HouseType):
        if house_type is HouseType.row:
            return self.row_id
        elif house_type is HouseType.col:
            return self.col_id
        elif house_type is HouseType.blk:
            return self.block_id

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, submitted_value: str):
        """
        This setter function is not used when initializing the cell object.
        It is only called externally by a solver.
        """
        if (submitted_value in self.impossible_values) or (
            submitted_value not in ALL_VALUES
        ):
            raise ValueError(f"value: {submitted_value} is not possible for {self}")
        self._value = submitted_value
        self.impossible_values = ALL_VALUES - set([self._value])
        self.mark_solved_in_houses()

    def mark_solved_in_houses(self):
        self.row.update_manifest(self)
        self.column.update_manifest(self)
        self.block.update_manifest(self)

    def remove_candidate(self, candidate_value):
        if candidate_value not in self.impossible_values:
            self.impossible_values.add(candidate_value)
            progress_made = True
        else:
            progress_made = False
        return progress_made

    @property
    def possible_values(self) -> set[str]:
        if self._value:
            return set([self._value])
        else:
            return ALL_VALUES - self.impossible_values

    def __repr__(self):
        return self.id_


class SudokuSolver:
    puzzle_file_path: str
    display_unsolved_puzzle: bool
    silent: bool
    disabled_solvers: set[str]

    def __init__(self, args=[]):
        argv = args if args else sys.argv[1::]
        parser = argparse.ArgumentParser()
        parser.add_argument("--puzzle-file-path", type=str, required=True)
        parser.add_argument("--display-unsolved-puzzle", action="store_true")
        parser.add_argument("--silent", action="store_true")
        solver_names = self._get_solver_names()
        for solver_name in solver_names:
            parser.add_argument(
                f"--disable-{solver_name.replace('_', '-')}",
                action="store_true",
            )
        parser.parse_args(argv, self)
        self.disabled_solvers = {
            solver_name
            for solver_name in solver_names
            if getattr(self, f"disable_{solver_name}")
        }
        self.import_puzzle()
        if self.display_unsolved_puzzle is False:
            self.solve_puzzle()

    @classmethod
    def _get_solver_names(cls) -> list[str]:
        return [
            name
            for name, member in inspect.getmembers(cls)
            if getattr(member, "_is_solver", False)
        ]

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
        print(self.get_puzzle_string())
        print(self.puzzle_file_str)

    def making_progress(self):
        self.loops += 1
        self.print_progress()
        enter_loop = self.progress_made
        self.progress_made = False
        return enter_loop

    def print_progress(self):
        if not self.silent:
            print(
                f"Current Loop: {self.loops}  Remaining Cells: {len(self.puzzle_unsolved_cell_by_id)}"
            )

    def import_puzzle(self):
        self.puzzle_all_cells: list[SudokuCell] = []
        self.puzzle_by_cell_id: dict[str, SudokuCell] = {}
        self.puzzle_unsolved_cell_by_id: dict[str, SudokuCell] = {}
        self.puzzle_by_row_id = defaultdict(list)
        self.puzzle_by_col_id = defaultdict(list)
        self.puzzle_by_block_id = defaultdict(list)
        self.puzzle_house_indexes = {
            HouseType.row: self.puzzle_by_row_id,
            HouseType.col: self.puzzle_by_col_id,
            HouseType.blk: self.puzzle_by_block_id,
        }

        with open(self.puzzle_file_path, "r") as f:
            self.puzzle_file_str = f.read().strip()

        for idx, char in enumerate(self.puzzle_file_str):
            cell = SudokuCell(char, idx)
            self.puzzle_all_cells.append(cell)
            self.puzzle_by_cell_id[f"{cell.row_id}{cell.col_id}"] = cell
            self.puzzle_by_row_id[cell.row_id].append(cell)
            self.puzzle_by_col_id[cell.col_id].append(cell)
            self.puzzle_by_block_id[cell.block_id].append(cell)
            if not cell.value:
                self.puzzle_unsolved_cell_by_id[cell.id_] = cell
        print(self.small_board())

    def set_impossible_values(self):
        for cell in list(self.puzzle_unsolved_cell_by_id.values()):
            if cell.value:
                continue

            self.already_in_house(
                cell, self.get_house(cell.row_id, HouseType.row), HouseType.row
            )
            self.already_in_house(
                cell, self.get_house(cell.col_id, HouseType.col), HouseType.col
            )
            self.already_in_house(
                cell, self.get_house(cell.block_id, HouseType.blk), HouseType.blk
            )

            self.x_wing(cell)

        for house_type in HouseType:
            for id in range(1, 10):
                house = self.get_house(id, house_type)
                empty_cells = [c for c in house if c.value is None]
                for group, other_cells in self.get_powerset(empty_cells):
                    self.shared_hidden_values(group, other_cells)
                    self.shared_naked_values(group, other_cells)

        for blk in set([cell.block_id for cell in self.puzzle_all_cells]):
            self.check_vector_beyond_block(blk)
            self.check_subvectors_within_blk(blk)

    def get_house(self, house_id: int, house_type: HouseType) -> list[SudokuCell]:
        return self.puzzle_house_indexes[house_type][house_id]

    def get_house_empty_cells(
        self, house_id: int, house_type: HouseType
    ) -> list[SudokuCell]:
        return [
            cell
            for cell in self.puzzle_house_indexes[house_type][house_id]
            if cell.value is None
        ]

    @solver
    def already_in_house(self, cell: SudokuCell, house, house_type: HouseType):
        for see_cell in house:
            if see_cell.value is None:
                continue
            else:
                self.eliminate_candidate(
                    cell=cell,
                    candidate_value=see_cell.value,
                    message=f"{see_cell = } can see {cell.value} in {cell}",
                    explicit_silent=False,
                )

    def eliminate_candidate(
        self,
        cell: SudokuCell,
        candidate_value,
        message=None,
        print_board=False,
        explicit_silent=False,
    ):
        if progress_made := cell.remove_candidate(candidate_value):
            self.progress_made = progress_made
            if message and not (self.silent or explicit_silent):
                print(
                    f"Eliminated candidate: {candidate_value} from r{cell.row_id}c{cell.col_id} ({message})"
                )
            if print_board and not self.silent:
                print(self)  # To help develop new logic to solve harder puzzles

            if len(possible_values := cell.possible_values) == 1:
                last_value = possible_values.pop()
                self.assign_cell_value(
                    cell=cell,
                    value=last_value,
                    msg=f"\tsolved: {cell.id_} = {last_value} (naked single)",
                )

    @solver
    def x_wing(self, cell: SudokuCell):
        if cell.value or 9 in (cell.row_id, cell.col_id):
            return
        for value_intersection, x_list, outer_empty_cells in self.x_sets(cell):
            message = f"x_wing: {sorted([c.id_ for c in x_list])}"
            for c in outer_empty_cells:
                self.eliminate_candidate(c, value_intersection, message)

    def x_sets(self, top_left):
        empty_cells_in_col = (
            c
            for c in self.get_house_empty_cells(top_left.col, HouseType.col)
            if c.row_id > top_left.row
        )
        empty_cells_in_row = [
            c
            for c in self.get_house_empty_cells(top_left.row, HouseType.row)
            if c.col_id > top_left.col
        ]
        for bottom_left in empty_cells_in_col:
            for top_right in empty_cells_in_row:
                bottom_right = self.puzzle_by_cell_id[
                    f"{bottom_left.row_id}{top_right.col_id}"
                ]
                if bottom_right.value:
                    continue
                x_list = sorted(
                    [top_left, bottom_left, top_right, bottom_right],
                    key=lambda x: len(x.possible_values),
                )
                if len(x_list[0].possible_values) != 2:
                    continue
                if len(x_list[1].possible_values) != 2:
                    continue
                if (
                    x_list[0].row_id is not x_list[1].row_id
                    and x_list[0].col_id is not x_list[1].col_id
                ):
                    continue
                value_intersection = set.intersection(
                    *[c.possible_values for c in x_list]
                )
                if len(value_intersection) != 1:
                    continue
                value_intersection = value_intersection.pop()
                x_ids = [c.id_ for c in x_list]

                rows_candidates = [
                    c
                    for c in self.get_house_empty_cells(top_left.row, HouseType.row)
                    if c.id_ not in x_ids and value_intersection in c.possible_values
                ]
                [
                    rows_candidates.append(c)
                    for c in self.get_house_empty_cells(
                        bottom_left.row_id, HouseType.row
                    )
                    if c.id_ not in x_ids and value_intersection in c.possible_values
                ]
                cols_candidates = [
                    c
                    for c in self.get_house_empty_cells(top_left.col, HouseType.col)
                    if c.id_ not in x_ids and value_intersection in c.possible_values
                ]
                [
                    cols_candidates.append(c)
                    for c in self.get_house_empty_cells(
                        bottom_right.col_id, HouseType.col
                    )
                    if c.id_ not in x_ids and value_intersection in c.possible_values
                ]

                if not cols_candidates and rows_candidates:
                    yield (value_intersection, x_list, rows_candidates)
                elif not rows_candidates and cols_candidates:
                    yield (value_intersection, x_list, cols_candidates)

    @solver
    def shared_hidden_values(self, grp, other_cells):
        # For strategy explanation, see https://www.learn-sudoku.com/hidden-pairs.html
        grp_size = {2: "double", 3: "triple", 4: "quadruple"}
        if len(other_cells) == 0:
            outside_values = set()
        else:
            outside_values = set.union(*[cell.possible_values for cell in other_cells])
        for combo in combinations(grp, 2):
            value_intersection = set.intersection(
                *[cell.possible_values - outside_values for cell in combo]
            )
            if len(value_intersection) >= len(grp):
                shared_hidden_group = [c for c in combo]
                last_grp_members = [c for c in grp if c not in combo]
                for c in last_grp_members:
                    mbr_intersect = value_intersection.intersection(c.possible_values)
                    if len(mbr_intersect) >= len(value_intersection) - 1:
                        shared_hidden_group.append(c)
                for cell in shared_hidden_group:
                    for value in outside_values:
                        self.eliminate_candidate(
                            cell, value, f"hidden {grp_size[len(shared_hidden_group)]}"
                        )

    @solver
    def shared_naked_values(self, grp, other_cells):
        # For strategy explanation, see: https://www.learn-sudoku.com/naked-pairs.html
        grp_size = {2: "double", 3: "triple", 4: "quadruple"}
        value_union = set.union(*[cell.possible_values for cell in grp])
        for c in other_cells:
            if c.possible_values.issubset(value_union):
                return  # a future set will include this other_cell as a grp member
        if len(value_union) == len(grp):
            for cell in other_cells:
                for value in value_union:
                    self.eliminate_candidate(cell, value, f"naked {grp_size[len(grp)]}")

    def get_powerset(self, empty_cells):
        for group in self.powerset(empty_cells):
            if len(group) not in (2, 3, 4):
                continue
            other_cells = [c for c in empty_cells if c not in group]
            yield (group, other_cells)

    def powerset(self, iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

    @solver
    def check_vector_beyond_block(self, blk):
        all_blk_cells = self.get_house(blk, HouseType.blk)
        blk_cells_without_values = [c for c in all_blk_cells if c.value is None]
        if len(blk_cells_without_values) == 0:
            return
        for house_type in [HouseType.row, HouseType.col]:
            e_range = set(
                [c.get_house_id(house_type) for c in all_blk_cells if c.value is None]
            )
            empty_vectors_possibilities = {v: set([]) for v in e_range}
            for c in blk_cells_without_values:
                empty_vectors_possibilities[c.get_house_id(house_type)].update(
                    c.possible_values
                )
            for vector, possibilities in empty_vectors_possibilities.items():
                other_possibilities = set()
                for other_vect, other_pos in empty_vectors_possibilities.items():
                    if other_vect != vector:
                        other_possibilities.update(other_pos)
                difference = possibilities - other_possibilities
                cells_in_vector_beyond_blk = [
                    c
                    for c in self.get_house_empty_cells(vector, house_type)
                    if c.block_id != blk
                ]
                for value in difference:
                    for c in cells_in_vector_beyond_blk:
                        self.eliminate_candidate(
                            c, value, message="vector beyond block"
                        )

    @solver
    def check_subvectors_within_blk(self, blk):
        all_blk_cells = self.get_house(blk, HouseType.blk)
        blk_cells_without_values = [c for c in all_blk_cells if c.value is None]
        if len(blk_cells_without_values) == 0:
            return
        for house_type in [HouseType.row, HouseType.col]:
            e_range = set(
                [c.get_house_id(house_type) for c in all_blk_cells if c.value is None]
            )
            empty_vectors_possibilities = {v: [set(), []] for v in e_range}
            for c in blk_cells_without_values:
                empty_vectors_possibilities[c.get_house_id(house_type)][0].update(
                    c.possible_values
                )
                empty_vectors_possibilities[c.get_house_id(house_type)][1].append(c)
            for vector, possibilities in empty_vectors_possibilities.items():
                other_possibilities = set()
                for other_vect, other_pos in empty_vectors_possibilities.items():
                    if other_vect != vector:
                        other_possibilities.update(other_pos[0])
                values_possible_in_v_not_other = possibilities[0] - other_possibilities
                number_possiblities_equals_number_cells = len(
                    values_possible_in_v_not_other
                ) == len(possibilities[1])
                impossible_in_vector = possibilities[0] - values_possible_in_v_not_other
                if number_possiblities_equals_number_cells:
                    for impossible_value in impossible_in_vector:
                        for c in possibilities[1]:
                            self.eliminate_candidate(
                                c, impossible_value, message="vectors within block"
                            )

    def set_values(self):
        for cell in self.puzzle_all_cells:
            if cell.value:
                continue
            for house_type in HouseType:
                self.hidden_singles(cell, house_type)
                self.naked_singles(cell, house_type)

    def assign_cell_value(self, cell: SudokuCell, value: str, msg=None):
        if cell.value:
            print(f"Already solved: {cell.id_} = {value}, probably by propogation")
            return

        try:
            cell.value = value
        except ValueError:
            print(self)
            raise

        if not self.silent:
            print(msg)

        del self.puzzle_unsolved_cell_by_id[cell.id_]
        self.progress_made = True
        if self.puzzle_solved():
            raise self.PuzzleSolved

        self.eliminate_candidate_from_sees(cell)
        self.propogate_hidden_singles(cell)

    def eliminate_candidate_from_sees(self, cell: SudokuCell):
        """
        How do we do already_in_house eliminations in a propogating sort of way?
        At cell value assignment, do we iterate over each house cell and add the impossible
        value? I think
        """
        for see_cell in chain(
            self.get_house_empty_cells(cell.row_id, HouseType.row),
            self.get_house_empty_cells(cell.col_id, HouseType.col),
            self.get_house_empty_cells(cell.block_id, HouseType.blk),
        ):
            self.eliminate_candidate(
                cell=see_cell,
                candidate_value=cell.value,
                message=f"{see_cell = } can see {cell.value} in {cell}",
            )

    def propogate_hidden_singles(self, cell: SudokuCell):
        """
        Function gets run whenever a cell is assigned in order to check for
        downstream affects as is often the case.
        """
        if len(cell.row.unsolved_cells) == 1:
            last_cell_in_row = next(iter(cell.row.unsolved_cells))
            remaining_unsolved_value = cell.row.unsolved_values.pop()
            self.assign_cell_value(
                last_cell_in_row,
                remaining_unsolved_value,
                msg=f"\tsolved: {last_cell_in_row.id_} = {remaining_unsolved_value} (hidden single {HouseType.row}:{last_cell_in_row.row_id})",
            )

    def puzzle_solved(self):
        return len(self.puzzle_unsolved_cell_by_id) == 0

    def hidden_singles(self, cell: SudokuCell, house_type: HouseType):
        house_cells = self.get_house(cell.get_house_id(house_type), house_type)
        unsolved_cells = [c for c in house_cells if c.value is None]
        house_values = set([c.value for c in house_cells if c.value])
        missing_values = ALL_VALUES - house_values
        for missing_value in missing_values:
            cells_possibly_containing_missing_values = [
                c for c in unsolved_cells if missing_value in c.possible_values
            ]
            if len(cells_possibly_containing_missing_values) != 1:
                continue
            c = cells_possibly_containing_missing_values[0]
            msg = f"\tSOLVED: r{c.row_id}c{c.col_id} = {missing_value} (hidden single {house_type.name}:{cell.get_house_id(house_type)})"
            self.assign_cell_value(c, missing_value, msg)

    def naked_singles(self, cell, house_type: HouseType):
        house_cells = self.get_house(cell.get_house_id(house_type), house_type)
        unsolved_cells = [c for c in house_cells if c.value is None]
        for c in unsolved_cells:
            if len(possible_values := c.possible_values) == 1:
                remaining_value = possible_values.pop()
                msg = f"\tSOLVED: r{c.row_id}c{c.col_id} = {remaining_value} (naked single)"
                self.assign_cell_value(c, remaining_value, msg)

    def get_puzzle_string(self) -> str:
        return "".join(obj.value or "_" for obj in self.puzzle_all_cells)

    def __str__(self):
        if not self.puzzle_solved():
            return big_board.render(self.puzzle_all_cells)
        else:
            return self.small_board()

    def small_board(self):
        # This is borrowed code from:
        """https://tio.run/##dY9dSsQwEMff9xQhsJA0g9Tt7nZd8Ca@pB/gQre2pcr2TTyBQgdBEEVF8eMInmYuUrOpKX1QmGQy//nNP0nR1KdnedB15XGmt1Gi2Q6a9U41yq5J5WQNEcSQQLrWqhSliLwAYgmJVKniJzmfFNUmr4UQlfA4YUt4TfhC@Ep4y6UdMfINmyaM2qtR4l6g9h3jAf3sA7WX1H4TfhI@cSl/5Udr@UH4RfhsZNXLd1Z@I3wnvDfyNL3QmdjkxXktpJQHVVpkOk4N6zPT7jrhA1sC810cATsENnflDNjKnXtsASy0mG@xmeX9vyJwfF@uRvsw3l8xwAPwn@fC8qF7z9KRoQPmI6vQ8uPf7WH5Aw"""

        def q(x, y):
            return x + y + x + y + x

        def r(a, b, c, d, e):
            return a + q(q(b * 3, c), d) + e + "\n"

        print_input = tuple(
            [
                0 if x is None else int(x)
                for x in [c.value for c in self.puzzle_all_cells]
            ]
        )
        return (
            (
                (
                    r(*"╔═╤╦╗")
                    + q(q("║ %d │ %d │ %d " * 3 + "║\n", r(*"╟─┼╫╢")), r(*"╠═╪╬╣"))
                    + r(*"╚═╧╩╝")
                )
                % print_input
            )
            .replace(*"0 ")
            .strip()
        )

    def validate_board(self):
        self.valid_board = True
        for house_type in HouseType:
            house_ids = set([c.get_house_id(house_type) for c in self.puzzle_all_cells])
            all_of_house_type = [
                self.get_house(house_id, house_type) for house_id in house_ids
            ]
            for house in all_of_house_type:
                for cell in house:
                    if cell.value is None or cell.is_given:
                        continue
                    house_cells_with_value = [
                        c for c in house if c.value == cell.value and c.id_ != cell.id_
                    ]
                    if len(house_cells_with_value) != 0:
                        ex_c = house_cells_with_value[0]
                        print(
                            f" ! THIS SOLUTION IS INCORRECT ! {ex_c.id_}={ex_c.value} {cell.id_}={cell.value}"
                        )
                        self.valid_board = False
        if self.valid_board and not self.silent:
            print("Board Values Are Valid.")


if __name__ == "__main__":
    SudokuSolver()
