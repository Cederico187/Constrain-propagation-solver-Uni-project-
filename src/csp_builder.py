from asyncio.windows_events import NULL
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
        pass

class AdjacentCellConstraint(Constraint):
    def __init__(self, cell: Tuple[int, int], size : int) -> None:
        x = cell[0]
        y = cell[1]
        self.cell = cell
        self.cell_above = (x, y + 1)
        self.cell_below = (x, y - 1)
        self.cell_left = (x - 1, y)
        self.cell_right = (x + 1, y)
        variables = []
        if all(0 <= ele < size for ele in self.cell_above):
            variables.append(self.cell_above)
        if all(0 <= ele < size for ele in self.cell_below):
            variables.append(self.cell_below)
        if all(0 <= ele < size for ele in self.cell_left):
            variables.append(self.cell_left)
        if all(0 <= ele < size for ele in self.cell_right):
            variables.append(self.cell_right)
        super().__init__(variables)

    def satisfied(self, assignment: Dict) -> bool:
        match assignment[self.cell]:
            case "EMPTY":
                return True
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
                left, right, above, below = 0
                if self.cell_right in assignment:
                    if assignment[self.cell_right] == "CIRCLE" or assignment[self.cell_right] == "VERTICAL_LINE" :
                        return False
                    if assignment[self.cell_right] == "HORIZONTAL_LINE":
                        right = 1
                if self.cell_left in assignment:
                    if assignment[self.cell_left] == "CIRCLE" or assignment[self.cell_left] == "VERTICAL_LINE" :
                        return False
                    if assignment[self.cell_left] == "HORIZONTAL_LINE":
                        left = 1
                if self.cell_above in assignment:
                    if assignment[self.cell_above] == "CIRCLE" or assignment[self.cell_above] == "HORIZONTAL_LINE" :
                        return False
                    if assignment[self.cell_above] == "VERTICAL_LINE":
                        above = 1
                if self.cell_below in assignment:
                    if assignment[self.cell_below] == "CIRCLE" or assignment[self.cell_below] == "HORIZONTAL_LINE" :
                        return False
                    if assignment[self.cell_below] == "VERTICAL_LINE":
                        below = 1
                if self.cell_right in assignment and self.cell_left in assignment and self.cell_above in assignment and self.cell_below in assignment:
                    if left + right + above + below != 1:
                        return False
        return True


class RowColumnConstraint(Constraint):
    def __init__(self, cell : Tuple[int,int], size: int) -> None:
        self.cell = cell
        self.row = cell[0]
        self.column = cell[1]
        self.size = size
        super().__init__([(self.row,j) for j in range(self.size)] + [(i,self.column) for i in range(self.size)])

    def satisfied(self, assignment: Dict) -> bool:
        value = assignment[self.cell]
        error = False
        sightbreak = False
        last_cell = None
        for i in range(self.row,self.size):
            current_cell = (self.row,i)
            while current_cell in assignment:
                if assignment[current_cell] != value and assignment[current_cell] != "EMPTY":
                    sightbreak = True
                last_cell = current_cell

        if last_cell != None:
            if assignment[last_cell] == value:
                if (sightbreak ==False):
                    error = 1


        sightbreak = False
        last_cell = None
        for i in reversed(range(self.row)):
            current_cell = (self.row, i)
            while current_cell in assignment:
                if assignment[current_cell] != value and assignment[current_cell] != "EMPTY":
                    sightbreak = True
                last_cell = current_cell
        if last_cell != None:
            if assignment[last_cell] == value:
                if sightbreak == False:
                    error = 1

        sightbreak = False
        last_cell = None
        for i in range(self.column, self.size):
            current_cell = (i, self.column)
            while current_cell in assignment:
                if assignment[current_cell] != value and assignment[current_cell] != "EMPTY":
                    sightbreak = True
                last_cell = current_cell
        if last_cell != None:
            if assignment[last_cell] == value:
                if (sightbreak == False):
                    error = 1

        sightbreak = False
        last_cell = None
        for i in reversed(range(self.column)):
            current_cell = (i,self.column)
            while current_cell in assignment:
                if assignment[current_cell] != value and assignment[current_cell] != "EMPTY":
                    sightbreak = True
                last_cell = current_cell
        if last_cell is not None:
            if assignment[last_cell] == value:
                if (sightbreak == False):
                    error = 1
        if error == 0:
            return True
        else:
            return False



class LollipopGitter():
    def __init__(self, size : int):
        self.size = size
        self.variables = list() # Liste der Zellen im Gitter
        for i in range(size):
            for j in range(size):
                self.variables.append((i, j))
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

    def build_puzzle(self, difficulty: Difficulty) -> Dict:
        for x in self.variables:
            self.add_constraint(RowColumnConstraint(x, self.size))
            self.add_constraint(AdjacentCellConstraint(x, self.size))
        assignment = dict()
        return assignment