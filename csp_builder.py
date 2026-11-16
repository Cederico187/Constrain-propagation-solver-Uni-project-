from enum import Enum
from typing import List, Dict, Generic
from abc import ABC, abstractmethod
import numpy as np

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

class Zelle:
    def __init__(self, zeile: int, spalte: int):
        self.zeile = zeile
        self.spalte = spalte
    
# Constraint zwischen Variablen
class Constraint(ABC):
    def __init__(self, variables: List):
        self.variables = variables

    @abstractmethod
    def satisfied(self, assignment: Dict) -> bool:
        return True


class LollipopGitter():
    def __init__(self, size : int, difficulty : Difficulty):
        self.variables = list() # Liste der Zellen im Gitter als Liste
        for i in range(size):
            for j in range(size):
                self.variables.append(Zelle(i, j))
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