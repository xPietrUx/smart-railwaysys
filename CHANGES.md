# CHANGES — Autonomiczny system pociągów

Dokumentacja zmian wprowadzonych w ramach przeprojektowania systemu na branchu
`feat/autonomic-trains`: z całkowicie statycznej wizualizacji sieci (10 stacji,
zero ruchu) na autonomiczną symulację pociągów kursujących samodzielnie po
sieci kolejowej województwa śląskiego, obsługujących losowe awarie bez
ingerencji człowieka.

Pełne uzasadnienie decyzji architektonicznych znajduje się w planie zapisanym
podczas projektowania tej funkcji; ten dokument opisuje to, co faktycznie
powstało i zostało zweryfikowane.

---

## Stan wyjściowy

Przed zmianami: `Train` istniały w Memgraph jako statyczne węzły utworzone
przez `seed.py`, ale nic ich nie aktualizowało — brak API dla pociągów, brak
silnika symulacji, frontend w ogóle ich nie rysował. Sieć obejmowała tylko
konurbację katowicką (10 stacji, 12 odcinków).

Po drodze znaleziono niezmergowaną gałąź `origin/feat/dodanie-algorytmu-A-`
z wcześniejszym prototypem tego samego pomysłu (A*, ręczne blokowanie
odcinków). Miała realne wady: symulacja napędzana przez klienta
(`setInterval` w przeglądarce — zamierała bez otwartej karty, przyspieszała
przy wielu kartach), pociągi tylko w pamięci procesu (znikały przy każdym
restarcie), zahardkodowany dystans odcinka (`dist_km = 20.0` zamiast
rzeczywistej wartości), brak losowości, blokada zawsze na oba kierunki naraz,
brak cyklu powrotnego po dotarciu do celu. Gałąź została **nietknięta** —
zaadaptowano z niej tylko koncepcję A* i heurystykę haversine, resztę
napisano od nowa pod nową architekturę.

---

## Architektura — kluczowe decyzje

1. **Memgraph jako jedyne źródło prawdy** dla stanu stacji/torów/pociągów
   (zamiast pamięci procesu jak w prototypie) — istotne również dlatego, że
   `docker compose watch` + `uvicorn --reload` restartują backend przy
   praktycznie każdym zapisie pliku podczas developmentu, więc stan
   trzymany tylko w pamięci ginąłby bardzo często, nie tylko sporadycznie.
2. **Pętla symulacji działa autonomicznie po stronie backendu**
   (`asyncio.create_task` w `lifespan`), niezależnie od tego, czy ktoś ma
   otwartą przeglądarkę. Naprawia to oba błędy z prototypu (zamrożenie bez
   klienta, przyspieszenie przy wielu klientach). Synchroniczny sterownik
   `neo4j` jest odpalany przez `asyncio.to_thread`, żeby nie blokować event
   loopa dla ruchu HTTP/WS.
3. **WebSocket (`/ws/live`) jako główny kanał na żywo**, z automatycznym
   fallbackiem frontendu na odpytywanie REST, jeśli WS nie działa (i cichą
   próbą powrotu na WS w tle). Zero nowych zależności — `uvicorn[standard]`
   już zawiera `websockets`.
4. **Blokada torów jest świadoma kierunku i liczby torów
   (`rail_tracks`)**: awaria na odcinku jednotorowym blokuje oba kierunki
   (fizycznie jeden wspólny tor), na dwutorowym — tylko jeden losowo
   wybrany kierunek, drugi działa dalej.
5. **Dokładnie jeden pisarz stanu torów**: cały efekt zdarzeń (blokada,
   ograniczenie prędkości) idzie przez `event_service.py`, także w trybie
   debug (`POST /api/simulation/events/trigger` używa tej samej funkcji co
   losowy scheduler — nie ma osobnej ręcznej ścieżki).
6. **Czas rzeczywisty vs. czas symulacji rozdzielone**: przerwy (`dwell`) i
   czas trwania zdarzeń liczone w realnych sekundach (obserwator widzi efekt
   szybko niezależnie od skali), tylko ruch pociągu skalowany przez
   `SIM_TIME_SCALE`.

---

## Model danych (Memgraph)

