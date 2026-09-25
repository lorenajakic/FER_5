"""
Ana želi kupiti poklon najboljoj prijateljici za rođendan. Kao moguće poklone razmatra torbicu, šminku, parfem i nakit.
Prilikom odlučivanja, u obzir uzima tri kriterija: cijenu, korisnost i izgled poklona.
S obzirom na kriterije, Ana ima sljedeće preferencije:
Korisnost ima jaku prednost pred cijenom. Izgled ima slabu prednost pred cijenom. Korisnost ima slabu prednost pred izgledom.

U odnosu na kriterij cijene, Ana procjenjuje:
Šminka ima jaku prednost pred torbicom te slabu do jaku prednost pred parfemom i nakitom.
Parfem i nakit su po cijeni otprilike jednaki te oboje imaju slabu prednost pred torbicom.

S obzirom na korisnost, Ana smatra:
Torbica ima jaku prednost pred šminkom, vrlo jaku prednost pred parfemom te apsolutnu prednost pred nakitom.
Šminka je srednje korisna: ima jaku prednost pred parfemom te vrlo jaku prednost pred nakitom.
Parfem ima slabu do jaku prednost pred nakitom.

S obzirom na izgled, Ana procjenjuje:
Nakit ima jaku prednost pred torbicom i parfemom te vrlo jaku prednost pred šminkom.
Parfem je jednako je atraktivan kao šminka.
Torbica ima slabu prednost pred šminkom i parfemom.
"""

import numpy as np

EPS = 5e-5
RI = {3: 0.58, 4: 0.90}

kriteriji = ["Cijena", "Korisnost", "Izgled"]
alternative = ["Torbica", "Šminka", "Parfem", "Nakit"]

A_k = np.array([
    [1,   1/5, 1/3], # Cijena
    [5,   1,   3  ], # Korisnost
    [3,   1/3, 1  ]  # Izgled
])

A_cijena = np.array([
    [1,   1/5, 1/3, 1/3],  # Torbica
    [5,   1,   4,   4  ],  # Šminka
    [3,   1/4, 1,   1  ],  # Parfem
    [3,   1/4, 1,   1  ]   # Nakit
])

A_korisnost = np.array([
    [1,   5,   7,   9  ],  # Torbica
    [1/5, 1,   5,   7  ],  # Šminka
    [1/7, 1/5, 1,   4  ],  # Parfem
    [1/9, 1/7, 1/4, 1  ]   # Nakit
])

A_izgled = np.array([
    [1,   3,   3,   1/5],  # Torbica
    [1/3, 1,   1,   1/7],  # Šminka
    [1/3, 1,   1,   1/5],  # Parfem
    [5,   7,   5,   1  ]   # Nakit
])


def metoda_potencija(A):
    n = A.shape[0]
    y = np.ones(n)

    while True:
        x = y / np.linalg.norm(y, 2)
        y = A @ x
        lam = x @ y
        if np.linalg.norm(y - lam * x, 2) < EPS: break

    w = x / np.sum(x)
    return lam, w

def provjeri_matricu(A, ime):
    vals, vecs = np.linalg.eig(A)

    idx = np.argmax(np.real(vals))
    lam_eig = np.real(vals[idx])
    v_eig = np.real(vecs[:, idx])
    w_eig = v_eig / np.sum(v_eig)

    lam_pow, w_pow = metoda_potencija(A)

    print(f"\nProvjera za {ime}")
    print("λ_max (potencije)   =", round(lam_pow, 6))
    print("λ_max (eig)         =", round(lam_eig, 6))
    print("Razlika λ           =", abs(lam_pow - lam_eig))
    print("w (potencije)       =", np.round(w_pow, 6))
    print("w (eig)             =", np.round(w_eig, 6))
    print("||w_pow - w_eig||_2 =", np.linalg.norm(w_pow - w_eig))

lam_k, w_k = metoda_potencija(A_k)

CI = (lam_k - 3) / 2
CR = CI / RI[3]

print("Matrica kriterija:")
print(A_k)
print("\nλ_max =", round(lam_k,4))
print("w =", np.round(w_k,4))
print("CI =", round(CI,4), "CR =", round(CR,4))

if CR < 0.1: print("Podaci su konzistentni.\n")
else:print("Podaci nisu konzistentni.\n")

print("Najvažniji kriterij je:", kriteriji[np.argmax(w_k)])

matrice = [A_cijena, A_korisnost, A_izgled]
W = np.zeros((4,3))

for i in range(3):
    lam, w = metoda_potencija(matrice[i])
    W[:, i] = w
    print(f"\nS obzirom na {kriteriji[i]}:")
    print("λ_max =", round(lam,4))
    print("w     =", np.round(w,4))
    print("Najbolja alternativa:", alternative[np.argmax(w)])

v = W @ w_k

print("\nZavršna matrica prioriteta:")
print(np.round(W,4))

print("\nGlobalni prioriteti:")
print(np.round(v,4))

print("\nPrema dobivenim rezultatima, najbolji izbor je:", alternative[np.argmax(v)])

provjeri_matricu(A_k, "kriterije")
provjeri_matricu(A_cijena, "cijenu")
provjeri_matricu(A_korisnost, "korisnost")
provjeri_matricu(A_izgled, "izgled")
