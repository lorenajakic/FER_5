# IEEE 754 – minimalni bitovi, 15.5 + 0.75

## 1. Minimalni bitovi za 24 i 25 bez pogreške

**Normalizirani zapis:** broj = (−1)^s × 1.f × 2^e (implicitna vodeća 1).

- **24** = 11000₂ = **1.1** × 2⁴ → eksponent 4, frakcija **.1** (1 bit)
- **25** = 11001₂ = **1.1001** × 2⁴ → eksponent 4, frakcija **.1001** (4 bita)

Da se **.1001** točno zapise, frakcija mora imati **najmanje 4 bita**.

Eksponent 4 mora biti predstavljiv. Za 0.75 kasnije trebamo eksponent −1, pa raspon eksponenta mora uključivati barem [−1, 4]. S pomakom (bias) 2^(e−1) − 1:
- **e = 3** → bias = 3, pohranjeni eksponenti 0..7 → stvarni eksponenti **−3 do 4** ✓

**Zaključak:** minimalno **3 bita za eksponent**, **4 bita za frakciju** (ukupno 1 + 3 + 4 = **8 bita**).

Format: **1 bit predznak | 3 bita eksponent (bias 3) | 4 bita frakcija**.

---

## 2. Zapis 15.5 i 0.75

**15.5** = 1111.1₂ = **1.1111** × 2³  
→ predznak 0, eksponent 3 → pohranjen 3+3 = **6** = 110₂, frakcija **1111**  
→ **0 110 1111**

**0.75** = 0.11₂ = **1.1** × 2⁻¹  
→ predznak 0, eksponent −1 → pohranjen −1+3 = **2** = 010₂, frakcija **1000** (.1 + padding)  
→ **0 010 1000**

---

## 3. Zbrajanje

Poravnaj po većem eksponentu (3):

- 15.5 = 1.1111 × 2³  
- 0.75 = 1.1 × 2⁻¹ = **0.0011** × 2³ (pomak desno za 4 mjesta)

Zbrajanje significanda:
```
  1.1111
+ 0.0011
---------
 10.0010  × 2³
```

Normalizacija: 10.0010 × 2³ = **1.0001 × 2⁴**.

Eksponent 4 → pohranjen 4+3 = **7** = 111₂, frakcija **0001**.  
Rezultat u zapisu: **0 111 0001**.

---

## 4. Dekodiranje rezultata

**0 111 0001** → predznak 0, eksponent pohranjen 7 → stvarni 7−3 = 4, significand 1.0001  
→ vrijednost = **1.0001₂ × 2⁴** = (1 + 1/16) × 16 = **16.25**.

Provjera: 15.5 + 0.75 = **16.25** ✓
