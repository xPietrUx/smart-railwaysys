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

| element | zmiana |
|---|---|
| `Station` | bez zmian strukturalnych, +20 nowych węzłów |
| `TRACK` (relacja, nadal 2 skierowane instancje na `segment_id`) | nowe właściwości `restricted_vmax`, `active_event_id`; `status` (`active`/`blocked`/`restricted`) ustawiany **per kierunek**, nie zawsze na oba naraz |
| `Train` | przeprojektowany: `origin_station_id`/`destination_station_id` (stała para wahadłowa), `direction` (`outbound`/`return`), `status` (`running`/`dwelling`/`waiting`/`derailed` — celowo bez stanu końcowego), `route_station_ids`/`route_segment_ids`/`route_index`, `dwell_until`, `delayed_by_event_id` |
| `RailEvent` | **nowy węzeł**: `type` (`line_failure`/`derailment`/`speed_restriction`/`signal_failure`), `severity`, `status`, kontekst zależny od typu, `message` (PL), `started_at`/`resolves_at`/`resolved_at`; relacja `-[:AFFECTS]->` do `Train` przy wykolejeniach |

---

## Backend — nowe i zmienione pliki

| plik | status | rola |
|---|---|---|
| `app/core/haversine.py` | nowy | heurystyka odległości dla A* |
| `app/core/config.py` | rozszerzony | zmienne `SIM_*` sterujące symulacją |
| `app/core/ws_manager.py` | nowy | rozgłaszanie stanu do klientów WebSocket |
| `app/core/lifespan.py` | rozszerzony | start/stop pętli symulacji |
| `app/schemas/train.py`, `event.py`, `routing.py` | nowe | kontrakty API |
| `app/schemas/network.py` | zmieniony (breaking) | `TrackSegment.status` → `forward`/`backward` |
| `app/services/network_service.py` | przepisany | scala obie skierowane relacje w jeden `TrackSegment` |
| `app/services/routing_service.py` | nowy | A* świadome kierunku i ograniczeń prędkości |
| `app/services/train_service.py` | nowy | silnik ruchu: dysponowanie, przesuwanie, cykl dojazd→przerwa→powrót, proaktywny rerouting |
| `app/services/event_service.py` | nowy | losowe zdarzenia (harmonogram Poissona), ich zastosowanie i rozwiązywanie |
| `app/services/simulation_engine.py` | nowy | pętla `asyncio` z izolacją błędów |
| `app/api/routes/trains.py`, `events.py`, `live.py`, `routing.py` | nowe | patrz sekcja API niżej |
| `app/api/routes/network.py` | bez zmian | (usunięcie ręcznego `PATCH` z prototypu — nigdy nie istniał na tym branchu) |
| `db/seed.py` | rozszerzony | +20 stacji, +26 odcinków, nowy schemat 16 pociągów |
| `requirements.txt` | rozszerzony | `pytest`, `httpx` |
| `pytest.ini` | nowy | `pythonpath = .` (żeby `pytest` widział pakiet `app`/`db` niezależnie od sposobu odpalenia) |
| `tests/*.py` | nowe, 6 plików | patrz sekcja Testy |

### Nowe/zmienione endpointy

- `GET /api/network` — bez zmiany URL, zmieniony kształt (`forward`/`backward` per odcinek)
- `GET /api/trains` — snapshot wszystkich pociągów
- `GET /api/events?status=` — historia i aktywne zdarzenia
- `POST /api/simulation/events/trigger` — debugowe wymuszenie zdarzenia (gated przez `SIM_DEBUG_ENDPOINTS_ENABLED`)
- `GET /api/route/fastest` — A* jako samodzielne narzędzie (ten sam kod, którego backend używa wewnętrznie)
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

| plik | status | rola |
|---|---|---|
| `lib/types/train.ts`, `event.ts` | nowe | odbicie TS schematów backendu |
| `lib/types/network.ts` | zmieniony | `TrackSegment.forward`/`backward` |
| `lib/services/live.ts` | nowy | store WebSocket z reconnect+backoff i fallbackiem na polling |
| `lib/components/network/SimulationHeader.svelte` | nowy | zegar/liczniki, status połączenia, ukryty przycisk debug (`?debug=1`) |
| `lib/components/network/IncidentFeed.svelte` | nowy | lista aktywnych/rozwiązanych zdarzeń z odliczaniem |
| `lib/components/network/NetworkGraph.svelte` | przeprojektowany | dwutorowe odcinki jako dwie niezależnie kolorowane linie, żywe znaczniki pociągów (kształt/kolor wg typu i statusu), pierścień przy stacji z awarią sterowania |
| `routes/+page.ts` | zmieniony | SSR-prefetch `/api/network` + `/api/trains` + `/api/events` równolegle |
| `routes/+page.svelte` | przeprojektowany | nowy układ: pasek telemetrii + mapa + panel incydentów |
| `.prettierrc` | naprawiony | usunięto martwe odwołanie do nieistniejącego `layout.css` (`prettier-plugin-tailwindcss`), które blokowało `npm run lint` na **całym** projekcie, nie tylko na nowym kodzie |

Trzy panele dyspozytorskie z prototypowej gałęzi (`RouteControlPanel`,
`BreakdownControlPanel`, `TrainControlPanel`) świadomie nie zostały
przeniesione — nie istniały na tym branchu, więc nic nie usunięto, po prostu
nie powielono wzorca ręcznego sterowania (kłóci się z autonomicznością).

---

## Testy

Backend, `pytest` (28/28 przechodzi):

- `test_haversine.py` — poprawność i admissibility heurystyki
- `test_routing_direction_aware.py` — A* wyklucza tylko zablokowany kierunek, nie oba automatycznie; `restricted` obniża prędkość zamiast wykluczać krawędź
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
