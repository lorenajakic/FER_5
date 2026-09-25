import numpy as np

def explore(xP, dx, f):
    x = np.array(xP, dtype=float)
    n = len(x)
    
    for i in range(n):
        P = f(x)
        x[i] = x[i] + dx[i]
        N = f(x)
        
        if N > P:
            x[i] = x[i] - 2 * dx[i]
            N = f(x)

            if N > P: x[i] = x[i] + dx[i]
    
    return x

def hooke_jeeves(f, x0, dx=0.5, epsilon=1e-12, output=False):
    x0 = np.array(x0, dtype=float)
    n = len(x0)
    
    if np.isscalar(dx): dx = np.full(n, dx)
    else: dx = np.array(dx, dtype=float)
    
    if np.isscalar(epsilon): epsilon = np.full(n, epsilon)
    else: epsilon = np.array(epsilon, dtype=float)
    
    xB, xP = x0.copy(), x0.copy()
    
    while True:
        xN = explore(xP, dx, f)
        
        if f(xN) < f(xB):
            xP = 2 * xN - xB
            xB = xN.copy()
        else:
            dx = dx / 2.0
            xP = xB.copy()
        
        if np.all(dx < epsilon):
            break
    
    return xB