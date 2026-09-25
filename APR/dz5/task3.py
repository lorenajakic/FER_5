from matrix import Matrix
from euler import euler_solve
from inverzni_euler import inverse_euler_solve
from trapezni_euler import trapezoidal_solve
from runge_kutta import rk4_solve
from predictor_corrector import predictor_corrector_solve

def r_function(t):
    return Matrix([[1], [1]])

def task3():
    A = Matrix([[0, -2], 
                [1, -3]])
    
    B = Matrix([[2, 0], 
                [0, 3]])
    
    x0 = Matrix([[1], 
                 [3]])
    
    T = 0.01
    t_max = 10
    
    print("3:")
    
    print_every = 100
    
    print("\n1. EULEROV POSTUPAK:")
    euler_solve(A, B, x0, T, t_max, r_function, print_every)
    
    print("\n\n2. OBRNUTI EULEROV POSTUPAK:")
    inverse_euler_solve(A, B, x0, T, t_max, r_function, print_every)
    
    print("\n\n3. TRAPEZNI POSTUPAK:")
    trapezoidal_solve(A, B, x0, T, t_max, r_function, print_every)
    
    print("\n\n4. RUNGE-KUTTA 4. REDA:")
    rk4_solve(A, B, x0, T, t_max, r_function, print_every)
    
    print("\n\n5. PE(CE)² (Euler, Obrnuti Euler):")
    predictor_corrector_solve(A, B, x0, T, t_max, r_function, method='inverse_euler', num_corrections=2, print_every=print_every)
    
    print("\n\n6. PECE (Euler, Trapezni):")
    predictor_corrector_solve(A, B, x0, T, t_max, r_function, method='trapezoidal', num_corrections=1, print_every=print_every)

if __name__ == "__main__":
    task3()
