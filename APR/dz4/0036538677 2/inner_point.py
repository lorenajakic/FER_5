from hooke_jeeves import hooke_jeeves
import numpy as np

def G(g, x):
    G_value = 0.0
    for gi in g:
        gi_value = gi(x)
        if gi_value < 0:
            G_value -= gi_value
    return G_value

def inner_point(g, x0, epsilon=1e-12):
    x = np.array(x0, dtype=float)
    
    if all(gi(x) >= 0 for gi in g):
        return x
    
    while True:
        xs = x.copy()
        x = hooke_jeeves(lambda x_val: G(g, x_val), x, dx=0.5, epsilon=epsilon, output=False)
        
        if np.linalg.norm(xs - x) < epsilon: break
    
    return x
