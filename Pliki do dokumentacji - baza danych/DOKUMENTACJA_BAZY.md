# Baza danych symulatora ruchu kolejowego — dokumentacja metodyczna

Dokument opisuje sposób powstania bazy danych sieci kolejowej województwa śląskiego wykorzystywanej przez symulator. Zawiera wykaz źródeł, wyprowadzenia matematyczne zastosowanych przekształceń, wyniki kontroli jakości oraz jawnie wskazane ograniczenia.

Wersja bazy: 1.2 · Data budowy: 24 lipca 2026 · Stan sieci: rozkład jazdy 2025/2026 · Parametry infrastruktury: Regulamin sieci PKP PLK 2025/2026 (stan 30.08.2026)

---

## 1. Zakres i założenia

Baza obejmuje sieć kolejową **województwa śląskiego** wraz z punktami granicznymi umożliwiającymi prowadzenie ruchu tranzytowego. Odwzorowuje stan aktualny, zgodny z rozkładem jazdy obowiązującym od 14 grudnia 2025 r.

| Wielkość | Wartość |
|---|---|
| Węzły (stacje, posterunki, punkty graniczne) | 57 |
| Odcinki (szlaki) | 71 |
| Łączna długość sieci | 931,4 km |
| Relacje pociągów | 52 |
| Odcinki z prędkością ze źródła PLK | 66 z 71 (93%) |
| Odcinki z liczbą torów ze źródła PLK | 66 z 71 (93%) — pozostałe 5 z założeniem `assumed` |
| Stacje z liczbą peronów ze źródła PLK | 55 z 57 (96%) |
| Odcinek najdłuższy | Zawiercie – Częstochowa, 44,78 km |
| Odcinek najkrótszy | 1,03 km |

Podział węzłów: 29 węzłów rozgałęźnych, 20 przelotowych, 6 granicznych, 2 końcowe.

Wszystkie parametry infrastrukturalne pochodzą ze źródeł (rozkład jazdy lub Regulamin sieci PLK); jedyne wartości szacowane to liczba peronów dla 2 stacji granicznych leżących poza siecią PLK (Bohumín, Skalité).

Baza zawiera wyłącznie **dane statyczne**: węzły, odcinki i szablony pociągów. Zdarzenia ruchowe (awarie, ograniczenia prędkości) są generowane przez silnik symulacji w czasie działania i nie są częścią zasilenia początkowego.

---

## 2. Źródła danych

### 2.1. Źródło podstawowe

**Feed GTFS Kolei Śląskich**, wersja `2026.166`, okres obowiązywania do 13 grudnia 2026 r.

- publikacja: repozytorium `gtfs-proxies/24-Koleje-Slaskie` (kopia lustrzana danych przewoźnika)
- wydawca danych źródłowych: Koleje Śląskie sp. z o.o.
- zawartość wykorzystana: `stops.txt` (239 punktów ze współrzędnymi), `routes.txt` (202 relacje), `trips.txt` (13 639 kursów), `stop_times.txt` (213 567 rekordów rozkładu), `shapes.txt` (geometria przebiegu tras), `calendar.txt` i `calendar_dates.txt` (kalendarz kursowania)

Format GTFS (*General Transit Feed Specification*) jest otwartym standardem opisu rozkładów jazdy transportu zbiorowego. Istotne dla niniejszej pracy jest to, że feed zawiera nie tylko rozkład, ale również **rzeczywistą geometrię przebiegu tras** wraz z narastającą odległością wzdłuż toru — co pozwoliło wyznaczyć długości odcinków metodą pomiarową, a nie szacunkową.

### 2.2. Źródła autorytatywne parametrów infrastruktury

Wartościami autorytatywnymi dla parametrów infrastrukturalnych są załączniki **Regulaminu sieci PKP Polskie Linie Kolejowe S.A. 2025/2026** (stan na dzień 30.08.2026):

| Załącznik | Parametr | Zastosowanie w bazie |
|---|---|---|
| 1 Wykaz linii kolejowych | numery i przebiegi linii | weryfikacja przypisania odcinków do linii |
| 2.1 Wykaz maksymalnych prędkości | `vmax` (EZT / wagonowe / towarowe), tory N/P | `vmax_*`, `rail_tracks` |
| 2.4 Klasy odcinków linii | klasa odcinka (D3, D4, C3…) | `plk_klasa` |
| 2.6 Wykaz posterunków ruchu | typ punktu, kilometraż osi, peron | `type`, walidacja długości |
| 2.18 Wykaz peronów | liczba peronów, torów przyperonowych, długość | `platforms`, `tracks` |

Każdy z wykazów obejmuje całą sieć PLK; wykorzystano z nich rekordy dotyczące linii przechodzących przez węzeł śląski. Sposób powiązania wykazów z bazą opisano w rozdziale 3.9.

### 2.3. Źródła referencyjne i pomocnicze

- oficjalny kilometraż linii nr 1, użyty do wstępnej kontroli metody pomiaru długości
- podział administracyjny RP — klasyfikacja punktów względem granic województwa

### 2.4. Źródła niedostępne

Rozkłady **PKP Intercity** oraz **przewoźników towarowych** nie były dostępne maszynowo; rozkłady towarowe nie są zresztą jawne, ponieważ stanowią informację handlową przewoźników. Warstwy te są oznaczone jako modelowane (rozdz. 3.8).

### 2.5. Znaczniki wiarygodności

Każdy rekord zawiera pole `*_confidence` o jednej z wartości:

| Wartość | Znaczenie |
|---|---|
| `measured` | pochodzi wprost ze źródła |
| `derived` | wyliczone ze źródła zdefiniowaną procedurą |
| `modeled` | odtworzone na podstawie wiedzy dziedzinowej, bez źródła maszynowego |
| `missing` | brak pokrycia źródłowego, pole puste |

Rozkład pokrycia w gotowej bazie:

| Element | measured | derived | modeled | missing |
|---|---|---|---|---|
| Współrzędne stacji | 57 | – | – | – |
| Typ stacji (PLK 2.6) | 57 | – | – | – |
| Liczba peronów (PLK 2.18) | 55 | 2 | – | – |
| Długości odcinków | 71 | – | – | – |
| Prędkości `vmax` (PLK 2.1) | 66 | 5 | – | – |
| Liczba torów (PLK 2.1) | 66 | – | 5 (przyjęte 1, `assumed`) | – |
| Klasa odcinka (PLK 2.4) | 66 | – | – | 5 |
| Relacje pociągów | 42 | – | 10 | – |

---

## 3. Metodyka

Cały proces jest zautomatyzowany siedmioma skryptami w katalogu `src/`. Uruchomienie ich w kolejności odtwarza bazę od zera — żadna wartość nie została wpisana ręcznie.

### 3.1. Budowa grafu pełnego (`step1_graph.py`)

Z każdego kursu odczytano uporządkowaną sekwencję przystanków. Każda para kolejnych przystanków utworzyła krawędź nieskierowaną. Otrzymano graf o **239 wierzchołkach i 308 krawędziach**.

Stopień wierzchołka zdefiniowano jako liczbę różnych sąsiadów (nie liczbę kursów). Wierzchołki stopnia ≥ 3 są rozgałęzieniami sieci, stopnia 1 — punktami końcowymi, stopnia 2 — punktami pośrednimi na szlaku.

### 3.2. Usunięcie krawędzi-skrótów (`step2_clean.py`)

**Problem.** Feed GTFS opisuje kursy, nie infrastrukturę. Pociąg przyspieszony jadący z A do C bez zatrzymania w B tworzy w grafie krawędź (A, C) równoległą do ścieżki A–B–C. Krawędź taka nie odpowiada odrębnemu szlakowi — jest artefaktem rozkładu. Pozostawiona, tworzy fikcyjne objazdy, które algorytm wyznaczania trasy mógłby wykorzystać.

**Odrzucone kryterium odległościowe.** Pierwsza wersja usuwała (A, C), gdy `d(A,B) + d(B,C) ≤ 1,3·d(A,C)`. Kryterium okazało się nieodróżnialne od sytuacji, w której między A i C biegną **dwie różne linie** o zbliżonej długości — a w węźle śląskim to przypadek częsty (np. Bytom – Chorzów Batory: bezpośrednio linią 131 albo przez Chorzów Miasto). Kryterium kasowałoby zatem prawdziwe objazdy, czyli niszczyło dokładnie tę własność sieci, którą symulator ma badać. Wersję tę zachowano jako `step2_clean_v1_odleglosciowy.py`.

**Kryterium przyjęte — przynależność do przebiegu toru.** Jeśli pociąg jadący z A do C fizycznie mija posterunek B, to B leży na geometrii jego przejazdu zapisanej w `shapes.txt`. Jeśli jedzie inną linią — geometria omija B szerokim łukiem.

Krawędź (A, C) usuwamy wtedy i tylko wtedy, gdy istnieje wierzchołek B, którego odległość od łamanej opisującej przejazd A→C nie przekracza **TOL = 250 m**.

Odległość punktu **S** od odcinka **PQ** liczona jest wzorem:

```
t = clamp( ((S−P) · (Q−P)) / |Q−P|² , 0, 1 )
d = | S − (P + t·(Q−P)) |
```

Współrzędne rzutowane odwzorowaniem równopromiennym względem środka obszaru (φ₀ = 50°N, λ₀ = 19°E):

```
x = R · (λ − λ₀) · cos φ₀
y = R · (φ − φ₀)
```

gdzie R = 6 371 008,8 m. Błąd odwzorowania dla obszaru rzędu 200 km jest rzędu pojedynczych metrów, czyli pomijalny wobec progu 250 m.

**Dobór progu.** Perony stacji leżą w promieniu 100–200 m od osi toru, a linie równoległe w węźle śląskim są oddalone o co najmniej 400 m. Analiza wrażliwości:

| TOL [m] | Krawędzi uznanych za skrót |
|---|---|
| 100 | 54 |
| 150 | 54 |
| **250** | **56** |
| 400 | 57 |
| 600 | 59 |

Wynik jest stabilny w otoczeniu wartości przyjętej.

**Strażnik spójności.** Usuwanie prowadzone jest iteracyjnie, a przed każdym usunięciem sprawdzana jest spójność: krawędź-skrót wolno usunąć tylko wtedy, gdy trasa, którą skraca, nadal istnieje w grafie. Bez tego zabezpieczenia przystanki Ustroń Brzegi i Wisła Głębce zostały odcięte od sieci. Zachowano z tego powodu 1 krawędź mimo cech skrótu.

**Wynik:** 253 krawędzie (usunięto 55). Przykłady usuniętych: Mysłowice – Wisła Uzdrowisko (pomija 34 punkty), Katowice – Skoczów (15 punktów), Katowice – Czechowice-Dziedzice (10 punktów).

### 3.3. Pomiar długości odcinków (`step3_lengths.py`)

Plik `shapes.txt` zawiera dla każdego kursu łamaną opisującą przebieg toru wraz z kolumną `shape_dist_traveled` — narastającą odległością w metrach liczoną wzdłuż tej łamanej.

Dla krawędzi (A, B) i konkretnego kursu:

1. rzutujemy A i B na łamaną,
2. długość odcinka = |`shape_dist_traveled`[P(B)] − `shape_dist_traveled`[P(A)]|.

Otrzymana wielkość jest mierzona **wzdłuż toru**, a więc odpowiada kilometrażowi kolejowemu, a nie odległości w linii prostej.

**Rzutowanie monotoniczne.** Rzutowanie każdego przystanku niezależnie (`argmin` po całej łamanej) jest błędne, gdy trasa przechodzi w pobliżu tej samej stacji dwukrotnie — `argmin` wybiera wówczas nieprawidłowe wystąpienie. Przystanki rzutujemy więc w kolejności ich następstwa w kursie, przy czym rzut przystanku *i+1* szukany jest wyłącznie w części łamanej położonej za rzutem przystanku *i*. Wersję pierwotną zachowano jako `step3_lengths_v1_argmin.py`.

