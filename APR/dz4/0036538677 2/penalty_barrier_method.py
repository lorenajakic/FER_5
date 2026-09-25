from hooke_jeeves import hooke_jeeves
from inner_point import inner_point
import numpy as np
import math

def F(f, g, h, t, x):
    F = f(x)
    
    for gi in g:
        gi_value = gi(x)
        if gi_value <= 0: return float('inf')
        else: F -= (1.0 / t) * math.log(gi_value)
    
    for hi in h:
        hi_value = hi(x)
        F += t * (hi_value ** 2) 
    return F

def penalty_barrier_method(f, constraints, g=None, h=None, t0=1.0, x0=None, epsilon=1e-6):
    g = constraints.implicit_constraints
    h = constraints.equality_constraints

    if g is None: g = []
    if h is None: h = []
    
    x = np.array(x0, dtype=float)
    t = t0

    if g and not all(gi(x) >= 0 for gi in g):
        x = inner_point(g, x, epsilon=epsilon)
    
    no_improvement_count = 0
    best_value = float('inf')
    
    while True:
        xs = x.copy()
        
        def F_t(x_val): return F(f, g, h, t, x_val)
        
        x = hooke_jeeves(F_t, x, dx=0.5, epsilon=epsilon, output=False)
        t = 10 * t
        
        current_value = f(x)
        if current_value < best_value - epsilon:
            best_value = current_value
            no_improvement_count = 0
        else: no_improvement_count += 1
        
        if no_improvement_count >= 100: raise RuntimeError("Divergencija: nema poboljšanja u 100 uzastopnih iteracija")
        if np.linalg.norm(xs - x) < epsilon: break
    return x
