from matrix import Matrix
from utils import save_results_to_file

def f(A, B, x, t, r_func):
    return A @ x + B @ r_func(t)

def pece_step(A, B, T, x_k, t_k, r_func, method='trapezoidal', num_corrections=1):
    t_next = t_k + T
    
    x_next = x_k + f(A, B, x_k, t_k, r_func) * T
    
    for _ in range(num_corrections):
        if method == 'inverse_euler': x_next = x_k + f(A, B, x_next, t_next, r_func) * T
            
        elif method == 'trapezoidal':
            f_k = f(A, B, x_k, t_k, r_func)
            f_next = f(A, B, x_next, t_next, r_func)
            x_next = x_k + (f_k + f_next) * (T / 2)
            
    return x_next

def predictor_corrector_solve(A, B, x0, T, t_max, r_func, method='trapezoidal', num_corrections=1, print_every=1, save_to_file=None):
    results = []
    x = x0.copy()
    num_steps = int(round(t_max / T))

    for k in range(num_steps + 1):
        t = k * T
        curr_x = [x[i, 0] for i in range(x.rows)]
        results.append([t] + curr_x)

        if k % print_every == 0 or k == num_steps:
            x_str = " ".join(f"{val:10.6f}" for val in curr_x)
            print(f"t = {t:8.6f}, x = [{x_str}]")

        if k < num_steps: x = pece_step(A, B, T, x, t, r_func, method, num_corrections)

    if save_to_file: save_results_to_file(results, save_to_file)
        
    return results
