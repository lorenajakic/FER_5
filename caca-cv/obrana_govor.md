# Obrana diplomskog — agent u detalje + govor po slajdovima

## DIO 1: Kako agent radi (detaljno)

### Stanje (TripPlannerState)
Jedan `TypedDict` koji dijele svi čvorovi. Čvor vrati `Command(update={...}, goto="...")`, LangGraph to **spoji** u stanje i skoči na sljedeći čvor. Zato u `build_graph.py` postoje samo uvjetni bridovi iz `route_intent` — sve ostalo se usmjerava kroz `goto` unutar samih čvorova.

Što je u stanju:
- **Ulaz iz Railsa:** `trip`, `places`, `place_comments`, `current_plan`, `conversation_history`, `user_message`
- **Izvedeno:** `collected_context`, `intent`, `user_language`
- **Za pitanja korisniku:** `pending_intent`, `pending_slots`
- **Radno:** `accommodation_geo`, `excluded_places`, `candidates`, `validation_reports`, `repair_round`, `max_repair_rounds`
- **Izlaz:** `selected_candidate_id`, `score_report`, `constraint_report`, `message`, `structured_response`, `node_timings_ms`

**Pamćenje razgovora:** `MemorySaver` checkpointer + `thread_id = "trip-<id>"`. Zato agent kod sljedeće poruke još uvijek zna što je pitao (`pending_intent`/`pending_slots`).

### Dva modela
- `llm_fast` = **claude-haiku-4-5** → klasifikacija, izvlačenje želja, kratki odgovori, kuriranje ponuda
- `llm` = **claude-sonnet-4-6** → generiranje i popravak plana
- Fallback: **gemini-2.5-flash** (`with_fallbacks`)

⚠️ U radu piše `claude-3-5-haiku` i `gemini-1.5` — kod ima novije verzije. Na obrani se drži onoga što piše u radu.

---

### 1. `route_intent` — ulazna točka
1. `collect_context(state)` gradi kontekst:
   - `mandatory_place_names` = spremljena mjesta **minus** `excluded_places`
   - `comments_by_place` = komentari grupirani po mjestu
   - `arrival_cutoff` / `departure_cutoff` — iz `arrival_at`/`departure_at` + buffer po načinu prijevoza (**avion: 180 min prije / 120 min poslije**, ostalo 60/60)
   - `duration_days`, zadnjih 20 poruka
2. **Jezik:** heuristika (dijakritici + lista riječi) → `user_language` (hr/en)
3. **Ako je `pending_intent` postavljen** (korisnik odgovara na prethodno pitanje) → preskoči LLM, koristi zapamćenu namjeru
4. Inače `llm_fast` + `PydanticOutputParser(IntentClassification)` uz zadnjih 5 poruka → jedna od 6 namjera
5. Uvjetni bridovi → odgovarajući čvor

### 2. `plan_node` (novi plan)
Tri "vratara" prije generiranja, svaki može prekinuti tok i pitati korisnika:
1. **`_resolve_accommodation`:** ima adresu ali nema koordinate → (a) iskoristi spremljeni `accommodation_geo`, (b) izvuci koordinate iz Google Maps linka u poruci, (c) geokodiraj preko **Photon/OSM**. Ako ne uspije → postavi `pending_intent` i pita korisnika za detalje, `goto END`.
2. **Nema smještaja uopće** → jednokratna napomena ("dodaj smještaj pa ću plan složiti oko njega"), `goto END`.
3. **`_extract_plan_preferences`** (`llm_fast` → `PlanPreferences`: tempo/interesi/budžet). Ako ništa nije rečeno → jednokratno pita 3 neobavezna pitanja, `goto END`.

Kad sve prođe: ubaci `plan_preferences` u kontekst → `goto execute_plan_node`.

