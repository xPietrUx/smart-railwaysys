# Smart Railway System

Smart Railway System to aplikacja webowa do oglądania i monitorowania wirtualnej sieci kolejowej województwa śląskiego. Projekt składa się z trzech głównych części:

- **frontend** — strona, którą widzi użytkownik
- **backend** — API, które rozmawia z bazą grafową
- **Memgraph** — baza danych przechowująca stacje, tory i pociągi

Jeśli widzisz ten projekt pierwszy raz, najważniejsza rzecz jest taka:  
**frontend nie łączy się bezpośrednio z bazą**. Zawsze pobiera dane z backendu, a backend dopiero pyta Memgraph.

## Co ten projekt pokazuje

Projekt prezentuje autonomiczną symulację ruchu pociągów na sieci kolejowej województwa śląskiego:

- ok. 30 stacji kolejowych jako węzły grafu (konurbacja katowicka + Częstochowa, Zagłębie Dąbrowskie, korytarz rybnicko-raciborski, Podbeskidzie)
- połączenia między stacjami jako relacje `TRACK`, ze stanem liczonym **osobno dla każdego kierunku** (jednotorowy odcinek blokuje oba kierunki naraz, dwutorowy tylko jeden)
- pociągi, które same kursują między swoją stacją początkową i końcową, robią przerwę po dotarciu, a potem wracają — bez ingerencji człowieka
- losowe zdarzenia (awarie linii, wykolejenia, ograniczenia prędkości, awarie sterowania), które pociągi same obsługują: zatrzymują się albo automatycznie przeliczają trasę (algorytm A\*)
- wszystko na żywo przez WebSocket, z podglądem bieżącego stanu grafu w Memgraph

To nie jest tylko statyczna strona. Silnik symulacji działa po stronie backendu niezależnie od tego, czy ktoś ma otwartą przeglądarkę — dane w Memgraph zmieniają się same, na bieżąco.

---

## Jak działa całość

Dwa równoległe przepływy:

**Pierwsze załadowanie strony (SSR):**
1. Użytkownik otwiera stronę w przeglądarce.
2. Frontend (server-side) woła równolegle `GET /api/network`, `GET /api/trains`, `GET /api/events`.
3. Backend pobiera stan z Memgraph i zwraca gotowy JSON.
4. Frontend rysuje graf, pociągi i incydenty w ich aktualnym stanie.

**Życie na żywo (po załadowaniu):**
1. Backend ma własną, autonomiczną pętlę symulacji (co ok. 1s): przesuwa pociągi, rozwiązuje zdarzenia, którym minął czas, i czasem losuje nowe zdarzenie (awaria linii, wykolejenie, ograniczenie prędkości, awaria sterowania).
2. Każdy krok jest od razu zapisywany do Memgraph i rozgłaszany do wszystkich podłączonych klientów przez `WS /ws/live`.
3. Frontend aktualizuje widok na bieżąco, bez przeładowania strony (z automatycznym fallbackiem na odpytywanie REST, jeśli WebSocket nie działa).

Czyli:

**Memgraph <-> backend (silnik symulacji) <-> WebSocket -> frontend -> użytkownik**

---

## Stos technologiczny

| Warstwa | Technologia | Port |
| --- | --- | --- |
| Frontend | SvelteKit + TypeScript | 5173 |
| Backend | Python 3.12 + FastAPI | 8000 |
| Baza danych | Memgraph | 7687 |
| GUI bazy | Memgraph Lab | 3000 |

---

## Struktura repozytorium

```text
smart-railwaysys/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/          # config, lifespan (start/stop pętli symulacji), WS manager
│   │   ├── api/routes/    # network, trains, events, live (WS), routing, health
│   │   ├── services/      # network/routing/train/event serwisy + silnik ticka
│   │   └── schemas/
│   ├── db/
│   │   └── seed.py        # stacje, tory, pociągi (stan startowy)
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   ├── lib/
│   │   │   ├── components/network/  # NetworkGraph, SimulationHeader, IncidentFeed
│   │   │   ├── services/            # network.ts, live.ts (WebSocket + fallback)
│   │   │   └── types/
│   │   └── app.html
│   └── Dockerfile
├── compose.yaml
├── .env.example
└── README.md
```