| element                                                         | zmiana                                                                                                                                                                                                                                                                                                   |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Station`                                                       | bez zmian strukturalnych, +20 nowych węzłów                                                                                                                                                                                                                                                              |
| `TRACK` (relacja, nadal 2 skierowane instancje na `segment_id`) | nowe właściwości `restricted_vmax`, `active_event_id`; `status` (`active`/`blocked`/`restricted`) ustawiany **per kierunek**, nie zawsze na oba naraz                                                                                                                                                    |
| `Train`                                                         | przeprojektowany: `origin_station_id`/`destination_station_id` (stała para wahadłowa), `direction` (`outbound`/`return`), `status` (`running`/`dwelling`/`waiting`/`derailed` — celowo bez stanu końcowego), `route_station_ids`/`route_segment_ids`/`route_index`, `dwell_until`, `delayed_by_event_id` |
| `RailEvent`                                                     | **nowy węzeł**: `type` (`line_failure`/`derailment`/`speed_restriction`/`signal_failure`), `severity`, `status`, kontekst zależny od typu, `message` (PL), `started_at`/`resolves_at`/`resolved_at`; relacja `-[:AFFECTS]->` do `Train` przy wykolejeniach                                               |

---

## Backend — nowe i zmienione pliki

| plik                                                             | status               | rola                                                                                        |
| ---------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------- |
| `app/core/haversine.py`                                          | nowy                 | heurystyka odległości dla A\*                                                               |
| `app/core/config.py`                                             | rozszerzony          | zmienne `SIM_*` sterujące symulacją                                                         |
| `app/core/ws_manager.py`                                         | nowy                 | rozgłaszanie stanu do klientów WebSocket                                                    |
| `app/core/lifespan.py`                                           | rozszerzony          | start/stop pętli symulacji                                                                  |
| `app/schemas/train.py`, `event.py`, `routing.py`                 | nowe                 | kontrakty API                                                                               |
| `app/schemas/network.py`                                         | zmieniony (breaking) | `TrackSegment.status` → `forward`/`backward`                                                |
| `app/services/network_service.py`                                | przepisany           | scala obie skierowane relacje w jeden `TrackSegment`                                        |
| `app/services/routing_service.py`                                | nowy                 | A\* świadome kierunku i ograniczeń prędkości                                                |
| `app/services/train_service.py`                                  | nowy                 | silnik ruchu: dysponowanie, przesuwanie, cykl dojazd→przerwa→powrót, proaktywny rerouting   |
| `app/services/event_service.py`                                  | nowy                 | losowe zdarzenia (harmonogram Poissona), ich zastosowanie i rozwiązywanie                   |
| `app/services/simulation_engine.py`                              | nowy                 | pętla `asyncio` z izolacją błędów                                                           |
| `app/api/routes/trains.py`, `events.py`, `live.py`, `routing.py` | nowe                 | patrz sekcja API niżej                                                                      |
| `app/api/routes/network.py`                                      | bez zmian            | (usunięcie ręcznego `PATCH` z prototypu — nigdy nie istniał na tym branchu)                 |
| `db/seed.py`                                                     | rozszerzony          | +20 stacji, +26 odcinków, nowy schemat 16 pociągów                                          |
| `requirements.txt`                                               | rozszerzony          | `pytest`, `httpx`                                                                           |
| `pytest.ini`                                                     | nowy                 | `pythonpath = .` (żeby `pytest` widział pakiet `app`/`db` niezależnie od sposobu odpalenia) |
| `tests/*.py`                                                     | nowe, 6 plików       | patrz sekcja Testy                                                                          |

### Nowe/zmienione endpointy

- `GET /api/network` — bez zmiany URL, zmieniony kształt (`forward`/`backward` per odcinek)
- `GET /api/trains` — snapshot wszystkich pociągów
- `GET /api/events?status=` — historia i aktywne zdarzenia
- `POST /api/simulation/events/trigger` — debugowe wymuszenie zdarzenia (gated przez `SIM_DEBUG_ENDPOINTS_ENABLED`)
- `GET /api/route/fastest` — A\* jako samodzielne narzędzie (ten sam kod, którego backend używa wewnętrznie)
- `WS /ws/live` — snapshot na connect + broadcast po każdym ticku; ręczna weryfikacja `Origin` względem `ALLOWED_ORIGINS` (CORS middleware nie obejmuje scope `websocket`)

---

## Rozszerzenie sieci o województwo śląskie

Z 10 do **30 stacji** i z 12 do **38 odcinków** (76 skierowanych relacji), w 6 podregionach:

- **Częstochowski** (linia 1): Zawiercie, Myszków, Częstochowa
- **Zagłębie Dąbrowskie**: Czeladź, Będzin (druga, wolniejsza trasa Sosnowiec↔Dąbrowa Górnicza)
- **Rybnicko-raciborski** (linia 140): Racibórz, Wodzisław Śląski, Jastrzębie-Zdrój
- **Podbeskidzie** (linia 139): Pszczyna, Czechowice-Dziedzice, Bielsko-Biała, Żywiec, Cieszyn — najdłuższy jednotorowy łańcuch w sieci, najlepszy kandydat do obserwowania blokad kierunkowych
- **GOP (dogęszczenie)**: Ruda Śląska, Świętochłowice, Siemianowice Śląskie, Piekary Śląskie, Mikołów, Knurów — alternatywne trasy wokół istniejących jednotorówek
- **Wschód**: Jaworzno

16 pociągów (4× IC, 9× REGIONAL, 3× FREIGHT) z przypisanymi na stałe parami stacji.

---

## Frontend — nowe i zmienione pliki

| plik                                             | status           | rola                                                                                                                                                                        |
| ------------------------------------------------ | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lib/types/train.ts`, `event.ts`                 | nowe             | odbicie TS schematów backendu                                                                                                                                               |
| `lib/types/network.ts`                           | zmieniony        | `TrackSegment.forward`/`backward`                                                                                                                                           |
| `lib/services/live.ts`                           | nowy             | store WebSocket z reconnect+backoff i fallbackiem na polling                                                                                                                |
| `lib/components/network/SimulationHeader.svelte` | nowy             | zegar/liczniki, status połączenia, ukryty przycisk debug (`?debug=1`)                                                                                                       |
| `lib/components/network/IncidentFeed.svelte`     | nowy             | lista aktywnych/rozwiązanych zdarzeń z odliczaniem                                                                                                                          |
| `lib/components/network/NetworkGraph.svelte`     | przeprojektowany | dwutorowe odcinki jako dwie niezależnie kolorowane linie, żywe znaczniki pociągów (kształt/kolor wg typu i statusu), pierścień przy stacji z awarią sterowania              |
| `routes/+page.ts`                                | zmieniony        | SSR-prefetch `/api/network` + `/api/trains` + `/api/events` równolegle                                                                                                      |
| `routes/+page.svelte`                            | przeprojektowany | nowy układ: pasek telemetrii + mapa + panel incydentów                                                                                                                      |
| `.prettierrc`                                    | naprawiony       | usunięto martwe odwołanie do nieistniejącego `layout.css` (`prettier-plugin-tailwindcss`), które blokowało `npm run lint` na **całym** projekcie, nie tylko na nowym kodzie |

Trzy panele dyspozytorskie z prototypowej gałęzi (`RouteControlPanel`,
`BreakdownControlPanel`, `TrainControlPanel`) świadomie nie zostały
przeniesione — nie istniały na tym branchu, więc nic nie usunięto, po prostu
nie powielono wzorca ręcznego sterowania (kłóci się z autonomicznością).

---

## Testy

Backend, `pytest` (28/28 przechodzi):

- `test_haversine.py` — poprawność i admissibility heurystyki
- `test_routing_direction_aware.py` — A\* wyklucza tylko zablokowany kierunek, nie oba automatycznie; `restricted` obniża prędkość zamiast wykluczać krawędź
- `test_train_dispatch.py` — cykl dojazd→przerwa→odwrócenie kierunku→powrót; regresja na błąd zahardkodowanego dystansu z prototypu
- `test_event_service.py` — jednotorowy odcinek blokuje oba kierunki, dwutorowy jeden; guard przed podwójnym przypisaniem zdarzenia; wykolejenie tylko na pociągach w drodze
- `test_simulation_tick.py` — proaktywny rerouting pociągów już w drodze po nowej blokadzie; pełny tick z realną fizyką ruchu
- `test_live_ws.py` — connect/snapshot przez `TestClient.websocket_connect`, odrzucanie niedozwolonego `Origin`

Frontend: `svelte-check` (0 błędów) i `eslint` (czysto) na wszystkich nowych/zmienionych plikach.

## Weryfikacja na żywym środowisku

Na uruchomionym stosie Docker (Memgraph + backend + frontend): baza
przeseedowana nowymi danymi; WebSocket faktycznie przesuwał pociągi między
kolejnymi klatkami (potwierdzone surowym klientem WS); wymuszona awaria na
jednotorowym odcinku (Dąbrowa Górnicza–Będzin) poprawnie zablokowała **oba**
kierunki ze wspólnym `active_event_id`; SSR renderuje wszystkie nowe stacje,
pasek telemetrii i panel incydentów bez błędów w logach.

---

## Iteracja 2 — życie na żywo w przeglądarce i pełnoekranowa mapa

Po pierwszej wersji UI zgłoszono problemy: mapa aktualizowała się dopiero po
odświeżeniu strony, klik w pociąg nie pokazywał dokąd zmierza, incydenty nie
były widoczne na mapie, klikanie elementów przestało działać po dodaniu
pan/zoom, a układ panelowy marnował miejsce. Ta iteracja rozwiązuje wszystkie
te punkty i przebudowuje UI na pełnoekranową mapę.

### Naprawa aktualizacji na żywo (root cause)

`compose.yaml` podawał frontendowi jeden adres backendu (`http://backend:8000`)
używany zarówno przy SSR, jak i w przeglądarce. SSR działał (kontener zna
hosta `backend`), ale przeglądarka nie — WebSocket i fallback polling po cichu
padały, więc widok żył tylko do pierwszego renderu. Adresy zostały rozdzielone:

- `PUBLIC_API_BASE_URL` (`http://localhost:8000`) — adres widziany przez
  **przeglądarkę** (WS `/ws/live` + polling),
- `API_INTERNAL_URL` (`http://backend:8000`) — adres widziany przy **SSR**;
  nowy `routes/+page.server.ts` zastąpił `routes/+page.ts`.

Po zmianie env trzeba raz przebudować kontener:
`docker compose up -d --force-recreate frontend`.

### Incydenty widoczne na mapie na żywo

Graf sieci (a z nim stany torów) był pobierany raz przy SSR i nigdy nie
odświeżany — kolory torów nie reagowały na zdarzenia. Nowy
`lib/services/liveNetwork.ts` wylicza stan każdego kierunku odcinka wprost z
aktywnych zdarzeń ze strumienia WS, odwzorowując semantykę
`event_service.py`: jednotorowy odcinek blokuje oba kierunki, blokada ma
pierwszeństwo nad ograniczeniem, `signal_failure` ogranicza wszystkie tory
wokół stacji (`SIM_SPEED_RESTRICTION_FACTOR = 0.5` zduplikowany świadomie —
patrz komentarz w pliku). Dodatkowo każdy aktywny incydent ma pulsującą ikonę
na mapie (⚡ awaria linii, 🚨 wykolejenie, 🐢 ograniczenie, 🚦 awaria
sterowania) — klik w ikonę albo w pozycję panelu incydentów zaznacza dotknięty
element.

### Pociąg jako pełnoprawny wybór

Klik w pociąg otwiera panel z relacją zapisaną **nazwami stacji** (z
uwzględnieniem kierunku tam/powrót), następnym przystankiem, postępem odcinka,
statusem, przyczyną wstrzymania (treść incydentu z `delayedByEventId`) i pełną
trasą z zaznaczeniem bieżącej pozycji. Na mapie podświetla się cała trasa
(`routeSegmentIds`/`routeStationIds`), a stacja docelowa dostaje pulsujący
pierścień.

### Pan & zoom mapy

Sterowanie przez `viewBox` SVG: kółko myszy zmienia zoom w punkt kursora
(od 0,5× — oddalenie poniżej pełnego kadru — do 8×),
przeciąganie przesuwa (z progiem 4 px odróżniającym klik od przeciągnięcia),
dwuklik przybliża, przyciski **+/−/⟲**. Współrzędne przeliczane przez
`getScreenCTM`, więc działa też przy pełnoekranowym SVG o innych proporcjach
niż rysunek (letterboxing). Margines `PAN_MARGIN_RATIO` pozwala wysunąć widok
poza obrys grafu, dzięki czemu mapę można przesuwać **również przy pełnym
oddaleniu**. Linie torów mają `vector-effect: non-scaling-stroke` (nie
grubieją przy zoomie), znaczniki skalują się z `1/√zoom`, a pełne nazwy stacji
pojawiają się dopiero po przybliżeniu (przy oddaleniu tylko kody — mniej
nakładających się etykiet).

**Pułapka, która zepsuła klikanie:** `setPointerCapture` wywołane już w
`pointerdown` sprawia, że późniejszy `click` celuje w SVG zamiast w
stację/pociąg pod kursorem — przechwytywać wolno dopiero w `pointermove`, gdy
przeciąganie faktycznie się zaczyna.

### Pełnoekranowa mapa z panelami-nakładkami

Mapa wypełnia całe okno; reszta pływa na niej: wąski pasek górny (tytuł,
liczniki, status połączenia), po lewej incydenty, po prawej szczegóły
(renderowane tylko, gdy coś wybrano), zoom w prawym dolnym rogu, legenda na
dole. Nic nie jest domyślnie zaznaczone (usunięty auto-wybór najbardziej
ruchliwej stacji); wybór czyści klik w tło mapy, przycisk **×** albo
klawisz **Escape**. Poniżej 900 px szerokości nakładki przechodzą w zwykły
układ pionowy. Stan wyboru mieszka w `+page.svelte` i jest dwukierunkowo
związany (`bind:selected`) z mapą i panelem szczegółów.

### Filtry podświetlenia i dojazd kamery

Chipy w pasku górnym (W drodze / Przerwa / Zatrzymane / Wykolejone /
Incydenty) są przełącznikami filtra (`HighlightFilter` w
`lib/types/selection.ts`): klik wyróżnia na mapie pasujące pociągi (pulsujący
pierścień, pozostałe pociągi wygaszone), a filtr „Incydenty" wygasza wszystko
poza znacznikami zdarzeń, dotkniętymi torami/stacjami i pociągami wstrzymanymi
przez incydent; filtr zdejmuje ponowny klik w aktywny chip (oznaczony
znakiem ×), klik w puste tło mapy albo Escape. Klik w incydent na
liście po lewej dodatkowo płynnie dojeżdża kamerą do miejsca zdarzenia
(eksportowana metoda `focusOn` na mapie + animacja `viewBox` z easingiem,
przerywana każdą ręczną interakcją z mapą; nie oddala, jeśli użytkownik jest
już przybliżony mocniej niż domyślny poziom dojazdu).

### Nowe/zmienione pliki

| plik                                             | status                      | rola                                                                    |
| ------------------------------------------------ | --------------------------- | ----------------------------------------------------------------------- |
| `compose.yaml`, `.env.example`, `README.md`      | zmienione                   | rozdzielenie `PUBLIC_API_BASE_URL` / `API_INTERNAL_URL` + dokumentacja  |
| `routes/+page.server.ts`                         | nowy (zastępuje `+page.ts`) | SSR przez adres wewnętrzny, przeglądarka dostaje publiczny              |
| `routes/+page.svelte`                            | przepisany                  | pełnoekranowa scena z nakładkami, stan wyboru, `liveGraph`              |
| `lib/types/selection.ts`                         | nowy                        | wspólny typ wyboru stacja/odcinek/pociąg                                |
| `lib/services/labels.ts`                         | nowy                        | wspólne etykiety statusów/typów i ikony zdarzeń                         |
| `lib/services/liveNetwork.ts`                    | nowy                        | stany torów wyliczane na żywo z aktywnych zdarzeń                       |
| `lib/components/network/NetworkGraph.svelte`     | przepisany                  | sama mapa: pan/zoom, wybór, podświetlanie tras, znaczniki incydentów    |
| `lib/components/network/DetailsPanel.svelte`     | nowy                        | szczegóły stacji/odcinka/pociągu wydzielone z mapy, przycisk zamknięcia |
| `lib/components/network/IncidentFeed.svelte`     | przerobiony                 | pływający panel, klikalne incydenty wskazujące element na mapie         |
| `lib/components/network/SimulationHeader.svelte` | przerobiony                 | kompaktowy pasek górny zamiast dużego hero                              |

### Weryfikacja

`svelte-check` — 0 błędów, 0 ostrzeżeń; `eslint` i `prettier` czyste na
wszystkich nowych/zmienionych plikach. (Wcześniej istniejące błędy
formatowania w nietkniętych plikach `vitest-examples/*`, `services/network.ts`
i `frontend/README.md` zostawiono bez zmian.)

---

## Świadomie poza zakresem (v1)

- Brak blokady zajętości toru między pociągami (dwa pociągi mogą teoretycznie
  "przenikać się" na tym samym jednotorowym odcinku) — celowe uproszczenie,
  pełna rezerwacja odcinków to nieproporcjonalny nakład względem tego, o co
  proszono.
- Brak limitu peronów, rozkładu jazdy z opóźnieniami, symulacji pasażerów,
  realnej mapy podkładowej, panelu z autoryzacją.

## Dalsze pomysły

1. Blokada zajętości/pierwszeństwo na jednotorowych odcinkach (rezerwacja per
   odcinek+kierunek, priorytet np. towarowy ustępuje IC)
2. Limit peronów per stacja
3. Model rozkładu jazdy + propagacja opóźnień, wskaźnik punktualności
4. Symulacja obłożenia pasażerskiego
5. Prawdziwa mapa podkładowa (MapLibre/Leaflet + OSM)
6. Panel administracyjny z bramką auth do ręcznego sterowania podczas prezentacji
7. Statystyki ticka (`/api/simulation/stats`)
8. Historia incydentów 24h jako raport/wykres — `RailEvent` już to przechowuje

---

# Scenariusze rozkładu pociągów + sterowanie symulacją

Na życzenie: panel scenariuszy utrudnień usunięty w całości (razem z backendem
kroków-zdarzeń i pociągów jednorazowych). Nowy model:

**Scenariusz = rozkład pociągów** — nazwana lista kursów (nazwa, typ
REGIONAL/IC/FREIGHT, stacja początkowa → docelowa, odjazd po X s od startu).
Uruchomienie zastępuje WSZYSTKIE pociągi na sieci flotą rozkładu; pociągi
wjeżdżają o swoich czasach i kursują cyklicznie jak flota bazowa (ten sam
silnik: A\*, blokady, zdarzenia losowe).

- **5 rozkładów startowych** zapisywanych do Memgraph przy pustej bazie
  scenariuszy (wszystkie w pełni edytowalne/usuwalne): Rozkład bazowy Kolei
  Śląskich (pełne 52 pociągi z seed.py), Szczyt poranny GOP, Ekspresy
  dalekobieżne, Korytarz towarowy, Beskidy i południe. Węzły scenariuszy w
  starym formacie są usuwane przy starcie (migracja).
- **Panel po prawej** (`TimetablePanel`): lista rozkładów z ▶ Uruchom i
  Szczegóły; box aktywnego rozkładu (na sieci X/Y pociągów); ➕ Nowy scenariusz.
- **Modal na środku ekranu** (`TimetableEditorModal`, renderowany na poziomie
  strony — dock ma backdrop-filter, który uwięziłby position:fixed): tabela
  pociągów z edycją w miejscu (nazwa, typ, stacje, odjazd), dodawanie/usuwanie
  wierszy, zapis (create/update), usunięcie scenariusza; Esc/backdrop zamyka.
- **Sterowanie w nagłówku**: ⏸ Zatrzymaj / ▶ Wznów symulację oraz 🗑 Usuń
  pociągi (czyści całą flotę bieżącego scenariusza + niewprowadzone wjazdy).
  Pauza = pętla przestaje mutować stan (broadcast dalej idzie, z paused:true);
  wznowienie przesuwa wszystkie zegary (dwell, resolves_at zdarzeń, timer
  losowań, zaplanowane wjazdy) o czas pauzy, więc nic nie "nadrabia" skokowo.
  Uruchomienie rozkładu podczas pauzy kotwiczy odjazdy w momencie pauzy —
  rozkład rusza dokładnie od wznowienia.
- API: `GET/POST /api/scenarios`, `PUT/DELETE /api/scenarios/{id}`,
  `POST /api/scenarios/{id}/run`, `GET /api/scenarios/active`,
  `POST /api/simulation/pause|resume`, `POST /api/simulation/trains/clear`.
  W ramkach WS dodatkowo `scenario` (aktywny rozkład) i `paused`.
- Usunięte: `create_targeted_event` w event_service (powrót do stanu sprzed
  scenariuszy utrudnień), kroki zdarzeń, pociągi jednorazowe z despawnem,
  `ScenarioPanel.svelte`.
- Weryfikacja: 36 testów pytest (10 dla nowego scenario_service, w tym pauza
  z przesuwaniem zegarów); e2e na stacku (podmiana floty, zamrożenie progresu
  w pauzie, wznowienie, CRUD, czyszczenie floty); pełny przepływ UI przez
  Playwright (modal, edycja pociągów, tworzenie/usuwanie rozkładu, pauza —
  chip "Wstrzymano", czyszczenie floty); `svelte-check` 0 błędów.

---

## Iteracja 3 — Poprawki logowania, kontrola dostępu (RBAC) i przekierowania

W tej iteracji usunięto usterki związane z logowaniem administratora, obsługą klawisza `Enter` w formularzach autoryzacji oraz przekierowaniami portów między backendem FastAPI a frontendem SvelteKit.

### Naprawa domyślnego przycisku w formularzu logowania (Enter key bug)

W kodzie HTML formularza autoryzacji ([AuthCard.svelte](file:///C:/Users/Piotr/Desktop/smart-railwaysys/frontend/src/lib/components/site/AuthCard.svelte)) przycisk wejścia w trybie gościa (`formaction="?/guest"`) znajdował się przed przyciskiem właściwego logowania. Zgodnie ze specyfikacją HTML, wciśnięcie klawisza `Enter` w polu tekstowym formularza wywoływało pierwszy submit button w drzewie DOM, nieumyślnie przełączając logującego się administratora w tryb sesji gościa (`srs_guest`).

- **Zmieniono kolejność przycisków w DOM**: Przycisk głównego logowania (`?/login` / `?/register`) umieszczono jako pierwszy w drzewie DOM.
- **Odwrócono kierunek układu w CSS (`flex-direction: row-reverse`)**: Zachowano spójność wizualną (przycisk gościa po lewej stronie, logowanie po prawej), gwarantując jednocześnie, że wciśnięcie klawisza `Enter` zawsze przesyła formularz do akcji logowania.

### Automatyczny zasiew ról i konta administratora

- Zaktualizowano skrypt zasilania bazy [db/seed.py](file:///C:/Users/Piotr/Desktop/smart-railwaysys/backend/db/seed.py), wywołując w nim `ensure_roles` oraz `ensure_admin_user`. Dzięki temu ręczny reseed bazy danych gwarantuje natychmiastowe utworzenie domyślnych ról oraz konta administratora (`admin@smartrailway.pl`).
- Użytkownicy z ważnym tokenem sesji administratora (`srs_session`) i uprawnieniem `users.manage` mają stały dostęp do panelu zarządczego pod adresem `/admin`.

### Przekierowania z backendu FastAPI do frontendu SvelteKit

- W pliku [backend/app/main.py](file:///C:/Users/Piotr/Desktop/smart-railwaysys/backend/app/main.py) dodano trasy przekierowań HTTP 307 (`/admin` oraz `/`) wskazujące bezpośrednio na adres frontendu SvelteKit (`http://localhost:5173/admin` oraz `http://localhost:5173`). Otwarcie ścieżek w przeglądarce na porcie backendu (8000) zamiast pokazywać surową dokumentację Swaggera lub błąd 404 automatycznie przekierowuje użytkownika do interfejsu graficznego.

### Weryfikacja

- `pytest backend/tests` — 51/51 testów przechodzi (100%).
- `svelte-check` — 0 błędów, 0 ostrzeżeń.
- `npm run build` — czysty build produkcyjny bez błędów.

---

## System autoryzacji i kontroli dostępu opartej na rolach (RBAC)

Aplikacja wykorzystuje hybrydowy model autoryzacji łączący sesje ciasteczkowe SvelteKit z bezstanowymi tokenami JWT backendu oraz dynamicznym przypisywaniem uprawnień w bazie danych Memgraph.

### 1. Model danych (Memgraph)

- **Węzeł `User`**:
  - `id`: Unikalny identyfikator użytkownika (np. `USR_a1b2c3d4e5f6`).
  - `email`: Znormalizowany adres e-mail (małe litery, bez spacji). Unikalny na poziomie bazy (`CONSTRAINT`).
  - `password_hash`: Hasło zarehashowane algorytmem `PBKDF2-HMAC-SHA256` z solą urlsafe base64 (310 000 iteracji).
  - `role`: Identyfikator roli przypisanej do użytkownika (domyślnie `user`).
  - `active`: Flaga stanu konta (`true` / `false`). Wyłączone konta nie mogą generować ani weryfikować tokenów.
  - `created_at`: Znacznik czasu utworzenia konta.

- **Węzeł `Role`**:
  - `name`: Nazwa systemowa roli (np. `admin`, `user`, `guest`).
  - `label`: Czytelna nazwa wyświetlana w panelu (np. `Administrator`, `Użytkownik`, `Gość`).
  - `permissions`: Lista kluczy przyznanych uprawnień (np. `["simulation.view", "simulation.control"]`).
  - `is_system`: Flaga uniemożliwiająca usunięcie roli systemowej.

### 2. Katalog uprawnień (`PERMISSIONS`)

Każda operacja chroniona w systemie wymaga posiadania odpowiedniego uprawnienia:

| Klucz uprawnienia | Opis i zakres dostępu |
| --- | --- |
| `simulation.view` | Dostęp do podglądu mapy sieci kolejowej, listy pociągów i zdarzeń na żywo. |
| `simulation.control` | Prawo do sterowania pracą symulacji (pauza, wznawianie, zmiana prędkości, czyszczenie floty). |
| `timetable.manage` | Zarządzanie scenariuszami rozkładów jazdy (tworzenie, edycja, usuwanie i uruchamianie rozkładów). |
| `users.manage` | Dostęp do panelu administratora (`/admin`), zarządzanie kontami (tworzenie, zmiana ról, zmiana haseł, aktywacja/blokowanie, usuwanie). |
| `roles.manage` | Tworzenie nowych ról, edycja etykiet i przypisanych do nich uprawnień oraz usuwanie ról niesystemowych. |

### 3. Domyślne role systemowe (`DEFAULT_ROLES`)

1. **Administrator (`admin`)**:
   - Posiada wszystkie uprawnienia w systemie.
   - Uprawnienia `users.manage` oraz `roles.manage` są zablokowane dla roli `admin` (`ADMIN_LOCKED_PERMISSIONS`), co uniemożliwia ich przypadkowe odebranie i samoblokadę panelu administracyjnego.
   - System chroni ostatniego aktywnego administratora przed usunięciem, wyłączeniem lub degradacją roli.
2. **Użytkownik (`user`)**:
   - Domyślna rola przy rejestracji nowych użytkowników.
   - Posiada uprawnienia: `simulation.view`, `simulation.control`, `timetable.manage`.
3. **Gość (`guest`)**:
   - Rola przypisywana w sesji tymczasowej dla osób nieposiadających konta (wejście przez "Kontynuuj jako gość").
   - Posiada wyłącznie uprawnienie `simulation.view` — wszystkie elementy sterujące i edycyjne są ukryte.

### 4. Przepływ autoryzacji (Authentication Flow)

```text
[Przeglądarka] ─── (Formularz logowania /login) ───> [SvelteKit SSR (+page.server.ts)]
                                                               │
                                                       POST /api/auth/login
                                                               ▼
                                                      [FastAPI Backend]
                                                               │
                                                    Przeszukaj User w Memgraph
                                                   Weryfikacja PBKDF2 Hasha
                                                               │
                                                     Wygeneruj JWT Token
                                                               ▼
[Przeglądarka] <─── Ustaw ciasteczko srs_session <─── [SvelteKit SSR]
```

- **Ciasteczko `srs_session`**: Przechowuje JWT Bearer Token (`httpOnly`, `sameSite: lax`).
- **Ciasteczko `srs_guest`**: Oznacza sesję gościa bez wymogu obecności konta w bazie.
- **Dynamiczna weryfikacja uprawnień**: Backendowy weryfikator `get_current_user` przy każdym zapytaniu REST odszyfrowuje token, sprawdza stan konta w Memgraph i świeżo pobiera aktualne uprawnienia przypisane do roli. Dzięki temu zmiana uprawnień roli w panelu administratora od razu wpływa na aktywnych użytkowników bez konieczności ich ponownego logowania.

### 5. Interfejs zarządczy (`/admin`)

Panel administratora dostępny pod adresem `/admin` umożliwia użytkownikom z uprawnieniem `users.manage`:
- Podgląd i edycję danych wszystkich zarejestrowanych użytkowników.
- Szybki reset hasła dla wybranego użytkownika.
- Przełączanie statusu aktywacji konta (aktywny / zablokowany).
- Zarządzanie rolami i przypisywanie im uprawnień (przy posiadanym `roles.manage`).
- Zakładanie nowych użytkowników z wybraną rolą początkową.