**Filtr krętości.** Krętość toru definiujemy jako iloraz długości mierzonej wzdłuż toru i odległości ortodromicznej. Dla kolei wartość ta mieści się praktycznie zawsze w przedziale 1,0–1,6. Obserwowano jednak pomiary rzędu 15,1 (Chybie – Chybie Mnich: 13,60 km przy odległości 0,90 km), ponieważ część łamanych prowadzi tam trasę okrężną. Odrzucamy zatem obserwacje o krętości spoza przedziału **[0,95 ; 2,5]**, a dopiero z pozostałych liczymy medianę.

Odległość ortodromiczna liczona jest wzorem haversine:

```
a = sin²(Δφ/2) + cos φ₁ · cos φ₂ · sin²(Δλ/2)
d = 2R · arcsin(√a)
```

**Agregacja.** Ta sama krawędź występuje w wielu kursach. Wartością końcową jest **mediana** — miara odporna na wartości odstające. Zapisywany jest również rozstęp i liczba obserwacji.

**Wynik i jakość pomiaru:**

| Miara rozrzutu (max − min na krawędź) | Wartość |
|---|---|
| Mediana | 0,000 km |
| 90. percentyl | 0,084 km |
| Maksimum | 0,823 km |

Zmierzono 232 krawędzie; dla 21 krawędzi bez wiarygodnego pomiaru zastosowano wartość zastępczą: odległość ortodromiczna przemnożona przez medianę krętości sieci (1,0425). Krawędzie te mają `len_confidence = derived`.

Uwaga: liczby te dotyczą **grafu pełnego przed kontrakcją** (253 krawędzie elementarne). Po kontrakcji (rozdz. 3.5) żaden z 71 odcinków bazy nie składa się wyłącznie z krawędzi zastępczych, dlatego w gotowej bazie wszystkie mają `dist_confidence = measured`.

**Kontrola krzyżowa z kilometrażem PKP PLK.** Dla odcinka Zawiercie – Sosnowiec Główny na linii nr 1:

- kilometraż oficjalny: 310,684 − 274,22 = **36,464 km**
- pomiar z geometrii GTFS: **36,23 km**
- różnica: **0,23 km (0,6 %)**

### 3.4. Selekcja węzłów (`step4_select.py`)

Graf pełny zawiera ponad 200 przystanków osobowych leżących w ciągu szlaku. Przystanek taki nie zmienia topologii — pociąg i tak musi przejechać cały szlak — więc utrzymywanie go jako osobnego wierzchołka zwiększa rozmiar grafu bez zwiększenia zdolności modelowania.

Wierzchołek wchodzi do bazy, gdy spełnia co najmniej jedną regułę:

| Reguła | Kryterium | Liczba węzłów |
|---|---|---|
| R1 | stopień ≥ 3 (posterunek odgałęźny) | 29 |
| R2 | stopień = 1 (stacja końcowa) | 2 |
| R3 | kończy bieg ≥ 5 kursów (stacja zwrotna) | 35 |
| R4 | punkt graniczny województwa | 6 |
| R5 | miasto na prawach powiatu | 16 |

Reguły nie są rozłączne — węzeł może spełniać kilka; pole `selection_rules` zawiera wszystkie spełnione.

**Droga dojścia do reguły R3 — dwie wersje odrzucone.**

*Wersja 1 — liczba zatrzymań w rozkładzie.* Odrzucona: na gęsto obsłużonej linii podmiejskiej **każdy** przystanek ma wysoką liczbę zatrzymań, więc reguła wciągała do bazy wszystkie przystanki w Tychach (po 2278 zatrzymań), mimo że żaden nie jest stacją. Miara opisuje częstotliwość kursowania linii, a nie rangę punktu.

*Wersja 2 — liczba różnych linii S obsługujących punkt.* Odrzucona z tego samego powodu w innej postaci: odnoga do Wisły obsłużona jest czterema relacjami (S6, S62, S76, S77), więc każdy z dziewięciu przystanków tej odnogi miał 4 linie i wchodził do bazy, podczas gdy Zabrze — miasto 155 tys. mieszkańców — miało linię jedną.

*Wersja przyjęta — liczba kursów kończących bieg.* Uzasadnienie ruchowe: pociąg może zakończyć bieg i zmienić kierunek jazdy wyłącznie tam, gdzie układ torowy na to pozwala, a więc na stacji, nie na przystanku osobowym. Miara jest niezależna od częstotliwości i wprost odpowiada zdolności technicznej punktu.

Analiza wrażliwości progu T potwierdza odporność kryterium:

| T (min. kursów kończących) | 5 | 20 | 50 | 100 |
|---|---|---|---|---|
| Liczba wybranych węzłów | **57** | 54 | 54 | 51 |

### 3.5. Kontrakcja grafu (`step4_select.py`)

Każda maksymalna ścieżka `v₀ – u₁ – … – u_k – v₁`, w której v₀, v₁ należą do zbioru wybranego, a wszystkie u_i nie należą i mają stopień 2, zastępowana jest pojedynczą krawędzią (v₀, v₁) o długości równej sumie długości krawędzi składowych. Punkty pośrednie zachowywane są w polu `via`.

Operacja zachowuje długości: suma długości krawędzi grafu zredukowanego (931,4 km) plus gałęzie odcięte poza województwem (189,2 km) równa się długości grafu pełnego (1120,7 km).

### 3.6. Wyznaczenie prędkości maksymalnej (`step5_vmax.py`)

**Dlaczego nie wystarczy prędkość średnia.** Naiwne `v = L/t` daje prędkość handlową, nie maksymalną. Pociąg między dwiema stacjami rusza z postoju, rozpędza się, jedzie ze stałą prędkością i hamuje. Różnica rośnie dla odcinków krótkich.

