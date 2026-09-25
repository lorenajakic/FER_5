import numpy as np
class Matrix:
    EPSILON = 1e-9
    def __init__(self, data):
        self.data = data
        self.rows = len(data)
        self.cols = len(data[0])
        self.number_of_swaps = 0

    def __getitem__(self, indices):
        i, j = indices
        return self.data[i][j]

    def __setitem__(self, indices, value):
        i, j = indices
        self.data[i][j] = value

    def __add__(self, other):
        res = self.empty_matrix(self.rows, self.cols)
        for i in range(self.rows):
            for j in range(self.cols):
                res[i, j] = self[i, j] + other[i, j]
        return res
    
    def __iadd__(self, other):
        for i in range(self.rows):
            for j in range(self.cols):
                self[i, j] += other[i, j]
        return self

    def __sub__(self, other):
        res = self.empty_matrix(self.rows, self.cols)
        for i in range(self.rows):
            for j in range(self.cols):
                res[i, j] = self[i, j] - other[i, j]
        return res
    
    def __isub__(self, other):
        for i in range(self.rows):
            for j in range(self.cols):
                self[i, j] -= other[i, j]
        return self

    def __mul__(self, scalar):
        res = self.empty_matrix(self.rows, self.cols)
        for i in range(self.rows):
            for j in range(self.cols):
                res[i, j] = self[i, j] * scalar
        return res

    def __rmul__(self, scalar):
        return self.__mul__(scalar)
    
    def __matmul__(self, other):
        if self.cols != other.rows:
            raise ValueError()
        
        res = self.empty_matrix(self.rows, other.cols)
        for i in range(self.rows):
            for j in range(other.cols):
                s = 0.0
                for k in range(self.cols):
                    s += self[i, k] * other[k, j]
                res[i, j] = s
        return res

    def __invert__(self):
        res = self.empty_matrix(self.cols, self.rows)
        for i in range(self.rows):
            for j in range(self.cols):
                res[j, i] = self[i, j]
        return res

    def __eq__(self, other):
        if self.rows != other.rows or self.cols != other.cols:
            return False
        for i in range(self.rows):
            for j in range(self.cols):
                if abs(self[i, j] - other[i, j]) > self.EPSILON:
                    return False
        return True
    
    def __str__(self):
        result = ""
        for row in self.data:
            result += " ".join(f"{element:10.6g}" for element in row)
            result += "\n"
        return result
    
    @classmethod
    def from_file(cls, path):
        data = []
        with open(path, "r") as f:
            for line in f:
                row = [float(x) for x in line.split()]
                data.append(row)
        return cls(data) 
    
    def save_to_file(self, path):
        with open(path, "w") as f:
            for row in self.data:
                line = " ".join(f"{element}" for element in row)
                f.write(line + "\n")
    
    def more_decimals(self):
        result = ""
        for row in self.data:
            result += " ".join(f"{element:5.30g}" for element in row)
            result += "\n"
        return result

    def forward_substitution(self, b):    
        for i in range(self.rows - 1):
            for j in range(i + 1, self.rows):
                b[j, 0] -= self[j, i] * b[i, 0]
        
        return b

    def backward_substitution(self, b):
        for i in range(self.rows - 1, -1, -1):
            if abs(self[i, i]) < self.EPSILON: raise ValueError(f"Zero or very small pivot number: {i}, {i}")

            b[i, 0] /= self[i, i]
            
            for j in range(i):
                b[j, 0] -= self[j, i] * b[i, 0]
        
        return b

    def lu_decomposition(self):
        for i in range(self.rows - 1): 
            if abs(self[i, i]) < self.EPSILON: raise ValueError(f"Zero or very small pivot at ({i}, {i}): {self[i, i]}")

            for j in range(i + 1, self.rows):                 
                self[j, i] /= self[i, i]
                
                for k in range(i + 1, self.rows):
                    self[j, k] -= self[j, i] * self[i, k]
        return self

    def lup_decomposition(self):
        P = list(range(self.rows))

        for i in range(self.rows - 1):
            pivot = i
            for j in range(i + 1, self.rows):
                if abs(self[j, i]) > abs(self[pivot, i]):
                    pivot = j

            if abs(self[pivot, i]) < self.EPSILON: raise ValueError(f"Zero or very small pivot at ({pivot}, {i}): {self[pivot, i]}")

            if pivot != i:
                self.data[i], self.data[pivot] = self.data[pivot], self.data[i]
                P[i], P[pivot] = P[pivot], P[i]
                self.number_of_swaps += 1

            for j in range(i + 1, self.rows):
                self[j, i] /= self[i, i]
                for k in range(i + 1, self.rows):
                    self[j, k] -= self[j, i] * self[i, k]

        self.permutation_vector = P
        return self

    
    def solve_linear_system(self, b, use_pivoting=True):
        print("Matrix: \n", self, "\n", sep="")
        print("b: \n", b, "\n", sep="")

        if use_pivoting:
            self.lup_decomposition()
            b_permuted = Matrix([b.data[self.permutation_vector[i]] for i in range(b.rows)])

        else:
            self.lu_decomposition()
            b_permuted = b

        print("Matrix after decompostion: \n", self, "\n", sep="")

        y = self.forward_substitution(b_permuted)
        print("y: \n", y, "\n", sep="")

        x = self.backward_substitution(y)
        print("x: \n", x, "\n", sep="")    

        return x
    
    def inverse(self):
        self.lup_decomposition()
            
        identity = self.identity_matrix()
        inverse = self.empty_matrix(self.rows, self.rows)
            
        for j in range(self.rows):
            e = [identity[i, j] for i in range(self.rows)]
                        
            b = Matrix([[e[self.permutation_vector[i]]] for i in range(self.rows)])

            y = self.forward_substitution(b)
                
            x = self.backward_substitution(y)
                
            for i in range(self.rows):
                inverse[i, j] = x[i, 0]
            
        return inverse
    
    def determinant(self):
        A_copy = self.copy()
        A_copy.lup_decomposition()
        
        det = 1.0
        for i in range(self.rows):
            det *= A_copy[i, i]
        
        return (-1) ** self.number_of_swaps * det
    
    def identity_matrix(self):
        return Matrix([[1.0 if i == j else 0.0 for j in range(self.rows)] for i in range(self.rows)])

    def empty_matrix(self, rows, cols):
        return Matrix([[0.0 for _ in range(cols)] for _ in range(rows)])    
    
    def copy(self):
        return Matrix([row[:] for row in self.data])
