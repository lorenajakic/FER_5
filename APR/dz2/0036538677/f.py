from math import sin, sqrt
import numpy as np

class FunctionWithCounter:
    def __init__(self, func):
        self.func = func
        self.evals = 0
    
    def __call__(self, x):
        self.evals += 1
        return self.func(x)
    
    def reset(self):
        self.evals = 0

def f_1(x):
    return 100 * (x[1] - x[0]**2)**2 + (1 - x[0])**2

def f_2(x):
    return (x[0] - 4)**2 + 4 * (x[1] - 2)**2

def f_3(x):
    return sum((x[i] - i - 1)**2 for i in range(len(x)))

def f_4(x):
    return abs((x[0] - x[1]) * (x[0] + x[1])) + sqrt((x[0]**2 + x[1]**2))

def f_5(x):
    sum_i = sum((x[i])**2 for i in range(len(x)))
    return 0.5 + (sin(sum_i - 0.5)**2) / ((1 + 0.001 * sum_i)**2)

def f_task1(x):
    if isinstance(x, (list, np.ndarray)) and len(x) > 0:
        x = x[0]
    return (x-3)**2