**Model trapezowy.** Przyjmujemy ruch jednostajnie przyspieszony, jednostajny i jednostajnie opóźniony:

```
t = L/v + v/(2a) + v/(2b)
```

gdzie *t* — czas przejazdu [s], *L* — długość odcinka [m], *v* — prędkość maksymalna [m/s], *a* — przyspieszenie rozruchu, *b* — opóźnienie hamowania.

Składniki `v/(2a)` i `v/(2b)` to straty czasu na rozruch i hamowanie. Dla ruchu jednostajnie zmiennego droga rozpędzania wynosi `v²/(2a)`, a czas jej przebycia `v/a`; ta sama droga przy stałej prędkości zajęłaby `v/(2a)` — różnica wynosi więc dokładnie `v/(2a)`.

Mnożąc obustronnie przez *v* i porządkując otrzymujemy równanie kwadratowe:

```
k = 1/(2a) + 1/(2b)
k·v² − t·v + L = 0
```

o rozwiązaniu:

```
v = ( t − √(t² − 4kL) ) / (2k)
```

Wybieramy pierwiastek z minusem — odpowiada rozwiązaniu fizycznemu; drugi dawałby prędkość, przy której pociąg nie zdążyłby wyhamować. Gdy wyróżnik `t² − 4kL < 0`, odcinek jest zbyt krótki, by osiągnąć prędkość ustaloną (profil trójkątny); wówczas `v = t/(2k)`.

**Parametry:** a = 0,6 m/s², b = 0,9 m/s² — wartości przyjęte dla elektrycznych zespołów trakcyjnych ruchu regionalnego, zgodne z parametrami silnika symulacji.

**Czas t** — 10. percentyl czasów przejazdu z rozkładu, nie mediana. Mediana zawiera rezerwy rozkładowe zaniżające wyliczoną prędkość; 10. percentyl przybliża czas techniczny.

**Pomiar na krawędziach elementarnych.** Pierwsza wersja stosowała model do odcinków już skontrahowanych, co było błędne: czas przejazdu takiego odcinka zawiera postoje na przystankach pośrednich oraz wielokrotne rozruchy i hamowania, których model z jednym rozruchem nie uwzględnia. Dla odcinka Zawiercie – Częstochowa (linia nr 1, prędkość szlakowa 140–160 km/h) dawało to **70 km/h**. Wersję zachowano jako `step5_vmax_v1_po_kontrakcji.py`.

**Wykorzystanie przejazdów bezpostojowych.** Pociąg zatrzymujący się co 3–4 km nie zdąży rozpędzić się do prędkości szlakowej, więc estymata z takich przejazdów jest zaniżona. Lepszym świadectwem są kursy przyspieszone pokonujące kilka szlaków bez zatrzymania — czyli właśnie te przejazdy, które w kroku 3.2 usunięto z grafu jako krawędzie-skróty. Odrzucono je jako krawędzie infrastruktury, ale ich **czasy** pozostają cenną informacją: przejazd bez postojów pośrednich ma jeden rozruch i jedno hamowanie na całej długości, więc model stosuje się do niego wprost.

Dla każdej krawędzi zbierane są estymaty z dwóch źródeł — (E1) przejazdy między sąsiednimi zatrzymaniami, (E2) przejazdy bezpostojowe — i przyjmowane jest **maksimum**. Wykorzystano 54 przejazdy bezpostojowe; estymata E2 okazała się wiążąca dla 84 z 253 krawędzi.

Po poprawce odcinek Zawiercie – Częstochowa otrzymuje **140 km/h**, co odpowiada rzeczywistej prędkości szlakowej linii nr 1.

**Agregacja i zaokrąglenie.** Prędkość odcinka po kontrakcji to średnia ważona długością krawędzi składowych, zaokrąglona **w dół** do klasy ze zbioru {30, 40, 50, 60, 70, 80, 100, 120, 140, 160} km/h. Zaokrąglenie w dół, ponieważ estymata z rozkładu jest wartością górną faktycznie realizowaną.

Rozkład klas **przyznanych przez sam model** (stan przed podmianą na dane PLK, zachowany w polu `vmax_model`): 30 km/h — 2 odcinki, 40 — 2, 50 — 6, 60 — 10, 70 — 4, 80 — 22, 100 — 19, 120 — 4, 140 — 2. Rozkład wartości finalnych, obowiązujących w bazie, podano w rozdz. 3.9.2.

**Ograniczenie i dalszy krok.** Wartości z modelu są estymatą **prędkości realizowanej**, nie konstrukcyjnej prędkości dopuszczalnej linii. W kroku 3.9 zostały one zastąpione danymi z załącznika 2.1 Regulaminu sieci PLK dla 66 z 71 odcinków; model zachowano w polu `vmax_model` do porównania (rozdz. 3.9.5). Prędkości modelowe pozostają jedynie na 5 odcinkach, których nie udało się dopasować do wykazów PLK.

### 3.7. Obciążenie stacji (`step7_emit.py`)

Pole `daily_trains` nie jest szacowane. Wybierany jest reprezentatywny dzień roboczy (wtorek w środku okresu obowiązywania rozkładu — 16 czerwca 2026), ustalany zbiór kursów aktywnych tego dnia na podstawie `calendar.txt` i `calendar_dates.txt` (211 aktywnych służb), a następnie zliczane zatrzymania w każdym punkcie.

Wartość dotyczy **wyłącznie ruchu Kolei Śląskich**. Pociągi PKP Intercity, POLREGIO i towarowe nie występują w źródle, więc rzeczywiste obciążenie stacji jest wyższe. Fakt ten odnotowuje pole `daily_trains_scope`.

### 3.8. Warstwa pociągów (`step6_services.py`)

Trzy warstwy o różnej wiarygodności:

**(A) Regionalne — 42 relacje, `measured`.** Źródło: feed GTFS. Oznaczenia linii, relacje, kolejność postojów i godziny odjazdów pochodzą wprost z obowiązującego rozkładu. Reprezentowane linie: S1, S3, S4, S5, S6, S7, S8, S9, S13, S17, S18, S31, S34, S61, S62, S71, S72, S74, S78, S82, KSL oraz relacja ZSSK do Skalitégo.

Dla każdej relacji wybierany jest **wariant dominujący** — sekwencja postojów powtarzająca się w największej liczbie kursów. Trasa rzutowana jest na węzły bazy z zachowaniem kolejności; relacje mające po rzutowaniu mniej niż 2 węzły są pomijane. Sprawdzana jest przejezdność trasy w grafie bazy.

**Trasy warstw modelowanych (B i C)** podawane są jako lista stacji charakterystycznych, które nie muszą być bezpośrednimi sąsiadami w grafie — między nimi leżą posterunki wybrane w kroku 3.4. Wpisanie takiej listy wprost dawałoby trasę z „przeskokami” bez odpowiadającej krawędzi `TRACK`. Każda para kolejnych stacji jest więc rozwijana najkrótszą ścieżką w grafie (przeszukiwanie wszerz po liczbie odcinków), dzięki czemu **wszystkie 52 relacje są w całości przejezdne** — każdy krok trasy ma odpowiadającą krawędź.

**(B) Dalekobieżne — 6 relacji, `modeled`.** Rozkłady PKP Intercity nie były dostępne maszynowo. Relacje odtworzono na podstawie faktycznie kursujących połączeń przez węzeł śląski (IC Ślązak, IC Ondraszek, EC Silesia, EC Sobieski, TLK Jasna Góra, IC Odra); godziny są przybliżone. Do zastąpienia danymi z Portalu Pasażera przy aktualizacji bazy.

**(C) Towarowe — 4 relacje, `modeled`.** Rozkłady pociągów towarowych **nie są jawne** — stanowią informację handlową przewoźników. Odtworzono realne korytarze przewozowe regionu: relacja kopalnie ROW – Gliwice, tranzyt do granicy państwa przez Chałupki, obsługa zakładów hutniczych Zagłębia, magistrala węglowa w kierunku Tczewa. Numery i godziny są modelowe.

**Parametry taborowe** są wartościami typowymi dla klas pojazdów eksploatowanych w regionie, nie pochodzą z dokumentacji taborowej przewoźników:

| Typ | vmax | Masa | Długość | a | b | Priorytet |
|---|---|---|---|---|---|---|
| REGIONAL | 120 | 120 t | 60 m | 0,6 | 0,9 | 2 |
| IC | 160 | 420 t | 200 m | 0,5 | 0,8 | 3 |
| FREIGHT | 80 | 1800 t | 550 m | 0,25 | 0,4 | 1 |

---

## 3.9. Integracja oficjalnych danych PKP PLK

Po zbudowaniu bazy z rozkładu jazdy uzupełniono ją o parametry infrastrukturalne z czterech wykazów Regulaminu sieci PLK. Etap ten realizują skrypty `step8a`–`step8e`.

### 3.9.1. Problem dopasowania

Wykazy PLK indeksowane są parą **(numer linii, kilometraż)**, a nie nazwą odcinka. Każdy węzeł występuje w wykazie posterunków na jednej lub wielu liniach — stacja węzłowa Chorzów Batory leży na siedmiu liniach. Aby odczytać prędkość odcinka (A, B), trzeba najpierw ustalić wspólną linię, po której biegnie ten odcinek, oraz zakres kilometrażu na tej linii.

**Dopasowanie nazw.** Węzły identyfikowane są przez nazwę. Nazwy w GTFS i w wykazach PLK różnią się zapisem (skrót „Gł." wobec pełnego „Główna", znaki diakrytyczne). Zastosowano normalizację: usunięcie znaków diakrytycznych, ujednolicenie „Gł."/„Główna", zamiana myślników i kropek na spacje. Po normalizacji **wszystkie 57 węzłów** dopasowano do wykazu posterunków 2.6.

**Przypisanie linii do odcinka.** Dla odcinka o końcach A, B:

1. wyznaczamy zbiory linii L(A) i L(B), na których leżą oba końce,
2. część wspólna L(A) ∩ L(B) daje linie kandydujące,
3. dla każdej kandydatki mamy kilometraż obu końców; wybieramy tę, dla której różnica kilometrażu jest najbliższa zmierzonej długości odcinka — to niezależne potwierdzenie, że wybrano właściwy szlak.

**Odcinki wieloliniowe.** Część odcinków biegnie przez stację pośrednią nieujętą jako węzeł bazy (np. Gliwice–Bytom przez Zabrze). Ich końce leżą wtedy na różnych liniach. Dla takich przypadków algorytm dzieli trasę na elementarne kroki po punktach pośrednich (`via`) i szuka wspólnej linii dla każdego kroku osobno; gdy i to zawodzi, próbuje dopasowania dwuetapowego przez punkt styku występujący na obu liniach.

**Punkty występujące w wykazie wielokrotnie.** Ten sam punkt figuruje w zał. 2.6 zwykle w kilku rekordach — po jednym na każdą linię — a niekiedy dodatkowo pod różnymi wyróżnikami i z różnym kilometrażem osi. Przykładem jest Katowice Szopienice Południowe: występuje jako posterunek odgałęźny (linie 1, 138, 660) oraz jako przystanek osobowy (linie 1, 138), przy czym kilometraż obu rekordów różni się o ok. 276 m. Przyjęto trzy reguły rozstrzygające:

1. **typ punktu** — rekord o najwyższej randze ruchowej (ST > STTH > PODG > PODS > PGR > pozostałe), bo to ona określa możliwości prowadzenia ruchu, które modeluje symulator;
2. **peron** — uznawany za czynny, jeśli występuje w *dowolnym* rekordzie punktu (peron należy do punktu, nie do konkretnej linii);
3. **kilometraż** — zachowywany osobno dla każdej linii; przy kilku rekordach na tej samej linii brany jest rekord o najwyższej randze, spójnie z regułą 1.

