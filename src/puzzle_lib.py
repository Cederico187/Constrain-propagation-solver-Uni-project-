import csp_builder as csp
def size15_Hard():
    size15_hard ={}
    size15_hard[(0,2)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(0,5)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(0,12)] = csp.Domain.CIRCLE
    size15_hard[(1,1)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(1,9)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(1,14)] = csp.Domain.CIRCLE
    size15_hard[(2,3)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(2,5)] = csp.Domain.CIRCLE
    size15_hard[(2,11)] = csp.Domain.CIRCLE
    size15_hard[(3,8)] = csp.Domain.CIRCLE
    size15_hard[(4,13)] = csp.Domain.VERTICAL_LINE
    size15_hard[(5,4)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(6,0)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(6,12)] = csp.Domain.CIRCLE
    size15_hard[(6,14)] = csp.Domain.VERTICAL_LINE
    size15_hard[(7,5)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(7,8)] = csp.Domain.CIRCLE
    size15_hard[(8,2)] = csp.Domain.CIRCLE
    size15_hard[(9,0)] = csp.Domain.CIRCLE
    size15_hard[(9,10)] = csp.Domain.CIRCLE
    size15_hard[(10,4)] = csp.Domain.CIRCLE
    size15_hard[(10,7)] = csp.Domain.CIRCLE
    size15_hard[(11,9)] = csp.Domain.VERTICAL_LINE
    size15_hard[(11,14)] = csp.Domain.VERTICAL_LINE
    size15_hard[(12,2)] = csp.Domain.CIRCLE
    size15_hard[(12,11)] = csp.Domain.VERTICAL_LINE
    size15_hard[(13,1)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(13,11)] = csp.Domain.CIRCLE
    size15_hard[(14,4)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(14,7)] = csp.Domain.HORIZONTAL_LINE
    size15_hard[(14,13)] = csp.Domain.CIRCLE
    return size15_hard


def size10_medium():
    assignment = {}
    assignment[(0,0)] = csp.Domain.HORIZONTAL_LINE
    assignment[(0,4)] = csp.Domain.CIRCLE
    assignment[(0,7)] = csp.Domain.VERTICAL_LINE
    assignment[(1,9)] = csp.Domain.VERTICAL_LINE
    assignment[(2,4)] = csp.Domain.HORIZONTAL_LINE
    assignment[(3,1)] = csp.Domain.HORIZONTAL_LINE
    assignment[(3,8)] = csp.Domain.VERTICAL_LINE
    assignment[(4,5)] = csp.Domain.CIRCLE
    assignment[(5,9)] = csp.Domain.VERTICAL_LINE
    assignment[(6,0)] = csp.Domain.CIRCLE
    assignment[(6,2)] = csp.Domain.VERTICAL_LINE
    assignment[(6,6)] = csp.Domain.CIRCLE
    assignment[(7,9)] = csp.Domain.HORIZONTAL_LINE
    assignment[(8,3)] = csp.Domain.CIRCLE
    assignment[(8,6)] = csp.Domain.HORIZONTAL_LINE
    assignment[(9,2)] = csp.Domain.HORIZONTAL_LINE
    assignment[(9,4)] = csp.Domain.CIRCLE
    return assignment

def size15_medium():
    assignment = {}
    assignment[(0,1)] = csp.Domain.VERTICAL_LINE
    assignment[(0,4)] = csp.Domain.CIRCLE
    assignment[(0,7)] = csp.Domain.HORIZONTAL_LINE
    assignment[(1,14)] = csp.Domain.CIRCLE
    assignment[(2,3)] = csp.Domain.HORIZONTAL_LINE
    assignment[(2,10)] = csp.Domain.VERTICAL_LINE
    assignment[(3,1)] = csp.Domain.HORIZONTAL_LINE
    assignment[(4,2)] = csp.Domain.HORIZONTAL_LINE
    assignment[(4,6)] = csp.Domain.VERTICAL_LINE
    assignment[(4,14)] = csp.Domain.CIRCLE
    assignment[(5,10)] = csp.Domain.VERTICAL_LINE
    assignment[(6,2)] = csp.Domain.VERTICAL_LINE
    assignment[(6,8)] = csp.Domain.CIRCLE
    assignment[(7,12)] = csp.Domain.VERTICAL_LINE
    assignment[(8,1)] = csp.Domain.HORIZONTAL_LINE
    assignment[(8,6)] = csp.Domain.VERTICAL_LINE
    assignment[(8,14)] = csp.Domain.VERTICAL_LINE
    assignment[(9,7)] = csp.Domain.CIRCLE
    assignment[(9,10)] = csp.Domain.CIRCLE
    assignment[(10,2)] = csp.Domain.HORIZONTAL_LINE
    assignment[(10,4)] = csp.Domain.CIRCLE
    assignment[(10,13)] = csp.Domain.HORIZONTAL_LINE
    assignment[(11,0)] = csp.Domain.VERTICAL_LINE
    assignment[(12,5)] = csp.Domain.CIRCLE
    assignment[(12,9)] = csp.Domain.CIRCLE
    assignment[(12,13)] = csp.Domain.VERTICAL_LINE
    assignment[(13,2)] = csp.Domain.VERTICAL_LINE
    assignment[(14,8)] = csp.Domain.CIRCLE
    assignment[(14,12)] = csp.Domain.CIRCLE
    return assignment

def size6_hard():
    assignment = {}
    assignment[(0,4)] = csp.Domain.HORIZONTAL_LINE
    assignment[(1,0)] = csp.Domain.CIRCLE
    assignment[(1,3)] = csp.Domain.CIRCLE
    assignment[(3,5)] = csp.Domain.VERTICAL_LINE
    assignment[(4,0)] = csp.Domain.CIRCLE
    assignment[(5,2)] = csp.Domain.HORIZONTAL_LINE
    return assignment


def size10_hard():
    assignment = {}
    assignment[(0,9)] = csp.Domain.VERTICAL_LINE
    assignment[(1,1)] = csp.Domain.VERTICAL_LINE
    assignment[(1,5)] = csp.Domain.HORIZONTAL_LINE
    assignment[(2,8)] = csp.Domain.CIRCLE
    assignment[(3,6)] = csp.Domain.HORIZONTAL_LINE
    assignment[(4,0)] = csp.Domain.VERTICAL_LINE
    assignment[(5,9)] = csp.Domain.VERTICAL_LINE
    assignment[(6,0)] = csp.Domain.HORIZONTAL_LINE
    assignment[(7,5)] = csp.Domain.HORIZONTAL_LINE
    assignment[(7,8)] = csp.Domain.CIRCLE
    assignment[(8,0)] = csp.Domain.VERTICAL_LINE
    assignment[(9,7)] = csp.Domain.CIRCLE 
    return assignment

def size6_medium():
    assignment = {}
    return assignment