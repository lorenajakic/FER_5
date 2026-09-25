import numpy as np
from f import f_task1
from golden_ratio import golden_ratio
from unimodal import unimodal

def coordinate_search(f, x0, e=1e-6, h=1.0):
    x = np.array(x0, dtype=float)
    n = len(x)
    
    if np.isscalar(e): e = np.full(n, e)
    else: e = np.array(e, dtype=float)

    while True:
        xs = x.copy()

        for i in range(n):
            e_i = np.zeros(n)
            e_i[i] = 1.0

            def f1d(lmbd):
                return f(x + lmbd * e_i)

            a, b = unimodal(0.0, h, f1d)
            lam = golden_ratio(a, b, e[i], f1d)
            x = x + lam * e_i
        print(xs)

        if np.linalg.norm(x - xs) <= np.linalg.norm(e):
            break

    return x

def main(f):
    x0_str = input("Enter starting point as a list (=> 1,2,3): ")
    x0 = [float(x) for x in x0_str.split(",")]
    
    e_str = input("Enter precision e as scalar or list (1e-6): ") or "1e-6"
    if "," in e_str: e = [float(x) for x in e_str.split(",")]
    else: e = float(e_str)

    h = float(input("Enter step h (1): ") or 1.0)

    result = coordinate_search(f, x0, e=e, h=h)
    print(f"Function minimum at x = {result}, f(x) = {f(result):.6f}")

if __name__ == "__main__":
    main(f_task1)