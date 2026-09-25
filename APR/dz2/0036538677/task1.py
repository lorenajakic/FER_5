from f import FunctionWithCounter, f_task1
from golden_ratio import golden_ratio
from unimodal import unimodal
from coordinate_search import coordinate_search
from simplex import nelder_mead
from hooke_jeeves import hooke_jeeves

def task1():
    f = FunctionWithCounter(f_task1)
    
    x0 = 10.0
    e = 1e-6
    h = 1.0
    for x0 in [10]:
        print(f"\nStarting point: {x0}")
        
        print("GOLDEN RATIO METHOD")
        f.reset()
        a, b = unimodal(x0, h, f)
        result = golden_ratio(a, b, e, f, output=False)
        print(f"Minimum found: x = {result:.10f}, f(x) = {f(result):.10f}")
        print(f"Function evaluations: {f.evals}")
        
        print()
        print("COORDINATE SEARCH")
        f.reset()
        result = coordinate_search(f, [x0], e, h=h)
        print(f"Minimum found: x = {result[0]:.10f}, f(x) = {f(result):.10f}")
        print(f"Function evaluations: {f.evals}")
        
        print()
        print("NELDER-MEAD SIMPLEX")
        f.reset()
        result = nelder_mead(f, [x0], step=1, epsilon=e, output=False)
        print(f"Minimum found: x = {result[0]:.10f}, f(x) = {f(result):.10f}")
        print(f"Function evaluations: {f.evals}")
        
        print()
        print("HOOKE-JEEVES")
        f.reset()
        result = hooke_jeeves(f, [x0], dx=0.5, epsilon=e, output=False)
        print(f"Minimum found: x = {result[0]:.10f}, f(x) = {f(result):.10f}")
        print(f"Function evaluations: {f.evals}")
if __name__ == "__main__":
    task1()