### 3. `refine_node` (izmjena plana)
Isto razrješavanje smještaja, **plus ključni korak `_detect_place_exclusions`**: `llm_fast` usporedi poruku s popisom obveznih mjesta i izdvoji ona koja korisnik želi izbaciti → makne ih iz `mandatory_place_names` i zapiše u `excluded_places`.
👉 **Ovo rješava problem iz rada:** bez toga bi provjera prijavila `MANDATORY_PLACE_MISSING`, a čvor popravka bi mjesto **vratio natrag** — izgledalo bi kao da agent ne sluša.
→ `goto execute_plan_node`

### 4. `execute_plan_node` — generiranje (najskuplji korak)
Sastavlja veliku uputu od blokova:
- **Način rada:** novi plan od nule / izmjena kao *delta* na postojeći plan
- **Tvrda ograničenja:** granice datuma, `departure_cutoff`, `arrival_cutoff`, sva obvezna mjesta
- **Redoslijed:** "kreni od stanice najbliže smještaju i idi u JEDNOM smjeru, nikad se ne vraćaj"
- **Prioritet mjesta:** MUST / SHOULD / NICE-TO-HAVE (iz komentara sudionika + znanja o gradu); ispada se odozdo
- **Obroci:** ručak 12–14, večera 17:30–21, kao **zasebne aktivnosti** s pravim imenom restorana
- **Bez praznog hoda:** rupa između aktivnosti < 90 min
- **`transit_details`:** linija, ulazna i izlazna stanica, smjer
- **SAMOPROVJERA (ključno):** model sam mora izračunati `kraj = početak + trajanje + put` za svaki par i pogurati preklapanja unaprijed, prije nego što išta vrati

**Dva kandidata paralelno** (`ThreadPoolExecutor`), različite strategije:
- `c1` — **zbijena geografija** (manje putovanja)
- `c2` — **raznoliki dani** (miks kultura/hrana/odmor)
- Kod izmjene: **samo 1 kandidat**

Izlaz se parsira u Pydantic `GeneratedPlan` (model prvo **ispiše popis ograničenja** — to mu služi kao *scratchpad* — pa tek onda slaže dane).
`_backfill_coords`: koordinate spremljenih mjesta se upisuju **iz baze**, model ih ne mora pisati → manje tokena i nema izmišljenih koordinata.
→ `goto validate_candidates`

### 5. `validate_candidates` — deterministička provjera (bez LLM-a, < 1 ms)
Tvrdi prekršaji:
- `TIME_OVERLAP` — razmak od kraja prethodne do početka sljedeće < 5 min
- `DEPARTURE_CONFLICT` — aktivnost završava nakon roka polaska
- `ARRIVAL_CONFLICT` — aktivnost počinje prije roka dolaska
- `TRAVEL_INFEASIBLE` — pješačenje > 3 km (haversine)
- `MANDATORY_PLACE_MISSING` — obvezno mjesto nije u planu
- `DATE_OUT_OF_RANGE` — dan izvan granica putovanja

Meka upozorenja: `HIGH_DAY_LOAD` (> 600 min), `LONG_TRANSIT_LEG` (> 45 km).

Grananje:
- barem jedan prošao → **`score_candidates`**
- svi pali i `repair_round < 2` → **`repair_failed_candidates`**
- svi pali i nema više rundi → **`compose_response`** (best-effort)

### 6. `repair_failed_candidates`
Jaki model dobije **popis prekršaja + trenutni plan (JSON) + kontekst** i uputu: *"popravi SAMO navedene greške, ostalo ne diraj"*. Batch preko svih palih kandidata → `repair_round += 1` → **natrag na provjeru** (petlja, max 2 runde).

### 7. `score_candidates` — 6 kriterija (samo za kandidate koji su prošli)
| Kriterij | Težina | Kako se računa |
|---|---|---|
| Efikasnost rute | 25% | minute putovanja po danu |
| Pokrivenost prioriteta | 25% | udio spremljenih mjesta + poštivanje željenog termina iz komentara |
| Ravnomjernost dana | 15% | standardna devijacija opterećenja dana (bez dana dolaska/odlaska) |
| Kvaliteta rasporeda | 15% | kazna za praznine > 60 min i za *detour ratio* (vraćanje unatrag) |
| Pravednost sudionika | 10% | min + prosjek udjela mjesta **svakog** sudionika |
| Troškovi | 10% | samo ako je budžet naveden (inače se težine renormaliziraju) |

