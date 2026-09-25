from utils import save_results_to_file

def trapezoidal_step(A, B, T, x_k, t_k, t_k_plus_1, r_func):
    I = A.identity_matrix()
    I_plus_AT= I + (A * (T/2))
    I_minus_AT = I - (A * (T/2))
    
    inverse_I_minus_AT = I_minus_AT.copy().inverse()
    R = inverse_I_minus_AT @ I_plus_AT
    S = inverse_I_minus_AT @ (B * (T/2))
    
    return R @ x_k + S @ (r_func(t_k) + r_func(t_k_plus_1))

def trapezoidal_solve(A, B, x0, T, t_max, r_func, print_every=1, save_to_file=None):
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
            x = trapezoidal_step(A, B, T, x, t, t_next, r_func)
    
    if save_to_file: save_results_to_file(results, save_to_file)
    
    return results
