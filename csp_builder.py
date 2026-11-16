from enum import Enum
from typing import List, Dict, Generic, Tuple
from abc import ABC, abstractmethod




# Wertebereich für Zellen im Gitter
class Domain(Enum):
    EMPTY = 0
    HORIZONTAL_LINE = 1
    VERTICAL_LINE = 2
    CIRCLE = 3

# Schwierigkeit des Gitters
class Difficulty(Enum):
    MEDIUM = 0
    HARD = 1

    
# Constraint zwischen Variablen
class Constraint(ABC):
    def __init__(self, variables: List):
        self.variables = variables

    @abstractmethod
    def satisfied(self, assignment: Dict) -> bool:

class adjacentCellConstraint(Constraint):
    def __init__(self, cell: Tuple[int, int]) -> None:
        x = cell[0]
        y = cell[1]
        self.cell = cell
        self.cell_above = (x, y + 1)
        self.cell_below = (x, y - 1)
        self.cell_left = (x - 1, y)
        self.cell_right = (x + 1, y)
        super().__init__([cell,self.cell_above, self.cell_below, self.cell_left, self.cell_right])

    def consistent(self, assignment: Dict) -> bool:
        match assignment[self.cell]:
            case "EMPTY":
                pass
            case "HORIZONTAL_LINE":
                if self.cell_above in assignment and assignment[self.cell_above] != "EMPTY":
                    return False
                if self.cell_below in assignment and assignment[self.cell_below] != "EMPTY":
                    return False
                if self.cell_left in assignment:
                    if assignment[self.cell_left] == "VERTICAL_LINE" or assignment[self.cell_left] == "HORIZONTAL_LINE":
                        return False
                if self.cell_right in assignment:
                    if assignment[self.cell_right] == "VERTICAL_LINE" or assignment[self.cell_right] == "HORIZONTAL_LINE":
                        return False
                if self.cell_right in assignment and self.cell_left in assignment:
                    if assignment[self.cell_left] == assignment[self.cell_right]:
                        return False

            case "VERTICAL_LINE":
                if self.cell_right in assignment and assignment[self.cell_right] != "EMPTY":
                    return False
                if self.cell_left in assignment and assignment[self.cell_left] != "EMPTY":
                    return False
                if self.cell_above in assignment:
                    if assignment[self.cell_above] == "VERTICAL_LINE" or assignment[self.cell_above] == "HORIZONTAL_LINE":
                        return False
                if self.cell_below in assignment:
                    if assignment[self.cell_below] == "VERTICAL_LINE" or assignment[self.cell_below] == "HORIZONTAL_LINE":
                        return False
                if self.cell_above in assignment and self.cell_below in assignment:
                    if assignment[self.cell_above] == assignment[self.cell_below]:
                        return False
            case "CIRCLE":
                if self.cell_right in assignment:



class LollipopGitter():
    def __init__(self, size : int):
        self.variables = list() # Liste der Zellen im Gitter
        for i in range(size):
            for j in range(size):
                self.variables.append((i, j)) #
        self.domains = {V : list(Domain) for V in self.variables}   # Dict Mapping aller Zellen auf ihren Wertebereich
        self.constraints = {}
        for variable in self.variables:
            self.constraints[variable] = []
            if variable not in self.domains:
                raise LookupError("Every variable should have a domain assigned to it.")

    def add_constraint(self, constraint: Constraint) -> None:
        for variable in constraint.variables:
            if variable not in self.variables:
                raise LookupError("Variable in constraint not in CSP")
            else:
                self.constraints[variable].append(constraint)

    def consistent(self, variable: int, assignment: Dict) -> bool:
        for constraint in self.constraints[variable]:
            if not constraint.satisfied(assignment):
                return False
        return True

    def build_puzzle(self, difficulty: Difficulty) -> None:
        self.add_constraint(self, Constraint)