Pole `plk_wyrozniki` przechowuje pełny zbiór wyróżników punktu, więc rozstrzygnięcie pozostaje odwracalne. Różnica kilometrażu rzędu setek metrów wpływa na walidację z rozdz. 3.9.4 i jest jedną z przyczyn odchyleń opisanych w tamtej sekcji.

**Linie zarządzane przez inny podmiot.** Odcinek Chałupki – Bohumín leży na linii 479, która występuje w zał. 2.1 i 2.4, ale **nie w zał. 1** — jest tam oznaczona jako infrastruktura zagraniczna (znacznik `ZAGR`). Kontrola przypisania odcinka do linii przez zał. 1 nie ma więc dla niego zastosowania; to samo zjawisko dotyczy przejścia Zwardoń – Skalité. W obu przypadkach kilometraż i zarządzanie po stronie zagranicznej prowadzone są w odrębnym systemie.

**Wynik:** 66 z 71 odcinków dopasowano do wykazów PLK. Pozostałe 5 to przypadki złożone (przejście graniczne Zwardoń–Skalité z osobnym systemem kilometrażu, obwodnice towarowe o styku na trzeciej linii); zachowują one prędkość modelową i są oznaczone `vmax_confidence = derived`.

### 3.9.2. Odczyt prędkości

Wykaz 2.1 podaje prędkości osobno dla trzech kategorii pociągów (autobusy szynowe i EZT, składy wagonowe, pociągi towarowe) oraz osobno dla toru nieparzystego (N) i parzystego (P). Na zakresie odcinka występuje zwykle wiele pod-odcinków o różnych prędkościach (linia 139 ma ich kilkadziesiąt). Prędkość odcinka dla danej kategorii liczymy jako **średnią ważoną długością** pod-odcinków przecinających zakres:

```
v = Σᵢ ( vᵢ · długość_przecięcia_i ) / Σᵢ długość_przecięcia_i
```

a następnie zaokrąglamy w dół do klasy PLK. Średnia ważona, nie maksimum — prędkość szlakowa odcinka to wartość reprezentatywna dla całej jego długości, a nie chwilowe maksimum na krótkim fragmencie. Baza przechowuje wszystkie trzy prędkości w osobnych polach `vmax_ezt`, `vmax_wagon`, `vmax_towar`; pole `vmax` przyjmuje wartość dla EZT jako reprezentatywną dla ruchu regionalnego.

Zaokrąglenie następuje w dół do najbliższej wartości ze zbioru klas stosowanych w wykazach PLK:
{20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 160, 200} km/h. Zbiór ten jest gęstszy niż użyty w modelu fizycznym (rozdz. 3.6), który pomijał wartości 90, 110 i 130 — dlatego w bazie finalnej występują klasy nieobecne w rozkładzie modelowym.

Rozkład prędkości `vmax` w gotowej bazie (71 odcinków):

| km/h | 30 | 40 | 50 | 60 | 70 | 80 | 90 | 100 | 110 | 120 | 130 | 140 | 160 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| odcinków | 1 | 1 | 1 | 3 | 7 | 7 | 8 | 17 | 9 | 9 | 5 | 2 | 1 |

### 3.9.3. Liczba torów

Wykaz 2.1 rozróżnia tor N i P. Liczba różnych oznaczeń torów występujących na zakresie odcinka jest liczbą torów szlakowych: odcinek z wpisami tylko dla toru N jest jednotorowy, z wpisami N i P — dwutorowy. Wynik: **49 odcinków dwutorowych i 17 jednotorowych**. Dla 5 odcinków bez dopasowania do wykazu przyjęto wartość 1 (tor pojedynczy) jako założenie konserwatywne — oznaczono ją polem `rail_tracks_confidence = assumed`, żeby odróżnić od 66 wartości źródłowych. Ta sama wartość i ten sam znacznik trafiają do obu seedów (`seed.py` i `seed.cypherl`).

### 3.9.4. Walidacja krzyżowa długości

Dysponując kilometrażem osi każdego punktu z wykazu 2.6, przeprowadzono **niezależną walidację** długości zmierzonych z geometrii GTFS (rozdz. 3.3). Dla odcinków elementarnych leżących na wspólnej linii różnica kilometrażu końców jest oficjalną długością odcinka wg zarządcy.

| Różnica \|GTFS − PLK\| (19 odcinków elementarnych) | Wartość |
|---|---|
| Mediana | **53 m** |
| Mediana (bez przejścia granicznego) | 48 m |
| Średnia | 252 m |
| Maksimum (bez przejścia granicznego) | 1464 m |
| Średni błąd względny | 5,7 % |

Zgodność jest bardzo dobra: dla połowy odcinków różnica nie przekracza 53 m.

**Kryterium doboru próby.** Do porównania kwalifikują się odcinki spełniające łącznie dwa warunki: (a) są elementarne, czyli po kontrakcji nie zawierają punktów pośrednich (puste pole `via` w `segments.csv`), oraz (b) mają przypisany dokładnie jeden numer linii PLK. Tylko wtedy różnica kilometrażu końców jest jednoznaczna. Warunek (a) spełniają 24 odcinki, oba łącznie — **19**. Listę można odtworzyć z `segments.csv` filtrem `via` puste i `plk_line` bez średnika.

 Dwa przypadki odstające mają wyjaśnienie fizyczne — Chałupki–Bohumin przekracza granicę państwa (dwa różne systemy kilometrażu, PKP i ČD), a Poręba–Zawiercie łapie kilometraż przez pośredni punkt styku na innej linii. Walidacja stanowi **niezależne potwierdzenie poprawności metody pomiaru długości** z geometrii GTFS, gdyż obie wartości pochodzą z całkowicie różnych źródeł (geometria toru vs ewidencja kilometrażowa zarządcy).

### 3.9.5. Porównanie modelu prędkości z danymi źródłowymi

