def unimodal(start_point, h, f):
    l, r = start_point - h, start_point + h
    m = start_point
    step = 1

    fm, fl, fr = f(m), f(l), f(r)

    if fm < fr and fm < fl: return l, r
    
    elif fm > fr:
        while fm > fr:
            l = m
            m = r
            fm = fr
            step *= 2
            r = start_point + h * step
            fr = f(r)
        return l, r

    else:
        while fm > fl:
            r = m
            m = l
            fm = fl
            step *= 2
            l = start_point - h * step
            fl = f(l)
        return l, r