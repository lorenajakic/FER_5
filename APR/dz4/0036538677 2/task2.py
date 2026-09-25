from penalty_barrier_method import penalty_barrier_method
from load_from_file import load_config
from constraint import Constraints
from f import f_1, f_2


def g1(x):
    return x[1] - x[0]
    
def g2(x):
    return 2 - x[0]

def task2(): 
    constraints = Constraints(explicit_bounds=None, implicit_constraints=[g1, g2], equality_constraints=[])
    epsilon, _, t0= load_config('config.txt')
    
    try:
        result_1 = penalty_barrier_method(f=f_1, constraints=constraints, t0=t0, x0=[-1.9, 2.0], epsilon=epsilon)
        print(f"\nRezultat za funkciju 1:")
        print(f"Minimum na x = {result_1}")
        print(f"f(x) = {f_1(result_1):.6f}")
    except Exception as e:
        print(e)
    
    try:
        result_2 = penalty_barrier_method( f=f_2, constraints=constraints, t0=t0, x0=[0.1, 0.3], epsilon=epsilon)
        print(f"\nRezultat za funkciju 1:")
        print(f"Minimum na x = {result_2}")
        print(f"f(x) = {f_2(result_2):.6f}")
    except Exception as e:
        print(e)

    try:
        result_3 = penalty_barrier_method( f=f_1, constraints=constraints, t0=t0, x0=[0, 2], epsilon=epsilon)
        print(f"\nRezultat za funkciju 1:")
        print(f"Minimum na x = {result_3}")
        print(f"f(x) = {f_1(result_3):.6f}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    task2()