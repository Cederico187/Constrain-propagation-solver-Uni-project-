from enum import Enum
from typing import List, Dict, Generic, Tuple
from abc import ABC, abstractmethod

#fehler -> adjacenzcellconstraint?

# Wertebereich für Zellen im Gitter
class Domain(Enum):
    CIRCLE = 0
    HORIZONTAL_LINE = 1
    VERTICAL_LINE = 2
    EMPTY = 3

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
        self.cell_above = (x-1, y)
        self.cell_below = (x+1, y)
        self.cell_left = (x, y-1)
        self.cell_right = (x, y+1)
        variables = []
        variables.append(self.cell)
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
        if self.cell not in assignment:
            return True
        match assignment[self.cell]:
            case Domain.EMPTY:
                return True
            case Domain.HORIZONTAL_LINE:
                if self.cell_above in assignment and assignment[self.cell_above] != Domain.EMPTY:
                    return False
                if self.cell_below in assignment and assignment[self.cell_below] != Domain.EMPTY:
                    return False
                if self.cell_left in assignment:
                    if assignment[self.cell_left] == Domain.VERTICAL_LINE or assignment[self.cell_left] == Domain.HORIZONTAL_LINE:
                        return False
                    if assignment[self.cell_left] == Domain.CIRCLE:
                        if self.cell_right in assignment and assignment[self.cell_right] != Domain.EMPTY:
                            return False
                    if assignment[self.cell_left] == Domain.EMPTY:
                        if self.cell_right in assignment and assignment[self.cell_right] != Domain.CIRCLE:
                            return False
                if self.cell_right in assignment:
                    if assignment[self.cell_right] == Domain.VERTICAL_LINE or assignment[self.cell_right] == Domain.HORIZONTAL_LINE:
                        return False
                    if assignment[self.cell_right] == Domain.CIRCLE:
                        if self.cell_left in assignment and assignment[self.cell_left] != Domain.EMPTY:
                            return False
                    if assignment[self.cell_right] == Domain.EMPTY:
                        if self.cell_left in assignment and assignment[self.cell_left] != Domain.CIRCLE:
                            return False
                if self.cell_right in assignment and self.cell_left in assignment:
                    if assignment[self.cell_left] == assignment[self.cell_right]:
                        return False
                
                

            case Domain.VERTICAL_LINE:
                if self.cell_right in assignment and assignment[self.cell_right] != Domain.EMPTY:
                    return False
                if self.cell_left in assignment and assignment[self.cell_left] != Domain.EMPTY:
                    return False
                if self.cell_above in assignment:
                    if assignment[self.cell_above] == Domain.VERTICAL_LINE or assignment[self.cell_above] == Domain.HORIZONTAL_LINE:
                        return False
                    if assignment[self.cell_above] == Domain.CIRCLE:
                        if self.cell_below in assignment and assignment[self.cell_below] != Domain.EMPTY:
                            return False
                    if assignment[self.cell_above] == Domain.EMPTY:
                        if self.cell_below in assignment and assignment[self.cell_below] != Domain.CIRCLE:
                            return False
                if self.cell_below in assignment:
                    if assignment[self.cell_below] == Domain.VERTICAL_LINE or assignment[self.cell_below] == Domain.HORIZONTAL_LINE:
                        return False
                    if assignment[self.cell_below] == Domain.CIRCLE:
                        if self.cell_above in assignment and assignment[self.cell_above] != Domain.EMPTY:
                            return False
                    if assignment[self.cell_below] == Domain.EMPTY:
                        if self.cell_above in assignment and assignment[self.cell_above] != Domain.CIRCLE:
                            return False
                if self.cell_above in assignment and self.cell_below in assignment:
                    if assignment[self.cell_above] == assignment[self.cell_below]:
                        return False
            case Domain.CIRCLE:
                yes = 0
                if self.cell_right in assignment:
                    if assignment[self.cell_right] == Domain.CIRCLE or assignment[self.cell_right] == Domain.VERTICAL_LINE :
                        return False
                    if assignment[self.cell_right] == Domain.HORIZONTAL_LINE:
                        yes = 1
                        if(self.cell_left) in assignment:
                            if assignment[self.cell_left] != Domain.EMPTY:
                                return False
                        if(self.cell_above) in assignment:
                            if assignment[self.cell_above] != Domain.EMPTY:
                                return False
                        if(self.cell_below) in assignment:
                            if assignment[self.cell_below] != Domain.EMPTY:
                                return False
                if self.cell_left in assignment:
                    if assignment[self.cell_left] == Domain.CIRCLE or assignment[self.cell_left] == Domain.VERTICAL_LINE :
                        return False
                    if assignment[self.cell_left] == Domain.HORIZONTAL_LINE:
                        yes = 1
                        if(self.cell_right) in assignment:
                            if assignment[self.cell_right] != Domain.EMPTY:
                                return False
                        if(self.cell_above) in assignment:
                            if assignment[self.cell_above] != Domain.EMPTY:
                                return False
                        if(self.cell_below) in assignment:
                            if assignment[self.cell_below] != Domain.EMPTY:
                                return False
                if self.cell_above in assignment:
                    if assignment[self.cell_above] == Domain.CIRCLE or assignment[self.cell_above] == Domain.HORIZONTAL_LINE :
                        return False
                    if assignment[self.cell_above] == Domain.VERTICAL_LINE:
                        yes = 1
                        if(self.cell_right) in assignment:
                            if assignment[self.cell_right] != Domain.EMPTY:
                                return False
                        if(self.cell_left) in assignment:
                            if assignment[self.cell_left] != Domain.EMPTY:
                                return False
                        if(self.cell_below) in assignment:
                            if assignment[self.cell_below] != Domain.EMPTY:
                                return False
                if self.cell_below in assignment:
                    if assignment[self.cell_below] == Domain.CIRCLE or assignment[self.cell_below] == Domain.HORIZONTAL_LINE :
                        return False
                    if assignment[self.cell_below] == Domain.VERTICAL_LINE:
                        yes = 1
                        if(self.cell_right) in assignment:
                            if assignment[self.cell_right] != Domain.EMPTY:
                                return False
                        if(self.cell_above) in assignment:
                            if assignment[self.cell_above] != Domain.EMPTY:
                                return False
                        if(self.cell_left) in assignment:
                            if assignment[self.cell_left] != Domain.EMPTY:
                                return False
                if all(v in assignment for v in self.variables):    
                    if yes == 0:
                        return False
        return True