---

## Szybki start

### 1. Skopiuj `.env`

```powershell
Copy-Item .env.example .env
```

Plik `.env` może zostać prawie bez zmian. Domyślne wartości są ustawione pod lokalne uruchomienie.

### 2. Uruchom cały stack

```bash
docker compose up --build
```

### 3. Załaduj dane startowe

W osobnym terminalu:

```bash
docker compose exec backend python db/seed.py
```

Po chwili powinieneś mieć:

- backend na `http://localhost:8000`
- frontend na `http://localhost:5173`
- Memgraph Lab na `http://localhost:3000`

---

## Co dzieje się przy starcie

Po uruchomieniu:

1. kontener Memgraph startuje jako baza grafowa
2. backend czeka, aż baza będzie gotowa
3. backend sprawdza, czy graf ma dane
4. jeśli graf jest pusty, uruchamia seed
5. frontend pobiera dane z backendu

To ważne, bo `depends_on` w Docker Compose nie oznacza, że baza jest już gotowa do zapytań. Backend ma własny retry mechanizm.

---

## Uruchamianie lokalne

Jeżeli pracujesz bez Dockera, musisz uruchomić osobno:

- backend
- frontend
- Memgraph

W tym projekcie zalecany jest jednak Docker, bo upraszcza środowisko i usuwa różnice między komputerami zespołu.

---

## Konfiguracja środowiska

### `.env`

Najważniejsze zmienne:

- `MEMGRAPH_HOST`
- `MEMGRAPH_PORT`
- `MEMGRAPH_USER`
- `MEMGRAPH_PASSWORD`
- `PUBLIC_API_BASE_URL`

### Co oznacza `PUBLIC_API_BASE_URL`

To adres backendu widziany przez frontend.

- lokalnie: `http://localhost:8000`
- w Dockerze: `http://backend:8000`

Dlaczego? Bo `localhost` w kontenerze oznacza **sam ten kontener**, a nie komputer hosta.

---

## Jak nawigować po kodzie

Jeśli chcesz zrozumieć projekt krok po kroku, czytaj w tej kolejności:

1. `backend/app/main.py` — jak składana jest aplikacja
2. `backend/app/api/routes/network.py` — skąd pochodzi endpoint grafu
3. `backend/app/services/network_service.py` — jak czytane są dane z Memgraph
4. `backend/app/services/train_service.py` — silnik ruchu pociągów (dysponowanie, cykl dojazd/przerwa/powrót)
5. `backend/app/services/event_service.py` — losowe zdarzenia i ich obsługa
6. `backend/app/core/lifespan.py` — jak i kiedy odpala się autonomiczna pętla symulacji
7. `frontend/src/routes/+page.ts` — jak frontend pobiera dane startowe
8. `frontend/src/lib/services/live.ts` — jak frontend odbiera dane na żywo (WebSocket + fallback)
9. `frontend/src/lib/components/network/NetworkGraph.svelte` — jak dane są rysowane

---

## Ważne adresy

- Frontend: `http://localhost:5173` (dodaj `?debug=1`, żeby zobaczyć przycisk ręcznego wywołania zdarzenia losowego)
- Backend API: `http://localhost:8000`
- Backend WebSocket (na żywo): `ws://localhost:8000/ws/live`
- Swagger: `http://localhost:8000/docs`
- Memgraph Lab: `http://localhost:3000`

---

## Gdy coś nie działa

### Frontend pokazuje `fetch failed`

Najczęściej oznacza to:

- backend nie działa
- zły adres API
- backend jeszcze nie wystartował

### Backend nie łączy się z Memgraph

Sprawdź:

- czy Docker działa
- czy kontener bazy wystartował
- czy dane w `.env` są poprawne

### Graf jest pusty

Uruchom seed:

```bash
docker compose exec backend python db/seed.py
```

---

## Jak rozwijać projekt

Jeśli dodajesz nową funkcję:

- backend: nowy route, service i schema
- frontend: nowy route lub komponent w `lib/components`
- wspólne typy: `frontend/src/lib/types`

Nie wkładaj wszystkiego do jednego pliku. Ten projekt jest teraz podzielony warstwowo, żeby dało się go rozwijać bez chaosu.