Ponieważ prędkości wyznaczono najpierw modelowo (rozdz. 3.6), a następnie zastąpiono danymi PLK, można ocenić **trafność modelu fizycznego**. Na 66 odcinkach z danymi PLK:

| Miara | Wartość |
|---|---|
| Średni błąd modelu (model − PLK) | **−18,0 km/h** |
| Mediana błędu bezwzględnego | 20 km/h |
| Odsetek w zakresie ±20 km/h | 67 % (44/66) |

Model **systematycznie zaniża** prędkość o około 18 km/h. Jest to spójne z jego założeniem: model wyznacza prędkość **realizowaną** przez pociąg regionalny między dwoma zatrzymaniami, a wykaz PLK podaje prędkość **konstrukcyjnie dopuszczalną** linii. Pociąg regionalny, zwłaszcza na krótkich odcinkach, nie zdąża rozpędzić się do prędkości dopuszczalnej — stąd stała różnica. Największe rozbieżności (Chybie–Zabrzeg: 40 wobec 120 km/h) występują na odcinkach, gdzie linia ma wysoką prędkość konstrukcyjną, ale ruch regionalny jest wolny. Model zachowano w polu `vmax_model` obok danych PLK, co pozwala tę różnicę analizować.

### 3.9.6. Liczba peronów i torów przyperonowych

Wykaz 2.18 zawiera jeden rekord na **krawędź peronową** (para peron–tor) z długością i wysokością krawędzi. Dla każdej stacji wyznaczamy: liczbę peronów (liczba różnych numerów peronów), liczbę krawędzi peronowych (przybliżenie liczby torów przyperonowych) oraz maksymalną długość krawędzi (pojemność stacji — najdłuższy skład, jaki może się zatrzymać). Zastępuje to dotychczas szacowane pola `platforms` i `tracks`.

Dopasowano **55 z 57 stacji**; dwie niedopasowane to Bohumín i Skalité, leżące poza siecią PLK (po stronie czeskiej i słowackiej) — zachowują wartość szacowaną. Największe stacje: Częstochowa (5 peronów), Gliwice, Bielsko-Biała Główna i Oświęcim (po 4).

---

## 4. Struktura bazy

### 4.1. Węzeł `Station`

| Pole | Typ | Źródło |
|---|---|---|
| `id` | string | kod 3-znakowy generowany z nazwy |
| `name` | string | GTFS `stops.txt` |
| `lat`, `lon` | float | GTFS `stops.txt` |
| `type` | string | typ punktu wg PLK zał. 2.6 (stacja / przystanek osobowy / posterunek odgałęźny) |
| `type_plk` | string | kod PLK (ST, PO, PODG, MPO) |
| `type_topologiczny` | string | typ wyliczony z grafu (węzeł / przelotowa / końcowa) |
| `plk_lines` | string | linie, na których leży punkt |
| `daily_trains` | int | wyliczone z rozkładu (rozdz. 3.7) |
| `has_platform` | string | czynny peron wg PLK 2.6 (TAK/NIE) |
| `platforms` | int | liczba peronów wg PLK zał. 2.18 |
| `tracks` | int | liczba torów przyperonowych wg PLK zał. 2.18 |
| `platform_len_max_m` | int | długość najdłuższej krawędzi peronowej (pojemność) |
| `platform_manager` | string | zarządca peronu, gdy inny niż PLK (np. `UM Tychy`) |
| `plk_wyrozniki` | string | pełny zbiór wyróżników punktu w zał. 2.6 |
| `platforms_est`, `tracks_est` | int | **wartości pomocnicze** — oszacowania z natężenia ruchu, obliczane dla wszystkich stacji i zachowane w CSV do porównania. Do bazy trafiają wyłącznie tam, gdzie brak danych z zał. 2.18, czyli dla 2 stacji granicznych (Bohumín, Skalité) — wtedy `platforms`/`tracks` przyjmują ich wartość, a `platforms_confidence` ma wartość `derived`. Kolumny `platforms`/`tracks` w CSV są zawsze identyczne z zawartością seedów. |
| `voivodeship` | string | klasyfikacja administracyjna |
| `gtfs_stop_id` | string | klucz obcy do źródła |

Zachowano dwa typy — formalny PLK i topologiczny — bo się różnią. Punktów o typie innym niż „stacja” jest 12, a **8 z nich pełni w grafie rolę węzła rozgałęźnego lub stacji końcowej**, będąc formalnie przystankami osobowymi: Chybie Mnich, Goczałkowice-Zdrój, Katowice Piotrowice, Katowice Szopienice Południowe, Poręba, Rudyszwałd, Tychy Lodowisko, Zabrzeg. Różnica jest sama w sobie informacją: ruch kończy się tam, gdzie pozwala na to układ torowy, niezależnie od formalnej kategorii punktu.

### 4.2. Relacja `TRACK`

| Pole | Typ | Źródło |
|---|---|---|
| `segment_id` | string | nadany sekwencyjnie |
| `dist_km` | float | pomiar z geometrii toru (rozdz. 3.3), zwalidowany PLK (rozdz. 3.9.4) |
| `vmax` | int | PLK zał. 2.1, kategoria EZT (reprezentatywna) |
| `vmax_ezt`, `vmax_wagon`, `vmax_towar` | int | PLK zał. 2.1, trzy kategorie pociągów |
| `vmax_model` | int | prędkość z modelu fizycznego (do porównania) |
| `rail_tracks` | int | PLK zał. 2.1 (liczba torów N/P) |
| `rail_tracks_confidence` | string | `measured` (66 odcinków) / `assumed` (5 bez dopasowania) |
| `plk_line` | string | numer(y) linii PLK |
| `plk_klasa` | string | klasa odcinka wg PLK zał. 2.4 |
| `travel_min` | float | 10. percentyl z rozkładu |
| `status` | string | `active` |
| `lines_gtfs` | string | linie S obsługujące odcinek |

Relacje zapisywane są **dwukierunkowo**, zgodnie ze schematem używanym przez silnik symulacji.

### 4.3. Węzeł `Train`