class RowColumnConstraint(Constraint):
    def __init__(self, cell : Tuple[int,int], size: int) -> None:
        self.cell = cell
        self.row = cell[0]
        self.column = cell[1]
        self.size = size
        super().__init__([(self.row,j) for j in range(self.column)] + [(self.row,j) for j in range(self.column+1, self.size)] + [(i,self.column) for i in range(self.size)])

    def satisfied(self, assignment: Dict) -> bool:
        if self.cell in assignment:
            value = assignment[self.cell]
        else:
            return True
        if value == Domain.EMPTY:
            return True
        error = False
        sightbreak = False
        last_cell = None
        for i in range(self.column+1,self.size):
            current_cell = (self.row,i)
            if current_cell in assignment:
                if assignment[current_cell] != value and assignment[current_cell] != Domain.EMPTY:
                    sightbreak = True
                last_cell = current_cell
                if(assignment[last_cell] == value):
                    break
            else:
                break
        if last_cell != None:
            if assignment[last_cell] == value:
                if (sightbreak ==False):
                    error = 1


        sightbreak = False
        last_cell = None
        for i in reversed(range(self.column)):
            current_cell = (self.row, i)
            if current_cell in assignment:
                if assignment[current_cell] != value and assignment[current_cell] != Domain.EMPTY:
                    sightbreak = True
                last_cell = current_cell
                if(assignment[last_cell] == value):
                    break
            else:
                break
        if last_cell != None:
            if assignment[last_cell] == value:
                if sightbreak == False:
                    error = 1

        sightbreak = False
        last_cell = None
        for i in range(self.row+1, self.size):
            current_cell = (i, self.column)
            if current_cell in assignment:
                if assignment[current_cell] != value and assignment[current_cell] != Domain.EMPTY:
                    sightbreak = True
                last_cell = current_cell
                if(assignment[last_cell] == value):
                    break
            else: 
                break
        if last_cell != None:
            if assignment[last_cell] == value:
                if (sightbreak == False):
                    error = 1

        sightbreak = False
        last_cell = None
        for i in reversed(range(self.row)):
            current_cell = (i,self.column)
            if current_cell in assignment:
                if assignment[current_cell] != value and assignment[current_cell] != Domain.EMPTY:
                    sightbreak = True
                last_cell = current_cell
                if(assignment[last_cell] == value):
                    break
            else:
                break
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

    def toString(self, assignment: Dict):
        # •, ─, │, ┼, ⎽, ·, ┴
        # string = "•─" * self.size + "•" + "\n"
        
        symbols = {
            Domain.EMPTY: " ",
            Domain.HORIZONTAL_LINE: "━",
            Domain.VERTICAL_LINE: "┃",
            Domain.CIRCLE: "o",
        }
        
        länge = len(str(abs(self.size)))

        string = "  "
        for i in range(self.size):
            i_len = len(str(abs(i)))
            string += " " * (länge - i_len) + " %d" % i

        string += "\n"

        for i in range(self.size + 1):
            string += "─" * (länge) + "┼"

        string += "\n"

        for i in range(self.size):
            i_len = len(str(abs(i)))

            string += " " * (länge - i_len)
            string += "%d" % i

            for j in range(self.size):
                string += "│"
                string += " " * (länge - 1)
                string += symbols.get(assignment.get((i, j)), " ")
            
            string += "│" + "\n"

        for i in range(self.size + 1):
                    string += "─" * (länge) + "┴"

        return string

    def add_constraint(self, constraint: Constraint) -> None:
        for variable in constraint.variables:
            if variable not in self.variables:
                raise LookupError("Variable in constraint not in CSP")
            else:
                self.constraints[variable].append(constraint)

    def consistent(self, variable: Tuple[int,int], assignment: Dict) -> bool:
        for constraint in self.constraints[variable]:
            if not constraint.satisfied(assignment):
                return False
        return True

    def possible(self, variable: Tuple[int,int], value: Domain, assignment: dict) -> bool:
        test_assignment = assignment.copy()
        test_assignment[variable] = value
        if self.consistent(variable, test_assignment):
            return True
        else:
            return False

    def build_puzzle(self, difficulty: Difficulty) -> Dict:
        for x in self.variables:
            self.add_constraint(RowColumnConstraint(x, self.size))
            self.add_constraint(AdjacentCellConstraint(x, self.size))
        assignment = dict()
        assignment[(0,2)] = Domain.HORIZONTAL_LINE
        assignment[(0,5)] = Domain.HORIZONTAL_LINE
        assignment[(0,12)] = Domain.CIRCLE
        assignment[(1,1)] = Domain.HORIZONTAL_LINE
        assignment[(1,9)] = Domain.HORIZONTAL_LINE
        assignment[(1,14)] = Domain.CIRCLE
        assignment[(2,3)] = Domain.HORIZONTAL_LINE
        assignment[(2,5)] = Domain.CIRCLE
        assignment[(2,11)] = Domain.CIRCLE
        assignment[(3,8)] = Domain.CIRCLE
        assignment[(4,13)] = Domain.VERTICAL_LINE
        assignment[(5,4)] = Domain.HORIZONTAL_LINE
        assignment[(6,0)] = Domain.HORIZONTAL_LINE
        assignment[(6,12)] = Domain.CIRCLE
        assignment[(6,14)] = Domain.VERTICAL_LINE
        assignment[(7,5)] = Domain.HORIZONTAL_LINE
        assignment[(7,8)] = Domain.CIRCLE
        assignment[(8,2)] = Domain.CIRCLE
        assignment[(9,0)] = Domain.CIRCLE
        assignment[(9,10)] = Domain.CIRCLE
        assignment[(10,4)] = Domain.CIRCLE
        assignment[(10,7)] = Domain.CIRCLE
        assignment[(11,9)] = Domain.VERTICAL_LINE
        assignment[(11,14)] = Domain.VERTICAL_LINE
        assignment[(12,2)] = Domain.CIRCLE
        assignment[(12,11)] = Domain.VERTICAL_LINE
        assignment[(13,1)] = Domain.HORIZONTAL_LINE
        assignment[(13,11)] = Domain.CIRCLE
        assignment[(14,4)] = Domain.HORIZONTAL_LINE
        assignment[(14,7)] = Domain.HORIZONTAL_LINE
        assignment[(14,13)] = Domain.CIRCLE
        return assignment
    
