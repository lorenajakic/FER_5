from utils import save_results_to_file

def inverse_euler_step(A, B, T, x_k, t_k_plus_1, r_func):
    I = A.identity_matrix()
    I_minus_AT = I - (A * T)
    P = I_minus_AT.copy().inverse()
    Q = P @ (B * T)

    return P @ x_k + Q @ r_func(t_k_plus_1)

def inverse_euler_solve(A, B, x0, T, t_max, r_func, print_every=1, save_to_file=None):
    results = []
    x = x0.copy()
    
    num_steps = int(round(t_max / T))
    
    for k in range(num_steps + 1):
        t = k * T 
        
        curr_x = [x[i, 0] for i in range(x.rows)]
        results.append([t] + curr_x)
        
        if k % print_every == 0 or k == num_steps:
            print(f"t = {t:8.6f}, x = [{" ".join(f"{val:10.6f}" for val in curr_x)}]")
        
        if k < num_steps:
            t_next = (k + 1) * T
            x = inverse_euler_step(A, B, T, x, t_next, r_func)
    
    if save_to_file: save_results_to_file(results, save_to_file)
    
    return results
