# Backend architecture

Ten folder zawiera API, które łączy frontend z Memgraph. Backend i jego zadania:

- uruchomienie aplikacji FastAPI
- utrzymanie połączenia z Memgraph
- pobieranie danych z grafu
- zwracanie ich w czytelnym JSON-ie

**Backend jest pośrednikiem między frontendem a bazą**.

---

## Jak backend jest zbudowany

Backend jest podzielony na warstwy:

```text
app/
├── main.py
├── core/
├── api/
├── services/
└── schemas/
```

### Co robi każda warstwa

#### `app/main.py`

To punkt wejścia aplikacji.

Tu znajduje się:

- utworzenie obiektu `FastAPI`
- CORS
- dołączenie routerów
- użycie lifecycle `lifespan`

W `main.py` nie powinno być ciężkiej logiki.
To ma być plik, który **składa aplikację**, a nie rozwiązuje problemy biznesowe.

#### `app/core/`

Tu trzymamy rzeczy wspólne dla całej aplikacji:

- konfigurację
- lifecycle
- ustawienia CORS
- przygotowanie połączeń z usługami zewnętrznymi

To miejsce na kod, który jest potrzebny globalnie, a nie tylko w jednym endpointcie.

#### `app/api/`

Tu trafia warstwa HTTP.

`api/` odpowiada za:

- odbieranie requestów
- walidację podstawowych parametrów
- wołanie odpowiednich serwisów
- zwracanie odpowiedzi

Nie mieszamy tu query do bazy z większą logiką. Router ma być możliwie cienki.

#### `app/services/`

Tu znajduje się logika pracy z danymi.

Jeśli endpoint ma:

- wykonać kilka query
- przetworzyć wynik
- zbudować strukturę odpowiedzi

to właśnie tu powinno się to znaleźć.

#### `app/schemas/`

Tu trzymamy modele danych zwracanych przez API.

To jest kontrakt między backendem a frontendem.

Jeżeli frontend ma dostać:

- `stations`
- `segments`
- `relationshipCount`

to właśnie ten kształt powinien być opisany w schematach.

---

## Przepływ requestu

Dla endpointu `GET /api/network` przepływ wygląda tak:

1. frontend wysyła request
2. router odbiera request
3. dependency dostarcza aktywny driver do Memgraph
4. serwis wykonuje query
5. schema opisuje wynik
6. backend odsyła JSON

To bardzo ważne, bo dzięki temu każda część ma jedną odpowiedzialność.

---

## Endpointy

### `GET /api/hello`

Prosty health check. Używany do sprawdzenia, czy backend działa.

### `GET /api/network`

Zwraca aktualny graf z Memgraph: stacje, odcinki torów (ze stanem **osobnym dla
każdego kierunku** — `forward`/`backward`) i liczbę relacji w bazie.

### `GET /api/trains`

Zwraca aktualny stan wszystkich pociągów (pozycja, status, kierunek, trasa).

### `GET /api/events`

Zwraca listę zdarzeń losowych (`?status=active` albo `?status=resolved`, żeby
przefiltrować). Zdarzenia to: `line_failure`, `derailment`, `speed_restriction`,
`signal_failure`.

### `POST /api/simulation/events/trigger`

Debugowe/demonstracyjne wymuszenie zdarzenia (opcjonalnie `?eventType=...`), poza
normalnym losowym harmonogramem. Idzie przez tę samą logikę co scheduler — nie ma
osobnej ścieżki mutującej stan torów. Wyłączane przez `SIM_DEBUG_ENDPOINTS_ENABLED=false`.

### `GET /api/route/fastest`

Liczy najszybszą trasę A* między dwiema stacjami (`?from_station=&to_station=&train_type=`).
Ten sam algorytm, którego backend używa wewnętrznie do dysponowania pociągów.

### `WS /ws/live`

Główny kanał na żywo. Po połączeniu wysyła pełny snapshot, potem broadcastuje
zaktualizowany stan po każdym kroku symulacji (ok. raz na sekundę). Frontend
korzysta z tego jako podstawowego źródła danych, z automatycznym fallbackiem na
odpytywanie REST (`/api/trains` + `/api/events`), jeśli WebSocket nie działa.

Frontend korzysta z tych endpointów łącznie — `/api/network` + `/api/trains` +
`/api/events` przy pierwszym załadowaniu strony, potem `/ws/live` na bieżąco.

---

## Połączenie z Memgraph

Backend łączy się z Memgraph podczas startu aplikacji.

Co się dzieje:

1. backend próbuje połączyć się z bazą
2. jeśli baza jeszcze nie działa, próbuje ponownie
3. po udanym połączeniu sprawdza, czy graf ma dane
4. jeśli graf jest pusty, uruchamia seed

To pozwala na stabilny start w Dockerze.

### Dlaczego retry jest potrzebny?

Bo w Docker Compose serwisy uruchamiają się równolegle.
`depends_on` mówi tylko kolejność startu, a nie to, że Memgraph jest już gotowy na zapytania.

---

## Silnik symulacji

Po starcie (`app/core/lifespan.py`) backend uruchamia w tle autonomiczną pętlę
(`app/services/simulation_engine.py`), niezależną od tego, czy ktoś ma otwartą
przeglądarkę:

