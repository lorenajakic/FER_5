from f import FunctionWithCounter, f_1
from simplex import nelder_mead

def task4():
    x0 = [0.5, 0.5]
    steps = [1, 5, 10, 15, 20]

    for x0 in [[0.5, 0.5], [20.0, 20.0]]:
        print(f"\n{x0}")
        print(f"{'Step':<10} {'Result':<30} {'f(x)':<15} {'Evaluations':<15}")
    
        for step in steps:
            f = FunctionWithCounter(f_1)
            result = nelder_mead(f, x0, step=step, epsilon=1e-6, output=False)
            print(f"{step:<10} {str(result):<30} {f(result):<15.6f} {f.evals:<15}")

if __name__ == "__main__":
    task4()

