from f import FunctionWithCounter, f_4
from simplex import nelder_mead
from hooke_jeeves import hooke_jeeves

def task3(): 
    x0 = [5.0, 5.0]
    f = FunctionWithCounter(f_4)
    print(f"Starting point: {x0}")
    print(f"Expected minimum: [0.0, 0.0], f(x) = 0.0")
    
    print("\nHOOKE-JEEVES")
    f.reset()
    result = hooke_jeeves(f, x0, dx=0.5, epsilon=1e-6, output=False)
    print(f"Result: {result}")
    print(f"f(x) = {f(result):.6f}")
    print(f"Evaluations: {f.evals}")
    
    print("\nNELDER-MEAD SIMPLEX")
    f.reset()
    result = nelder_mead(f, x0, step=1.0, epsilon=1e-6, output=False)
    print(f"Result: {result}")
    print(f"f(x) = {f(result):.6f}")
    print(f"Evaluations: {f.evals}")

if __name__ == "__main__":
    task3()