1. `app/services/train_service.py` — rdzeń: przesuwanie pociągów po torach,
   dysponowanie/przeliczanie trasy (A* z `routing_service.py`), cykl
   dojazd -> przerwa -> odwrócenie kierunku -> powrót.
2. `app/services/event_service.py` — losowe zdarzenia (proces Poissona, nie rzut
   monetą co tick): awarie linii i wykolejenia blokują odcinek (jednotorowy w obu
   kierunkach, dwutorowy tylko w jednym — na podstawie `rail_tracks`), ograniczenia
   prędkości i awarie sterowania tylko obniżają efektywne vmax.
3. Co krok stan jest zapisywany do Memgraph (Memgraph to baza in-memory, więc to
   tanie) i rozgłaszany przez `/ws/live`.

Tempo symulacji steruje się zmiennymi środowiskowymi (patrz `app/core/config.py`),
m.in. `SIM_TICK_INTERVAL_S`, `SIM_TIME_SCALE`, `SIM_EVENT_MEAN_INTERVAL_REAL_S`.

## Seed danych

Plik `backend/db/seed.py` odpowiada za:

- utworzenie stacji (ok. 30, całe województwo śląskie)
- utworzenie relacji `TRACK` (obie skierowane, z osobnym stanem per kierunek)
- dodanie pociągów (ok. 16, każdy ze stałą parą stacji start/koniec, startują jako `waiting` — pierwszy tick sam je dysponuje)
- wyczyszczenie bazy przed ponownym załadowaniem

Seed jest przydatny, gdy:

- baza jest pusta
- chcesz zresetować dane
- chcesz odtworzyć znany stan środowiska

---

## Struktura katalogów

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py       # w tym zmienne SIM_* sterujące symulacją
│   │   ├── lifespan.py      # start/stop pętli symulacji
│   │   ├── ws_manager.py    # broadcast do klientów WebSocket
│   │   └── haversine.py     # heurystyka dla A*
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/          # network, trains, events, live (WS), routing, health
│   ├── services/
│   │   ├── network_service.py
│   │   ├── routing_service.py     # A*
│   │   ├── train_service.py       # silnik ruchu pociągów + tick
│   │   ├── event_service.py       # losowe zdarzenia
│   │   └── simulation_engine.py   # pętla asyncio
│   └── schemas/
├── db/
│   └── seed.py
├── tests/
├── Dockerfile
└── requirements.txt
```

---

## Jak rozwijać backend

Jeśli dodajesz nową funkcję:

1. dodaj nowy router w `app/api/routes/`
2. jeśli potrzeba, dodaj serwis w `app/services/`
3. jeśli zmienia się kształt odpowiedzi, dodaj lub zmodyfikuj schema w `app/schemas/`

### Zasada praktyczna

- router ma mówić **co** się dzieje
- serwis ma mówić **jak** to się dzieje
- schema ma mówić **jak wygląda wynik**

---

## Gdzie szukać konkretów

- `app/main.py` — składanie aplikacji
- `app/core/lifespan.py` — start i stop backendu oraz pętli symulacji
- `app/services/train_service.py` — silnik ruchu pociągów i orkiestracja ticka
- `app/services/event_service.py` — losowe zdarzenia (awarie, wykolejenia...)
- `app/services/routing_service.py` — A*, świadome kierunku blokad
- `app/api/routes/live.py` — WebSocket na żywo
- `app/schemas/network.py` — format odpowiedzi (w tym `forward`/`backward` per odcinek)
- `db/seed.py` — dane startowe

---

## Wymagane środowisko

- Python 3.12+
- Memgraph uruchomiony i dostępny pod `MEMGRAPH_HOST`
- poprawny plik `.env`

### Najważniejsze zmienne

- `MEMGRAPH_HOST`, `MEMGRAPH_PORT`, `MEMGRAPH_USER`, `MEMGRAPH_PASSWORD`
- `SIM_TICK_INTERVAL_S` (domyślnie `1.0`) — co ile realnych sekund krok symulacji
- `SIM_TIME_SCALE` (domyślnie `60.0`) — ile symulowanych sekund ruchu na 1 realną sekundę
- `SIM_EVENT_MEAN_INTERVAL_REAL_S` (domyślnie `45.0`) — średni odstęp losowych zdarzeń
- `SIM_DEBUG_ENDPOINTS_ENABLED` (domyślnie `true`) — czy `POST /api/simulation/events/trigger` jest dostępne

Pełna lista w `app/core/config.py`.

---

## Uruchamianie

Najprościej przez Docker Compose:

```bash
docker compose up --build
```

Seed:

```bash
docker compose exec backend python db/seed.py
```

---

## Typowe problemy

### Backend nie startuje

Sprawdź:

- czy Memgraph działa
- czy `.env` ma poprawne dane
- czy Docker uruchomił wszystkie serwisy

### Endpoint zwraca 503

To znaczy, że backend nie ma jeszcze aktywnego drivera do Memgraph.

### Graf zwraca puste dane

Najpewniej trzeba uruchomić seed.
