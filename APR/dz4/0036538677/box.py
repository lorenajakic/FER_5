import numpy as np
import random

def box_method(f, x0, constraints, alpha=1.3, epsilon=1e-6):
    x0 = np.array(x0, dtype=float)
    Xc = x0.copy()
    X = [x0.copy()]
    n = len(x0)
    
    if not (constraints.check_implicit(x0) and constraints.check_explicit(x0)): raise ValueError(f"X0 = {x0} ne zadovoljava ograničenja!")
    
    for _ in range(1, 2 * n):
        x = np.zeros(n)
        for i in range(n):
            R = random.random()
            x_d, x_g = constraints.explicit_bounds[i]
            x[i] = x_d + R * (x_g - x_d)
        
        while not constraints.check_implicit(x):
            x = 0.5 * (x  + Xc)
        
        X.append(x.copy())
        Xc = np.mean(X, axis=0)
    
    X = np.array(X)
    
    no_improvement_count = 0
    best_value = float('inf')
    
    while True:
        F = np.array([f(x) for x in X])
        
        h = np.argmax(F)
        h2 = find_second_worst(F, h)
        
        current_best = np.min(F)
        if current_best < best_value - epsilon:
            best_value = current_best
            no_improvement_count = 0
        else: no_improvement_count += 1
        
        if no_improvement_count >= 100: raise ValueError("Divergencija: nema poboljšanja u 100 uzastopnih iteracija")
        
        Xc = np.mean(np.delete(X, h, axis=0), axis=0)
        Xr = (1 + alpha) * Xc - alpha * X[h]

        for i in range(n):
            x_d, x_g = constraints.explicit_bounds[i]
            if Xr[i] < x_d: Xr[i] = x_d
            elif Xr[i] > x_g: Xr[i] = x_g

            while not constraints.check_implicit(Xr):
                Xr = 0.5 * (Xr  + Xc)
        
        Fr = f(Xr)
        if Fr > F[h2]: Xr = 0.5 * (Xr + Xc)
        
        X[h] = Xr
        
        F_all = np.array([f(x) for x in X])
        F_mean = np.mean(F_all)
        std_dev = np.sqrt(np.mean((F_all - F_mean)**2))
        
        if std_dev < epsilon:
            break
            
    best_idx = np.argmin([f(x) for x in X])
    return X[best_idx]

def find_second_worst(F, h):
    F_without_h = F.copy()
    F_without_h[h] = -np.inf
    return np.argmax(F_without_h)