import numpy as np
from math import sqrt


def unimodal(start_point, h, f):
    """
    Pronalazi unimodalni interval oko početne točke.
    
    Args:
        start_point: Početna točka
        h: Korak za pretraživanje
        f: Funkcija za minimizaciju
    
    Returns:
        (a, b): Unimodalni interval [a, b]
    """
    l, r = start_point - h, start_point + h
    m = start_point
    step = 1

    fm, fl, fr = f(m), f(l), f(r)

    if fm < fr and fm < fl:
        return l, r
    
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


def golden_ratio(a, b, e, f, output=False):
    """
    Metoda zlatnog reza za pronalaženje minimuma funkcije na intervalu [a, b].
    
    Args:
        a: Početak intervala
        b: Kraj intervala
        e: Preciznost
        f: Funkcija za minimizaciju
        output: Ako je True, ispisuje korake
    
    Returns:
        Optimalna vrijednost λ
    """
    k = 0.5 * (sqrt(5) - 1)

    c = b - k * (b - a)
    d = a + k * (b - a)
    
    fc, fd = f(c), f(d)

    step = 0
    while (b - a) > e:
        if output:
            print(f"{step:2d}: a={a:.6f}, b={b:.6f}, c={c:.6f}, d={d:.6f}, f(c)={fc:.6f}, f(d)={fd:.6f}")

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


def gradijentni_spust(f, grad_f, x0, e=1e-6, use_golden_section=False, output=False):
    """
    Metoda gradijentnog spusta za minimizaciju funkcije.
    
    Args:
        f: Funkcija koja se minimizira (f: R^n -> R)
        grad_f: Funkcija koja računa gradijent (grad_f: R^n -> R^n)
        x0: Početna točka (numpy array ili lista)
        e: Željena preciznost (euklidska norma gradijenta)
        use_golden_section: Ako je True, koristi metodu zlatnog reza za određivanje optimalnog koraka
        output: Ako je True, ispisuje informacije o iteracijama
    
    Returns:
        x: Točka minimuma
    """
    x = np.array(x0, dtype=float)
    iteration = 0
    
    while True:
        # Računanje gradijenta
        grad = np.array(grad_f(x))
        grad_norm = np.linalg.norm(grad)
        
        if output:
            print(f"Iteracija {iteration}: x = {x}, f(x) = {f(x):.6f}, ||∇f(x)|| = {grad_norm:.6f}")
        
        # Provjera uvjeta zaustavljanja
        if grad_norm < e:
            break
        
        # Određivanje koraka
        if use_golden_section:
            # Metoda zlatnog reza za određivanje optimalnog koraka
            # Tražimo λ koje minimizira f(x - λ * grad)
            # (negativan gradijent jer idemo u smjeru najbržeg pada)
            def f_lambda(lambda_val):
                return f(x - lambda_val * grad)
            
            # Pronalazimo unimodalni interval oko 0
            # Koristimo unimodal funkciju koja traži interval oko početne točke
            h = 0.1  # Manji početni korak
            try:
                a, b = unimodal(0.0, h, f_lambda)
                # Provjeravamo da li je interval valjan
                if a >= b:
                    raise ValueError("Nevaljan interval")
            except:
                # Ako unimodal ne radi, koristimo jednostavniji pristup
                # Tražimo interval gdje funkcija pada u smjeru negativnog gradijenta
                f0 = f_lambda(0.0)
                
                # Probajmo pozitivne vrijednosti (što znači idemo u smjeru -grad)
                lambda_test = h
                f_test = f_lambda(lambda_test)
                
                if f_test < f0:
                    # Funkcija pada, proširimo interval dok pada
                    a = 0.0
                    b = lambda_test
                    while True:
                        lambda_new = b * 2
                        f_new = f_lambda(lambda_new)
                        if f_new < f_lambda(b):
                            b = lambda_new
                        else:
                            break
                        if b > 1000:  # Zaštita od beskonačnog rasta
                            break
                else:
                    # Funkcija raste, probajmo negativne vrijednosti
                    lambda_test = -h
                    f_test = f_lambda(lambda_test)
                    if f_test < f0:
                        a = lambda_test
                        b = 0.0
                        while True:
                            lambda_new = a * 2
                            f_new = f_lambda(lambda_new)
                            if f_new < f_lambda(a):
                                a = lambda_new
                            else:
                                break
                            if a < -1000:  # Zaštita od beskonačnog pada
                                break
                    else:
                        # Funkcija raste u oba smjera, koristimo mali interval oko 0
                        # To znači da smo možda već blizu minimuma
                        a, b = -h, h
            
            # Pronalazimo optimalni λ metodom zlatnog reza
            lambda_opt = golden_ratio(a, b, e, f_lambda, output=False)
            step = -lambda_opt * grad
        else:
            # Prvi način: pomičemo se za čitav iznos nenormiranog vektora gradijenta
            # Za gradijentni spust, idemo u smjeru suprotnom od gradijenta
            step = -grad
        
        # Ažuriranje točke
        x = x + step
        iteration += 1
        
        # Zaštita od beskonačne petlje
        if iteration > 10000:
            if output:
                print("Upozorenje: Dosegnut maksimalan broj iteracija!")
            break
    
    if output:
        print(f"\nKonvergencija postignuta nakon {iteration} iteracija")
        print(f"Finalna točka: x = {x}")
        print(f"f(x) = {f(x):.6f}")
        print(f"||∇f(x)|| = {np.linalg.norm(grad_f(x)):.6f}")
    
    return x