Težinski prosjek → najveći `final_score` = `selected_candidate_id`.

### 8. `compose_response`
- **Prošao:** markdown pregled po danima (baza = smještaj, mjesta po danu, prijedlozi prijevoza/smještaja) + `structured_response` (plan, `constraint_report`, `score_report`, `accommodation_location`)
- **Nitko nije prošao:** uzme kandidata s **najmanje prekršaja**, doda "Treba vašu pozornost: [popis]" — dakle nikad prazan odgovor
- `goto END`

### Ostale grane (svaka 1 poziv → END)
- **`recommend_node`** — Tavily pretraga + kontekst putovanja
- **`general_node`** — samo LLM + kontekst
- **`accommodation_node`** — izvuče želje (budžet/kvart/tip); ako nema dosta → pita. Zatim **paralelno Booking.com i Airbnb** (RapidAPI): Booking razriješi `dest_id` (radije *landmark/district* ako je zadan kvart), sortira po udaljenosti, filtrira po cijeni/noć i radijusu 3 km; Airbnb razriješi `placeId` → pretraga → **provjera kalendara dostupnosti** paralelno po objektu. Ako su izražene meke želje, `llm_fast` **kurira** listu. Fallback: Tavily ograničen na booking/airbnb/hostelworld.
- **`transport_node`** — prvo razlikuje **lokalno** (kretanje po gradu → samo savjet LLM-a o kartama/metrou) od **međugradskog**. Za međugradsko traži polazište, vrstu prijevoza i tip karte, pa: **letovi → Skyscanner** (RapidAPI: razrješavanje kodova zračnih luka → pretraga, retry na 502/503, dedupe, najjeftinije), **autobusi i vlakovi → Tavily** (prednost FlixBus/Omio/Trainline) + deep-linkovi.

### Veza Rails ↔ agent
`ChatMessagesController#create` → spremi poruku korisnika + praznu "processing" poruku agenta, odmah vrati odgovor (Turbo) → **`AgentChatJob`** (Solid Queue, 1 posao po putovanju) → dohvati zadnjih 20 poruka + trenutni plan → **`Trips::AgentService`** → `POST /chat` (FastAPI, **SSE**: `status` događaji po čvoru + `final`) → Rails uzme `final`, spremi `content` + `plan_json`, upiše koordinate smještaja natrag u `trip` → **Turbo Streams** preko WebSocketa osvježi poruku **kod svih sudionika**.

---

## DIO 2: Što reći na svakom slajdu

### Slajd 1 — Naslovnica
"Dobar dan, ja sam Lorena Jakić. Tema mog diplomskog rada je *Aplikacija za planiranje putovanja primjenom LLM-agenta*, pod mentorstvom doc. dr. sc. Luke Humskog."

### Slajd 2 — Sadržaj
"Kratko ću proći kroz motivaciju i rješenje, stanje tehnike, arhitekturu sustava, prikazati rješenje uživo i završiti sa zaključkom."

### Slajd 3 — Motivacija
"Krenula sam od jednostavnog pitanja: kako danas planiramo putovanje s prijateljima? Linkovi lete po WhatsAppu, mjesta se spremaju u Google Maps, raspored se piše u dokument, a karte završe u mailu. Nitko nema cjelovitu sliku, a onaj tko na kraju sve slaže radi to ručno."

### Slajd 4 — Rješenje
"Zato sam napravila aplikaciju gdje se sve to radi na jednom mjestu. Sudionici se pozivaju na putovanje, zajedno dodaju mjesta na kartu i komentiraju ih — a ti komentari nisu dekoracija, iz njih agent kasnije čita želje. Sve je u stvarnom vremenu: kad jedan doda mjesto, ostali ga odmah vide."

### Slajd 5 — Agent (chat)
"Ovo je razgovor s agentom. Korisnik samo kaže *isplaniraj mi putovanje po danima*, a agent vrati plan po danima gdje svaki dan kreće i završava kod smještaja. Plan se jednim klikom sprema u putovanje."

