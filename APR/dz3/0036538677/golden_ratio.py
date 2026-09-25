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
