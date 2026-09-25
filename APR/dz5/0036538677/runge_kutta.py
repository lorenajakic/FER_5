from matrix import Matrix
from utils import save_results_to_file

def rk4_f(A, B, x, t, r_func):
    return A @ x + B @ r_func(t)

def rk4_step(A, B, T, x_k, t_k, r_func):
    m1 = rk4_f(A, B, x_k, t_k, r_func)
    m2 = rk4_f(A, B, x_k + (m1 * (T / 2)), t_k + T / 2, r_func)
    m3 = rk4_f(A, B, x_k + (m2 * (T / 2)), t_k + T / 2, r_func)
    m4 = rk4_f(A, B, x_k + (m3 * T), t_k + T, r_func)
    return x_k + ((m1 + (m2 * 2) + (m3 * 2) + m4) * (T / 6))

def rk4_solve(A, B, x0, T, t_max, r_func, print_every=1, save_to_file=None):
    results = []
    x = x0.copy()
    
    num_steps = int(round(t_max / T))
    
    for k in range(num_steps + 1):
        t = k * T
        
        curr_x = [x[i, 0] for i in range(x.rows)]
        results.append([t] + curr_x)
        
        if k % print_every == 0 or k == num_steps:
            print(f"t = {t:8.6f}, x = [{" ".join(f"{val:10.6f}" for val in curr_x)}]")
        
        if k < num_steps: x = rk4_step(A, B, T, x, t, r_func)
    
    if save_to_file: save_results_to_file(results, save_to_file)
    return results