### Slajd 6 — Raspored
"Spremljeni plan izgleda ovako: za svaki dan vremena, trajanja, ručak i večera kao zasebne stavke, i konkretna linija javnog prijevoza — koji metro, s koje stanice na koju. Desno je ruta na karti."

### Slajd 7 — Dokumenti
"I na kraju, dokumenti i karte na jednom mjestu — ulaznice, putovnice, karte za prijevoz, dostupne svim sudionicima."

### Slajd 8 — Stanje tehnike
"Postojeći alati poput Wanderloga i TripIta dobro organiziraju plan, ali raspored korisnik i dalje slaže sam. MindTrip koristi LLM, ali za jednog korisnika i bez provjere rezultata. Iz istraživanja, TravelPlanner pokazuje da sam LLM zakaže na realnim ograničenjima; TTG i Reflexion pokazuju smjer — dodati determinističku provjeru i dati modelu priliku da se sam ispravi. Upravo je to pristup koji sam primijenila."

### Slajd 9 — Arhitektura
"Sustav ima dvije komponente. Web-aplikacija u Ruby on Railsu jedina je ulazna točka — sučelje, autentifikacija i podaci u PostgreSQL-u. Sve što traži obradu prirodnog jezika prosljeđuje se agentu u LangGraphu, preko HTTP-a. Samo agent priča s vanjskim servisima — jezičnim modelima i API-jima za smještaj i prijevoz."

### Slajd 10 — Agentski sustav (glavni graf)
"Agent je graf. Svaka poruka prvo ide u čvor **usmjeravanja**, koji brzim i jeftinim modelom klasificira namjeru u jednu od šest kategorija, pa se izvođenje grana.

**Novi plan** gradi raspored od nule, koristi jači model i traži dva kandidata. **Izmjena plana** mijenja postojeći plan po zahtjevu, čuva ostatak nepromijenjenim i generira samo jednog kandidata — oba na kraju idu u isti podgraf.

**Preporuke** rade pretragu preko Tavilyja sa slabijim modelom. **Smještaj** dohvaća Booking i Airbnb preko RapidAPI-ja, a slabiji model sređuje rezultate — tu je i poznato ograničenje, dostupnost nije uvijek pouzdana. **Prijevoz** koristi Skyscanner za letove, a Tavily za autobuse i vlakove."

### Slajd 11 — Put jedne poruke
"Konkretno: korisnik napiše *isplaniraj mi putovanje po danima*. Usmjeravanje to prepozna kao zahtjev za novim planom, poruka ide u čvor za novi plan i dalje u podgraf za izradu plana — koji je na sljedećem slajdu."

### Slajd 12 — Podgraf izrade plana
"Plan se ne prihvaća odmah, jer jezični model **ne može jamčiti** da su ograničenja zadovoljena.

U **generiranju** paralelno nastaju dva kandidata s različitim strategijama — jedan gura zbijenu geografiju dana, drugi raznolikost aktivnosti.

**Provjera** je potpuno deterministička, bez modela, i traje ispod milisekunde: preklapanja aktivnosti, poštivanje vremena dolaska i polaska, prisutnost svih obveznih mjesta i je li pješačenje uopće izvedivo.

Ako **nijedan** kandidat ne prođe, ide **popravak** — model dobije popis prekršaja i ispravlja samo njih, pa se vraća na provjeru; najviše dvije runde. Ako barem jedan prođe, popravak se preskače i ide se na **bodovanje**. Ako ni nakon popravaka nitko ne prođe, korisnik dobije kandidata s najmanje prekršaja i jasno označene probleme — dakle nikad prazan odgovor."

### Slajd 13 — Bodovanje
"Kad ostane više izvedivih planova, treba odabrati bolji. Bodujem po šest kriterija: efikasnost rute i pokrivenost prioriteta nose po 25 %, ravnomjernost dana i kvaliteta rasporeda po 15 %, pravednost sudionika i troškovi po 10 %.