def main():
    """
    Glavna funkcija koja omogućava konfiguraciju bez prevođenja programa.
    """
    print("=" * 60)
    print("METODA GRADIJENTNOG SPUSTA")
    print("=" * 60)
    
    # Unos preciznosti
    e_input = input("Unesite mjeru preciznosti ε (default: 1e-6): ").strip()
    e = float(e_input) if e_input else 1e-6
    
    # Unos početne točke
    x0_str = input("Unesite početnu točku (npr. '1,2,3' ili '1' za 1D): ").strip()
    if ',' in x0_str:
        x0 = [float(x.strip()) for x in x0_str.split(',')]
    else:
        x0 = [float(x0_str)]
    
    # Unos načina rada
    print("\nOdaberite način rada:")
    print("1 - Pomicanje za čitav iznos nenormiranog vektora gradijenta")
    print("2 - Korištenje metode zlatnog reza za određivanje optimalnog koraka")
    choice = input("Unesite izbor (1 ili 2, default: 1): ").strip()
    use_golden_section = (choice == '2')
    
    # Unos funkcije i gradijenta
    print("\nNapomena: Funkcija i gradijent moraju biti implementirani u kodu.")
    print("Za testiranje, koristite primjer funkcije.")
    
    # Primjer funkcije za testiranje: f(x) = x1^2 + x2^2 + ... + xn^2
    # Gradijent: ∇f(x) = [2*x1, 2*x2, ..., 2*xn]
    def example_f(x):
        """Primjer: f(x) = x1^2 + x2^2 + ... + xn^2"""
        return np.sum(np.array(x) ** 2)
    
    def example_grad_f(x):
        """Gradijent primjer funkcije: ∇f(x) = 2*x"""
        return 2 * np.array(x)
    
    use_example = input("\nKoristiti primjer funkcije f(x) = x1^2 + x2^2 + ...? (d/n, default: d): ").strip().lower()
    
    if use_example in ['', 'd', 'da', 'y', 'yes']:
        f = example_f
        grad_f = example_grad_f
        print("Koristi se primjer funkcije: f(x) = x1^2 + x2^2 + ...")
    else:
        print("Molimo implementirajte funkciju 'f' i 'grad_f' u kodu.")
        return
    
    # Unos opcije za ispis koraka
    show_output = input("Želite li ispisivati korake iteracija? (d/n, default: n): ").strip().lower()
    output = show_output in ['d', 'da', 'y', 'yes']
    
    print("\n" + "=" * 60)
    print("Pokretanje metode gradijentnog spusta...")
    print("=" * 60)
    
    # Pokretanje metode
    result = gradijentni_spust(f, grad_f, x0, e=e, use_golden_section=use_golden_section, output=output)
    
    print("\n" + "=" * 60)
    print("REZULTATI")
    print("=" * 60)
    print(f"Pronađena točka minimuma: {result}")
    print(f"Vrijednost funkcije: f(x) = {f(result):.10f}")
    print(f"Norma gradijenta: ||∇f(x)|| = {np.linalg.norm(grad_f(result)):.10f}")
    print("=" * 60)


if __name__ == "__main__":
    main()

