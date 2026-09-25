from f import FunctionWithCounter, f_1, f_2, f_3, f_4
from coordinate_search import coordinate_search
from simplex import nelder_mead
from hooke_jeeves import hooke_jeeves

def task2():
    functions = [
        ("f1", f_1, [-1.9, 2.0], [1.0, 1.0], 0.0),
        ("f2", f_2, [0.1, 0.3], [4.0, 2.0], 0.0),
        ("f3", lambda x: f_3(x), [0.0] * 5, [1.0, 2.0, 3.0, 4.0, 5.0], 0.0),
        ("f4", f_4, [5.1, 1.1], [0.0, 0.0], 0.0),
    ]
    
    methods = [
        ("Coordinate Search", coordinate_search),
        ("Nelder-Mead Simplex", nelder_mead),
        ("Hooke-Jeeves", hooke_jeeves),
    ]
    
    results = []
    
    for func_name, func, x0, expected_min, expected_val in functions:
        print()
        print(f"Function: {func_name}")
        print(f"Starting point: {x0}")
        print(f"Expected minimum: {expected_min}, f(x) = {expected_val}")
        print()
        
        for method_name, method_func in methods:
            f = FunctionWithCounter(func)
            f.reset()
            
            result = method_func(f, x0)
            f_val = f(result)
            evals = f.evals
                
            results.append({
                "function": func_name,
                "method": method_name,
                "result": result,
                "f_value": f_val,
                "evals": evals
            })    
    print()
    print(f"{'Function':<20} {'Method':<25} {'Evaluations':<15} {'f(x)':<15} {'Result':<15}")
    for r in results:
        print(f"{r['function']:<20} {r['method']:<25} {r['evals']:<15} {r['f_value']:<15.6f} {r['result']}")

if __name__ == "__main__":
    task2()