Dva su mi najzanimljivija: **kvaliteta rasporeda** kažnjava duge praznine i rute koje se vraćaju unatrag, a **pravednost sudionika** gleda da nijedan sudionik ne bude zakinut na račun drugoga. Troškovi se broje samo ako je korisnik naveo budžet.

Podjela uloga je jasna: **tvrde provjere odlučuju je li plan uopće izvediv, a bodovanje bira koji je od izvedivih ljepši.**"

### Slajd 14 — Upute za agenta
"Uputa je bila jednako važna kao i sama arhitektura. Četiri stvari su najviše pomogle:

Model prvo mora **popisati sva ograničenja** pa tek onda slagati plan — to mu služi kao bilježnica. Ograničenja su podijeljena na **tvrda** (mora) i **meka** (poželjno). Traži se **redoslijed obilaska bez vraćanja**. I najvažnije, **samoprovjera**: model za svaki par aktivnosti sam izračuna kraj, uključujući put, i pogura preklapanja prije nego išta vrati.

Samoprovjera je isplativa iako produljuje generiranje — jer izbjegne rundu popravka, koja je skuplja. U mjerenju je prolaz sa samoprovjerom bio oko 34 sekunde brži."

### Slajd 15 — Redoslijed obilaska
"Ovo je problem koji se **nije dao riješiti samom uputom**. Lijevo: agent je slao korisnika s Opére na Galeries Lafayette pa natrag na jug — cik-cak. Uputa je tražila *izbjegavaj vraćanje*, ali model nije imao **u odnosu na što** posložiti dan.

Rješenje je bila kombinacija dviju stvari: dodala sam **smještaj na kartu**, pa je model dobio konkretnu polaznu točku, i proširila uputu da dan kreće od stanice najbliže smještaju i ide u jednom smjeru. Desno je isti scenarij bez vraćanja.

Pouka: **uputa i kontekst rade zajedno** — uputa postaje provediva tek kad model uz nju dobije i konkretan podatak."

### Slajd 16 — Demonstracija
"Sad ću vam pokazati sustav uživo." *(Pokaži: dodavanje mjesta + komentar → agent → plan po danima → spremi → tab Raspored s kartom → izmjena, npr. "ne želim posjetiti X".)*

### Slajd 17 — Zaključak
"**Napravljeno:** cijeli sustav — Rails aplikacija za zajedničko planiranje u stvarnom vremenu i agentski sustav koji radi raspored, traži smještaj i prijevoz.

Pokazalo se da se kvaliteta plana **ne postiže jednim mehanizmom**, nego suradnjom jezičnog modela i determinističkih provjera. Agentski pristup s više kandidata, provjerom i popravkom nadmašuje jedan poziv LLM-u.

**Ograničenja:** dostupnost smještaja i prijevoza nije uvijek pouzdana jer RapidAPI zna vratiti i zauzete objekte. Sustav je slabiji na putovanjima s previše mjesta — tada plan prođe provjeru, ali je pretrpan.

**Dalje:** podrška za više smještaja unutar jednog putovanja, povezivanje s pouzdanim izvorom stvarne dostupnosti i veći testni skup."

### Slajd 18 — Hvala
"Hvala na pažnji, otvorena sam za pitanja."

---

## Moguća pitanja komisije
- **Zašto dva kandidata, a ne jedan?** Ako jedan padne, drugi često prođe → preskoči se skupi popravak (primjer Barcelone iz rada).
- **Zašto najviše 2 runde popravka?** Svaka runda je poziv jakom modelu (~30–60 s); nakon dvije runde je jeftinije vratiti best-effort s označenim problemima nego dalje trošiti vrijeme.
- **Zašto deterministička provjera, a ne LLM kao sudac?** Jer LLM ne daje jamstvo. Provjera traje < 1 ms i uvijek jednako presuđuje.
- **Kako se obvezno mjesto može ukloniti?** Poseban korak prepoznavanja isključenja u čvoru izmjene makne ga s popisa obveznih, inače bi ga popravak stalno vraćao.
- **Zašto dva različita modela?** Klasifikacija namjere je trivijalna → brzi/jeftini model. Slaganje plana traži zaključivanje → jaki model.
