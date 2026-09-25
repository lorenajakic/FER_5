from pathlib import Path
from matrix import Matrix

BASE_DIR = Path(__file__).parent

def load_matrix_and_vector(mat_file, vec_file, transpose_vec=True):
    A = Matrix.from_file(BASE_DIR / mat_file)
    A_copy = A.copy()
    b = Matrix.from_file(BASE_DIR / vec_file)
    if transpose_vec:
        b = ~b
    b_copy = b.copy()
    return A, A_copy, b, b_copy

def solve_system(A, b, use_pivoting=True):
    try:
        return A.solve_linear_system(b, use_pivoting=use_pivoting)
    except Exception as e:
        print(f"Error: {e}")
        return None

def print_solution(x):
    if x is not None:
        print(x.more_decimals())
        print()

if __name__ == "__main__":
    print("Zadatak 1: ")
    # potrebno je koristiti abs(self[i, j] - other[i, j]) > self.EPSILON radi preciznosti
    A = Matrix([[1.3, 2.32], [3.32, 4.32]])
    factor = 1.587428354

    B = (A * factor) * (1 / factor)
    print(A.more_decimals())
    print(B.more_decimals())
    print("A == B:", A == B) 
    print()

    print("Zadatak 2:")
    A, A_copy, b, b_copy = load_matrix_and_vector("zad_2_matrica.txt", "zad_2_b.txt")
    solve_system(A, b, use_pivoting=False)
    solve_system(A_copy, b_copy, use_pivoting=True)
    print()

    print("Zadatak 3:")
    A, A_copy, b, b_copy = load_matrix_and_vector("zad_3_matrica.txt", "zad_3_b.txt")
    solve_system(A, b, use_pivoting=False)
    solve_system(A_copy, b_copy, use_pivoting=True)
    print()

    print("Zadatak 4:")
    A, A_copy, b, b_copy = load_matrix_and_vector("zad_4_matrica.txt", "zad_4_b.txt")
    x1 = solve_system(A, b, use_pivoting=False)
    x2 = solve_system(A_copy, b_copy, use_pivoting=True)
    print_solution(x1)
    print_solution(x2)

    print("Zadatak 5:")
    A, _, b, _ = load_matrix_and_vector("zad_5_matrica.txt", "zad_5_b.txt")
    solve_system(A, b, use_pivoting=True)

    print("Zadatak 6:")
    A, A_copy, b, b_copy = load_matrix_and_vector("zad_6_matrica.txt", "zad_6_b.txt")
    solve_system(A, b, use_pivoting=False)
    solve_system(A_copy, b_copy, use_pivoting=True)

    # dijelimo svaki redak max vrijednoscu tog retka
    B = Matrix([[(1 / 4000000000), 0, 0], [0, (1 / 7), 0], [0, 0, (1 / 0.0000000005)]])

    solve_system(B @ A_copy, B @ b_copy, use_pivoting=True)

    print("Zadatak 7:")
    A = Matrix.from_file(BASE_DIR / "zad_7.txt")
    try:
        A_inv = A.inverse()
        print(A_inv)
    except Exception as e:
        print(f"Error: {e}")
    print()

    print("Zadatak 8:")
    A = Matrix.from_file(BASE_DIR / "zad_8_9.txt")
    try:
        inverse = A.inverse()
        print(inverse)
    except Exception as e:
        print(f"Error: {e}")

    print("Zadatak 9:")
    A = Matrix.from_file(BASE_DIR / "zad_8_9.txt")
    try:
        print(A.determinant())
    except Exception as e:
        print(f"Error: {e}")
    
    print("Zadatak 10:")
    A = Matrix.from_file(BASE_DIR / "zad_10.txt")
    try:
        print(A.determinant())
    except Exception as e:
        print(f"Error: {e}")
