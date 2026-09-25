from constraint import Constraints
from box import box_method
from f import f_1, f_2

from load_from_file import load_config


def g1(x):
    return x[1] - x[0]
    
def g2(x):
    return 2 - x[0]

def task1():
    explicit_bounds = [(-100, 100), (-100, 100)]
    constraints = Constraints(explicit_bounds=explicit_bounds, implicit_constraints=[g1, g2])

    epsilon, alfa, _ = load_config('config.txt')

    try: 
        result = box_method(f=f_1, x0=(-1.9, 2), constraints=constraints, alpha=alfa, epsilon=epsilon)
        print(f"\nRezultat za funkciju 1:")
        print(f"Minimum na x = {result}")
        print(f"f(x) = {f_1(result):.6f}")
    except Exception as e:
        print(e)
     
    try:
        result = box_method(f=f_2, x0=(0.1, 0.3), constraints=constraints, alpha=alfa, epsilon=epsilon)
        print(f"\nRezultat za funkciju 2:")
        print(f"Minimum na x = {result}")
        print(f"f(x) = {f_2(result):.6f}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    task1()