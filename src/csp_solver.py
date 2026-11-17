import csp_builder as csp

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

gitter = csp.LollipopGitter(4)
assignment = gitter.build_puzzle(csp.Difficulty.HARD)
solution = backtracking_search(gitter,assignment)
print(solution)