import math
from matrix import Matrix
from euler import euler_solve
from inverzni_euler import inverse_euler_solve
from trapezni_euler import trapezoidal_solve
from runge_kutta import rk4_solve
from predictor_corrector import predictor_corrector_solve

def analytical_solution(t, x1_0, x2_0):
    return x1_0 * math.cos(t) + x2_0 * math.sin(t), x2_0 * math.cos(t) - x1_0 * math.sin(t)

def r_function(t):
    return Matrix([[0], [0]])

def calculate_cumulative_error(numerical_results, x1_0, x2_0):
    cumulative_error_x1, cumulative_error_x2 = 0.0, 0.0
    
    for result in numerical_results:
        t = result[0]
        x1_num, x2_num = result[1], result[2]
        x1_analytical,x2_analytical = analytical_solution(t, x1_0, x2_0)
        
        cumulative_error_x1 += abs(x1_num - x1_analytical)
        cumulative_error_x2 += abs(x2_num - x2_analytical)
    
    return cumulative_error_x1, cumulative_error_x2

def task1():
    A = Matrix([[0, 1], 
                [-1, 0]])
    
    B = Matrix([[0, 0], 
                [0, 0]])
    
    x0 = Matrix([[1], 
                 [1]])
    
    T = 0.01 
    t_max = 10
    
    print("1:")
    
    print_every = 100
    
    print("\n1. EULEROV POSTUPAK:")
    euler_results = euler_solve(A, B, x0, T, t_max, r_function, print_every)
    euler_error_x1, euler_error_x2 = calculate_cumulative_error(euler_results, x0[0,0], x0[1,0])
    print(f"Cumulative error:\t{euler_error_x1:.5f};\t{euler_error_x2:.5f}")
    
    print("\n\n2. OBRNUTI EULEROV POSTUPAK:")    
    inverse_euler_results = inverse_euler_solve(A, B, x0, T, t_max, r_function, print_every)
    inverse_euler_error_x1, inverse_euler_error_x2 = calculate_cumulative_error(inverse_euler_results, x0[0,0], x0[1,0])
    print(f"Cumulative error:\t{inverse_euler_error_x1:.5f};\t{inverse_euler_error_x2:.5f}")
    
    print("\n\n3. TRAPEZNI POSTUPAK:")
    trapezoidal_results = trapezoidal_solve(A, B, x0, T, t_max, r_function, print_every)
    trapezoidal_error_x1, trapezoidal_error_x2 = calculate_cumulative_error(trapezoidal_results, x0[0,0], x0[1,0])
    print(f"Cumulative error:\t{trapezoidal_error_x1:.5f};\t{trapezoidal_error_x2:.5f}")
    
    print("\n\n4. RUNGE-KUTTA 4. REDA:")
    rk4_results = rk4_solve(A, B, x0, T, t_max, r_function, print_every)
    rk4_error_x1, rk4_error_x2 = calculate_cumulative_error(rk4_results, x0[0,0], x0[1,0])
    print(f"Cumulative error:\t{rk4_error_x1:.5f};\t{rk4_error_x2:.5f}")
    
    print("\n\n5. PE(CE)² (Euler, Obrnuti Euler):")
    pece1_results = predictor_corrector_solve(A, B, x0, T, t_max, r_function, method='inverse_euler', num_corrections=2, print_every=print_every)
    pece1_error_x1, pece1_error_x2 = calculate_cumulative_error(pece1_results, x0[0,0], x0[1,0])
    print(f"Cumulative error:\t{pece1_error_x1:.5f};\t{pece1_error_x2:.5f}")
    
    print("\n\n6. PECE (Euler, Trapezni):")
    pece2_results = predictor_corrector_solve(A, B, x0, T, t_max, r_function, method='trapezoidal', num_corrections=1, print_every=print_every)
    pece2_error_x1, pece2_error_x2 = calculate_cumulative_error(pece2_results, x0[0,0], x0[1,0])
    print(f"Cumulative error:\t{pece2_error_x1:.5f};\t{pece2_error_x2:.5f}")

if __name__ == "__main__":
    task1()
