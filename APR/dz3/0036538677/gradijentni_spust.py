import numpy as np
from golden_ratio import golden_ratio
from unimodal import unimodal

def gradijentni_spust(f, grad_f, x0, e=1e-6, use_golden_section=False, output=False):
    x = np.array(x0, dtype=float)
    iteration = 0
    
    while True:
        grad = np.array(grad_f(x))
        grad_norm = np.linalg.norm(grad)
        
        if use_golden_section:
            def f_lambda(lambda_val):
                return f(x - lambda_val * grad)
            
            h = 0.1 
            try:
                a, b = unimodal(0.0, h, f_lambda)
                if a >= b:
                    raise ValueError("Nevaljan interval")
            except:
                # Fallback: ručno pronalaženje unimodalnog intervala
                # Tražimo interval gdje funkcija pada u smjeru negativnog gradijenta
                f0 = f_lambda(0.0)  # Vrijednost funkcije u trenutnoj točki
                
                # Probajmo pozitivne lambda (što znači idemo u smjeru -grad)
                lambda_test = h
                f_test = f_lambda(lambda_test)
                
                if f_test < f0:
                    # Funkcija pada u smjeru negativnog gradijenta - proširimo interval
                    a = 0.0
                    b = lambda_test
                    while True:
                        lambda_new = b * 2
                        f_new = f_lambda(lambda_new)
                        if f_new < f_lambda(b):
                            # Funkcija još pada, proširimo interval
                            b = lambda_new
                        else:
                            # Funkcija počinje rasti, našli smo desnu granicu
                            break
                        if b > 1000:  # Zaštita od beskonačnog rasta
                            break
                else:
                    # Funkcija ne pada u smjeru -grad, možda smo blizu minimuma
                    # Koristimo mali interval oko 0
                    a, b = 0.0, h
            
            lambda_opt = golden_ratio(a, b, e, f_lambda, output=False)
            step = -lambda_opt * grad
        else:
            step = -grad
        
        x = x + step
        iteration += 1
        
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

