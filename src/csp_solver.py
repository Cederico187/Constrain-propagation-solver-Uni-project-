import csp_builder as csp
from typing import Tuple
import operator
from operator import itemgetter
import puzzle_lib as lib

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



def constraint_propagation(gitter: csp.LollipopGitter, assignment: dict, unassigned: list, domains: dict):
    for variable in assignment:    
        for constraint in gitter.constraints[variable]:
            for var in constraint.variables:
                if var in unassigned:
                    for possible_domain in domains[var]:
                        local_assignment = {variable: assignment[variable]}
                        local_assignment[var] = possible_domain
                        if not (constraint.satisfied(local_assignment)):
                            domains[var].remove(possible_domain)

def forward_check(gitter: csp.LollipopGitter, assignment: dict, variable: Tuple[int,int], unassigned: list, domains: dict):
    for constraint in gitter.constraints[variable]:
        var = constraint.cell
        if var in unassigned:
            for possible_domain in domains[var]:
                local_assignment = assignment.copy()
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
    if len(assignment) == len(gitter.variables):
           return assignment
    unassigned = [v for v in gitter.variables if v not in assignment]
    constraint_propagation(gitter, assignment,unassigned,domains)
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
            forward_check(gitter, local_assignment, first,unassigned, local_domains)
            result = forward_checking_search_with_heuristic(gitter, local_assignment, local_domains)
        # if we didn't find the result, we will end up backtracking
            if result is not None:
                return result
    return None


    

def eingabe():
    while True:
        try:
            difficulty = input("Wählen sie Schwierigkeit Normal oder Schwer\n")
            if difficulty not in ("Normal","Schwer"):
                raise ValueError()
            break
        except ValueError:
            print("Falsche Eingabe!")

    while True:
        try: 
            size = input("Wählen sie eine der folgenden Puzzle aus: 6, 10, 15 \n")
            size = int(size)
            if size not in(6, 10, 15):
                raise ValueError
            break
        except ValueError:
            print("Falsche Eingabe!")
    while True:
        try:
            loesen = input("Wählen sie einen Lösungsalgorithmus:  bs = backtracking_search, fcs = forward_checking_search, fcsH = forward_checking_search_with_heuristic, \n cs = complete_search\n")
            if loesen not in ("bs","fcs","fcsH","cs"):
                raise ValueError
            break
        except ValueError:
            print("Falsche Eingabe!")
    print("Probleminstanz:\nSize=" + str(size) + "\nSchwierigkeit=" + str(difficulty)+"\n")
    if difficulty == "Normal":
        difficulty = csp.Difficulty.MEDIUM
    if difficulty == "Schwer":
        difficulty = csp.Difficulty.HARD
    return difficulty, size, loesen
    
def make_puzzle(size ,difficulty) -> Tuple[csp.LollipopGitter, dict]:
    gitter = csp.LollipopGitter(size)
    start_assignment = gitter.build_puzzle(difficulty)
    return gitter,start_assignment

def solve_puzzle(loesen, gitter, start_assignment, domains: dict):
    print(gitter.toString(start_assignment))
    if loesen == "bs":
        solution = backtracking_search(gitter,start_assignment)
    if loesen == "fcs":
        solution = forward_checking_search(gitter,start_assignment, dict_copy(domains))
    if loesen == "fcsH":
        solution = forward_checking_search_with_heuristic(gitter,start_assignment,domains)
    if loesen == "cs":
        solution = complete_search(gitter,start_assignment,domains)
    # Logging(Ausgabe)
    # a) Probleminstanz
    
    # b) Lösung, sofern der Solver nicht nach Erreichen des Zeitlimits die Suche abgegrochen hat
    if(solution is not None):
        print(gitter.toString(solution))
    """if dauer <= 60:
        print(gitter.toString(solution))
    else:
        print("Lösung ist wegen überschrittenen Zeitlimit abgebrochen")
    # c) Dauer der Suche
    print("Die Dauer der Lösungssuche beträgt"+ dauer +"Sekunden")
    # d) Anzahl der Variablenbelegungen
    print("Anzahl der Variablenbelegung:"+ variablenbelegung)
    # e) Anzahl der Backtrackingschritte
    print("Anzahl der Backtrackingschritte:"+ backtracking_schritte)
    dauer, variablenbelegung, backtracking_schritte"""
    #TODO: Dauer, variablenbelegung,backtrackingschritte
    

def main():
    difficulty, size, loesen = eingabe()
    gitter, start_assignment = make_puzzle(size,difficulty)

    solve_puzzle(loesen, gitter, start_assignment, dict_copy(gitter.domains))

main()