Zawiera parametry fizyczne (`vmax`, `mass_tonnes`, `length_m`, `accel`, `decel`, `priority`), trasę jako listę identyfikatorów stacji oraz godziny odjazdów. **Nie zawiera stanu wykonania** (`progress`, `current_segment_id`, `updated_at`) — są to pola czasu działania, wypełniane przez silnik.

---

## 5. Kontrola jakości

| Test | Wynik |
|---|---|
| Spójność grafu | 1 składowa spójna — sieć jest w całości przejezdna |
| Unikalność kluczy stacji | tak (57/57) |
| Unikalność kluczy relacji | tak (52/52) |
| Zgodność sumy długości po kontrakcji | tak (931,4 + 189,2 = 1120,7 km) |
| Walidacja długości z kilometrażem PLK | mediana różnicy 53 m (rozdz. 3.9.4) |
| Dopasowanie węzłów do wykazu PLK 2.6 | 57/57 |
| Odcinki z prędkością i liczbą torów z PLK | 66/71 |
| Stacje z liczbą peronów z PLK 2.18 | 55/57 |
| Odcinki bez możliwości objazdu (mosty) | 15 z 71 = 21 % |

**Mosty w grafie** to odcinki, których zablokowanie odcina fragment sieci — algorytm wyznaczania trasy nie znajdzie dla nich objazdu. Ich udział spadł z 34 % (baza poprzednia, 13 z 38 odcinków) do 21 %, co jest bezpośrednim skutkiem rozszerzenia grafu o posterunki odgałęźne. Pozostałe mosty to odgałęzienia rzeczywiście jednodrogowe (m.in. Bielsko-Biała – Łodygowice, Chałupki – Rudyszwałd) i odzwierciedlają faktyczną strukturę sieci, nie wadę modelu. Pełna lista w `weryfikacja.txt`.

---

## 6. Ograniczenia

1. **Zasięg źródła rozkładowego.** Feed obejmuje ruch Kolei Śląskich. Linie obsługiwane wyłącznie przez innych przewoźników lub wyłącznie towarowo nie są reprezentowane jako odcinki.
2. **Pięć odcinków z prędkością modelową.** Dla 5 z 71 odcinków nie udało się jednoznacznie dopasować linii PLK (przejście graniczne, obwodnice towarowe o złożonym styku); zachowują prędkość z modelu fizycznego, oznaczoną `derived`.
3. **Dwie stacje graniczne bez danych peronowych.** Bohumín i Skalité leżą poza siecią PLK (znacznik `ZAGR`); ich liczba peronów jest szacowana, a `has_platform` ma wartość `NIE`, co odpowiada pustej kolumnie peronu w wykazie.
4. **Warstwy modelowane.** 10 z 52 relacji (dalekobieżne i towarowe) nie pochodzi ze źródła maszynowego.
5. **Stan sieci.** Baza odwzorowuje rozkład 2025/2026, obowiązujący w trakcie przebudowy węzła Katowice. Część relacji jest w nim skróconych lub przekierowanych wskutek prowadzonych robót.

---

## 7. Powtarzalność

```
python3 src/step1_graph.py       # graf pełny z GTFS
python3 src/step2_clean.py       # usunięcie krawędzi-skrótów
python3 src/step3_lengths.py     # pomiar długości i czasów
python3 src/step4_select.py      # selekcja węzłów i kontrakcja
python3 src/step5_vmax.py        # wyznaczenie prędkości (model fizyczny)
python3 src/step6_services.py    # warstwa pociągów
python3 src/step8a_load_plk.py   # wczytanie wykazów PLK
python3 src/step8b_enrich.py     # vmax, tory, klasy z PLK
python3 src/step8c_stations.py   # typy i perony stacji z PLK
python3 src/step8d_validate.py   # walidacja długości z kilometrażem PLK
python3 src/step8e_platforms.py  # liczba peronów z PLK zał. 2.18
python3 src/step7_emit.py        # generowanie plików wyjściowych (CSV + seed Cypher)
python3 src/step9_seedpy.py      # generowanie backend/db/seed.py dla aplikacji
```

Kroki 8 są opcjonalne — bez nich baza działa z wartościami modelowymi (`step5`). Uruchomienie ich wzbogaca bazę o dane źródłowe PLK i musi poprzedzać `step7`. Każdy skrypt zapisuje wynik pośredni w `work/`. Wszystkie parametry metod (progi TOL, krętości, T) są stałymi na początku plików.

Zasilenie bazy dwiema drogami: aplikacja ładuje dane przez `backend/db/seed.py` (generowany w kroku 9), a ręczny import do Memgrapha wykonuje się plikiem `out/seed.cypherl` (`mgconsole < out/seed.cypherl` albo sekcja Import w Memgraph Lab). Format `.cypherl` wymaga jednego polecenia na wiersz — dlatego jest generowany osobno od czytelnego `seed.cypher` z komentarzami.

---

## 8. Wykaz plików

| Plik | Zawartość |
|---|---|
| `out/stations.csv` | 57 węzłów z pełną proweniencją i typem PLK |
| `out/segments.csv` | 71 odcinków z długościami, prędkościami (3 kategorie), torami i klasą |
| `out/services.csv` | 52 relacje pociągów |
| `out/seed.cypherl` | skrypt zasilający Memgraph (format importu: 1 polecenie/wiersz) |
| `out/seed.cypher` | ta sama treść z komentarzami, do czytania i edycji |
| `out/seed.py` | plik do podmiany w `backend/db/seed.py` — źródło danych aplikacji |
| `out/weryfikacja.txt` | raport kontroli jakości i pokrycia źródłowego |
| `src/step1..7_*.py` | skrypty budujące bazę z GTFS |
| `src/step8a..e_*.py` | skrypty integrujące dane PLK i walidujące |
| `src/step9_seedpy.py` | generator `backend/db/seed.py` |
| `src/*_v1_*.py` | odrzucone warianty metod, zachowane do dokumentacji |
