import numpy as np
from f import FunctionWithCounter, f_5
from simplex import nelder_mead

def task5():    
    num_trials = 100
    success_threshold = 1e-4
    successes = 0
            
    for i in range(num_trials):
        x0 = np.random.uniform(-50, 50, 2).tolist()
        
        f = FunctionWithCounter(f_5)
        result = nelder_mead(f, x0, step=1.0, epsilon=1e-6, output=False)
        f_val = f(result)
        
        if f_val < success_threshold:
            successes += 1
    
    print(f"Successes: {successes}/{num_trials}")
    print(f"Success rate: {successes/num_trials * 100:.2f}%")

if __name__ == "__main__":
    task5()

