import numpy as np
from f import f_task1

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

def hooke_jeeves(f, x0, dx=0.5, epsilon=1e-6, output=False):
    x0 = np.array(x0, dtype=float)
    n = len(x0)
    
    if np.isscalar(dx): dx = np.full(n, dx)
    else: dx = np.array(dx, dtype=float)
    
    if np.isscalar(epsilon): epsilon = np.full(n, epsilon)
    else: epsilon = np.array(epsilon, dtype=float)
    
    xB, xP = x0.copy(), x0.copy()
    
    while True:
        xN = explore(xP, dx, f)
        
        if output:
            print(f"  Base point xB = {xB}, f(xB) = {f(xB):.6f}")
            print(f"  Search start xP = {xP}, f(xP) = {f(xP):.6f}")
            print(f"  Search result xN = {xN}, f(xN) = {f(xN):.6f}")
            print()
        
        if f(xN) < f(xB):
            xP = 2 * xN - xB
            xB = xN.copy()
        else:
            dx = dx / 2.0
            xP = xB.copy()
        
        if np.all(dx < epsilon):
            break
    
    return xB

def main(f):
    x0_str = input("Enter starting point as a list (1,2,3): ")
    x0 = [float(x) for x in x0_str.split(",")]
    
    dx_str = input("Enter step dx as scalar or list (0.5): ") or "0.5"
    if "," in dx_str: dx = [float(x) for x in dx_str.split(",")]
    else: dx = float(dx_str)
    
    epsilon_str = input("Enter precision epsilon as scalar or list (1e-6): ") or "1e-6"
    if "," in epsilon_str: epsilon = [float(x) for x in epsilon_str.split(",")]
    else: epsilon = float(epsilon_str)
    
    output = input("Do you want to print steps? (y/n): ").lower().startswith("y")
    result = hooke_jeeves(f, x0, dx=dx, epsilon=epsilon, output=output)
    print(f"Function minimum at x = {result}, f(x) = {f(result):.6f}")


if __name__ == "__main__":
    main(f_task1)