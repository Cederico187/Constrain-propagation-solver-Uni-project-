import csp_builder as csp
from typing import Tuple
import operator

def backtracking_search(gitter : csp.LollipopGitter, assignment):
    # assignment is complete if every variable is assigned (our base case)
    if len(assignment) == len(gitter.variables):
        return assignment

    # get all variables in the CSP but not in the assignment
    unassigned = [v for v in gitter.variables if v not in assignment]

    # get the every possible domain value of the first unassigned variable
    first = unassigned[0]
    for value in gitter.domains[first]:
        local_assignment = assignment.copy()
        local_assignment[first] = value
        # if we're still consistent, we recurse (continue)
        if gitter.consistent(first, local_assignment):
            result = backtracking_search(gitter, local_assignment)
            # if we didn't find the result, we will end up backtracking
            if result is not None:
                return result
    return None

def constraint_propagation(gitter: csp.LollipopGitter, assignment: dict, variable: Tuple[int,int], unassigned: list):
    for constraint in gitter.constraints[variable]:
        for var in constraint.variables:
            if var in unassigned:
                for domain in gitter.domains[var]:
                    if not (gitter.possible(var,domain,assignment)):
                        gitter.domains[var].remove(domain) 

def forward_check(gitter: csp.LollipopGitter, assignment: dict, variable: Tuple[int,int], unassigned: list):
    for constraint in gitter.constraints[variable]:
        var = constraint.cell
        if var in unassigned:
            for domain in gitter.domains[var]:
                if not (gitter.possible(var,domain,assignment)):
                    gitter.domains[var].remove(domain) 

def forward_checking_search(gitter: csp.LollipopGitter, assignment: dict):
    #TODO
    if len(assignment) == len(gitter.variables):
            return assignment
    unassigned = [v for v in gitter.variables if v not in assignment]

    first = unassigned[0]
    for value in gitter.domains[first]:
        local_assignment = assignment.copy()
        local_assignment[first] = value
        # if we're still consistent, we recurse (continue)
        if gitter.consistent(first, local_assignment):
            forward_check(gitter, local_assignment, first, unassigned) 
            result = forward_checking_search(gitter, local_assignment)
        # if we didn't find the result, we will end up backtracking
        if result is not None:
            return result
    return None


def forward_checking_search_with_heuristic(gitter: csp.LollipopGitter, assignment: dict):
    #TODO
    return None

def complete_search(gitter: csp.LollipopGitter, assignment: dict ):
    #TODO
    return None

def heuristic():
    #TODO: mrv
    #TODO: Gradheuristic
    return None

def solve_puzzle(search_function, gitter: csp.LollipopGitter, assignment: dict) -> None:
    #TODO
    solution = search_function(gitter,assignment)
    #TODO
    # Logging(Ausgabe)
    # a) Probleminstanz
    # b) Lösung, sofern der Solver nicht nach Erreichen des Zeitlimits die Suche abgegrochen hat
    # c) Dauer der Suche
    # d) Anzahl der Variablenbelegungen
    # e) Anzahl der Backtrackingschritte
    print(gitter.toString(solution))

def make_puzzle(size: int,difficulty: csp.Difficulty) -> Tuple[csp.LollipopGitter, dict]:
    gitter = csp.LollipopGitter(size)
    start_assignment = gitter.build_puzzle(difficulty)
    return (gitter,start_assignment)

gitter = csp.LollipopGitter(15)
assignment = gitter.build_puzzle(csp.Difficulty.HARD)
print(gitter.toString(assignment))
solution = forward_checking_search(gitter,assignment)
sorted = dict(sorted(solution.items(), key = operator.itemgetter(0)))
print(gitter.toString(sorted))