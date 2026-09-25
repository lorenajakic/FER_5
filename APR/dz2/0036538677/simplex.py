import numpy as np
from f import f_task1

def nelder_mead(f, x0, step=1.0, alpha=1.0, beta=0.5, gamma=2.0, sigma=0.5, epsilon=1e-6, output=False):
    x0 = np.array(x0, dtype=float)
    n = len(x0)
    
    X = [x0.copy()]
    for i in range(n):
        x_new = x0.copy()
        x_new[i] += step
        X.append(x_new)
    X = np.array(X)

    iteration = 0
    while True:
        F = np.array([f(x) for x in X])
        h, l = np.argmax(F), np.argmin(F)
        
        Xc = np.mean(np.delete(X, h, axis=0), axis=0)
        if output: print(f"Iter {iteration}: centroid={Xc}, f(c)={f(Xc):.6f}")
        
        # refleksija
        Xr = Xc + alpha * (Xc - X[h])
        print("Refleksija: ", Xr)
        print(X)
        Fr = f(Xr)

        if Fr < F[l]:
            # ekspanzija
            Xe = Xc + gamma * (Xr - Xc)
            print(Xe)
            Fe = f(Xe)
            if Fe < F[l]: X[h] = Xe 
            else: X[h] = Xr
        else:
            if all(Fr > F[j] for j in range(n + 1) if j != h):
                if Fr < F[h]:
                    X[h] = Xr
                # kontrakcija
                Xk = Xc + beta * (X[h] - Xc)
                Fk = f(Xk)
                if Fk < F[h]:
                    X[h] = Xk
                else:
                    for j in range(n + 1):
                        if j != l:
                            X[j] = X[l] + sigma * (X[j] - X[l])
            else:
                X[h] = Xr
        
        F_all = np.array([f(x) for x in X])
        Fc_mean = np.mean(F_all)
        variance = np.sqrt(np.sum((F_all - Fc_mean)**2))
        if variance < epsilon:
            break

        iteration += 1

    best_idx = np.argmin([f(x) for x in X])
    return X[best_idx]


def main(f):
    x0_str = input("Enter starting point as a list (e.g., 1,2,3): ")
    x0 = [float(x) for x in x0_str.split(",")]
    
    step = float(input("Enter step for generating simplex (1.0): ") or 1.0)
    epsilon = float(input("Enter precision epsilon (1e-6): ") or 1e-6)
    alpha = float(input("Enter alpha (1.0): ") or 1.0)
    beta = float(input("Enter beta (0.5): ") or 0.5)
    gamma = float(input("Enter gamma (2.0): ") or 2.0)
    sigma = float(input("Enter sigma (0.5): ") or 0.5)
    show_steps = input("Do you want to print steps? (y/n): ").lower().startswith("y")
    
    result = nelder_mead(f, x0, step=step, alpha=alpha, beta=beta, gamma=gamma, sigma=sigma, epsilon=epsilon, output=show_steps)
    print(f"Function minimum at x = {result}, f(x) = {f(result):.6f}")

if __name__ == "__main__":
    main(f_task1)
