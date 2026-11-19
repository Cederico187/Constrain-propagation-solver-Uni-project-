import csp_builder as csp
from typing import Tuple
import operator
from operator import itemgetter

def dict_copy(old_dict: dict) -> dict:
    copy = {}
    for key in old_dict:
        copy[key] = old_dict[key].copy()
    return copy


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



def constraint_propagation(gitter: csp.LollipopGitter, assignment: dict, variable: Tuple[int,int], unassigned: list, domains: dict):
    for constraint in gitter.constraints[variable]:
        for var in constraint.variables:
            if var in unassigned:
                for possible_domain in domains[var]:
                    if not (gitter.possible(variable,possible_domain,assignment)):
                        domains[var].remove(possible_domain)

def forward_check(gitter: csp.LollipopGitter, assignment: dict, variable: Tuple[int,int], unassigned: list, domains: dict):
    for constraint in gitter.constraints[variable]:
        var = constraint.cell
        if var in unassigned:
            for possible_domain in domains[var]:
                local_assignment = {variable: assignment[variable]}
                local_assignment[var] = possible_domain
                if not (constraint.satisfied(local_assignment)):
                    domains[var].remove(possible_domain)

def forward_checking_search(gitter: csp.LollipopGitter, assignment: dict, domains: dict):
    #TODO
    if len(assignment) == len(gitter.variables):
            return assignment
    unassigned = [v for v in gitter.variables if v not in assignment]

    first = unassigned[0]
    unassigned.pop(0)

    for value in domains[first]:
        local_assignment = assignment.copy()
        local_assignment[first] = value
        # if we're still consistent, we recurse (continue)
        if gitter.consistent(first, local_assignment):
            local_domains = dict_copy(domains)
            forward_check(gitter, local_assignment, first, unassigned, local_domains) 
            result = forward_checking_search(gitter, local_assignment, local_domains)
        # if we didn't find the result, we will end up backtracking
            if result is not None:
                return result
    return None


def forward_checking_search_with_heuristic(gitter: csp.LollipopGitter, assignment: dict, domains: dict):
    if len(assignment) == len(gitter.variables):
            return assignment
    unassigned = [v for v in gitter.variables if v not in assignment]
    # MRV Heuristik
    sorted_variables = sorted(unassigned, key= lambda x: len(domains[x]))

    first = sorted_variables[0]
    unassigned.remove(first)
    
    for value in domains[first]:
        local_assignment = assignment.copy()
        local_assignment[first] = value
        # if we're still consistent, we recurse (continue)
        if gitter.consistent(first, local_assignment):
            local_domains = dict_copy(domains)
            forward_check(gitter, local_assignment, first, unassigned, local_domains) 
            result = forward_checking_search_with_heuristic(gitter, local_assignment, local_domains)
        # if we didn't find the result, we will end up backtracking
            if result is not None:
                return result
    return None

def complete_search(gitter: csp.LollipopGitter, assignment: dict ,domains: dict):
    #TODO
    if len(assignment) == len(gitter.variables):
           return assignment
    unassigned = [v for v in gitter.variables if v not in assignment]
    # MRV Heuristik
    sorted_variables = sorted(unassigned, key= lambda x: len(domains[x]))
    first = sorted_variables[0]
    unassigned.remove(first)
    
    for value in domains[first]:
        local_assignment = assignment.copy()
        local_assignment[first] = value
        # if we're still consistent, we recurse (continue)
        if gitter.consistent(first, local_assignment):
            local_domains = dict_copy(domains)
            constraint_propagation(gitter, local_assignment, first,unassigned, local_domains)
            result = complete_search(gitter, local_assignment, local_domains)
        # if we didn't find the result, we will end up backtracking
            if result is not None:
                return result
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
# solution = backtracking_search(gitter,assignment, gitter.domains)
solution = complete_search(gitter,assignment, dict_copy(gitter.domains))
sorted = dict(sorted(solution.items(), key = operator.itemgetter(0)))
print(gitter.toString(sorted))