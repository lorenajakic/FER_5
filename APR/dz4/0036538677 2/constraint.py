import numpy as np

class Constraints:  
    def __init__(self, explicit_bounds=None, implicit_constraints=None, equality_constraints=None):
        self.explicit_bounds = explicit_bounds
        self.implicit_constraints = implicit_constraints or []
        self.equality_constraints = equality_constraints or []
    
    def check_explicit(self, x):
        if self.explicit_bounds is None: return True
        x = np.array(x)
        for i, (x_d, x_g) in enumerate(self.explicit_bounds):
            if x[i] < x_d or x[i] > x_g: return False
        return True
    
    def check_implicit(self, x):
        for g in self.implicit_constraints:
            if g(x) < 0: return False
        return True
    
    def check_equality(self, x, tolerance=1e-6):
        for h in self.equality_constraints:
            if abs(h(x)) > tolerance: return False
        return True