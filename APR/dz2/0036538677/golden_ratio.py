from math import sqrt
from f import f_task1
from unimodal import unimodal

def golden_ratio(a, b, e, f, output=False):
    k = 0.5 * (sqrt(5) - 1)

    c = b - k * (b - a)
    d = a + k * (b - a)
    
    fc, fd = f(c), f(d)

    step = 0
    while (b - a) > e:
        if output: print(f"{step:2d}: a={a:.6f}, b={b:.6f}, c={c:.6f}, d={d:.6f}, f(c)={fc:.6f}, f(d)={fd:.6f}")

        if fc < fd:
            b = d
            d = c
            c = b - k * (b - a)
            fd = fc
            fc = f(c)
        else:
            a = c
            c = d
            d = a + k * (b - a)
            fc = fd
            fd = f(d)

        step += 1

    return (a + b) / 2

def main(f):
    e = 1e-6

    print("Choose method:")
    print("1 - Starting point (automatic unimodal interval search)")
    print("2 - Predefined interval [a, b]")
    choice = int(input("Input: "))

    if choice == 1:
        point = float(input("Enter starting point: "))
        h = float(input("Enter step h (1): ") or 1.0)
        a, b = unimodal(point, h, f)
        print(f"Unimodal interval: [{a:.6f}, {b:.6f}]")
    else:
        a = float(input("Enter a: "))
        b = float(input("Enter b: "))
    
    e = float(input("Enter precision e (1e-6): ") or 1e-6)
    show_steps = input("Do you want to print steps? (y/n): ").lower().startswith("y")

    result = golden_ratio(a, b, e, f, output=show_steps)
    print(f"Function minimum at x = {result:.6f}, f(x) = {f(result):.6f}")

if __name__ == "__main__":
    main(f_task1)
