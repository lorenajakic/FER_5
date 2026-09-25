from penalty_barrier_method import penalty_barrier_method
from load_from_file import load_config
from constraint import Constraints
from f import f_4

def g1(x):
    return 3 - x[0] - x[1]
    
def g2(x):
    return 3 + 1.5 * x[0] - x[1]

def h1(x):
    return x[1] - 1

def task3():
    constraints = Constraints(explicit_bounds=None, implicit_constraints=[g1, g2], equality_constraints=[h1])
    epsilon, _, t0= load_config('config.txt')
    
    try:
        result_1 = penalty_barrier_method(f=f_4, constraints=constraints, t0=t0, x0=[5, 5], epsilon=epsilon)
        print(f"\nRezultat za funkciju 4:")
        print(f"Minimum na x = {result_1}")
        print(f"f(x) = {f_4(result_1):.6f}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    task3()