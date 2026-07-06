# Smart Railway System

Smart Railway System to aplikacja webowa do oglądania i monitorowania wirtualnej sieci kolejowej województwa śląskiego. Projekt składa się z trzech głównych części:

- **frontend** — strona, którą widzi użytkownik
- **backend** — API, które rozmawia z bazą grafową
- **Memgraph** — baza danych przechowująca stacje, tory i pociągi

Jeśli widzisz ten projekt pierwszy raz, najważniejsza rzecz jest taka:  
**frontend nie łączy się bezpośrednio z bazą**. Zawsze pobiera dane z backendu, a backend dopiero pyta Memgraph.

## Co ten projekt pokazuje

Projekt prezentuje:

- stacje kolejowe jako węzły grafu
- połączenia między stacjami jako relacje `TRACK`
- szczegóły stacji, takie jak liczba torów, peronów i przejazdów
- aktualny graf pobrany z Memgraph na żywo

To nie jest tylko statyczna strona. Dane pochodzą z bazy, więc po zmianie grafu frontend może od razu pokazać nowy stan.

---

## Jak działa całość

Przepływ danych wygląda tak:

1. Użytkownik otwiera stronę w przeglądarce.
2. Frontend woła backend pod `GET /api/network`.
3. Backend łączy się z Memgraph.
4. Backend pobiera stacje i relacje.
5. Backend zwraca gotowy JSON.
6. Frontend rysuje graf i pokazuje szczegóły.

Czyli:

**Memgraph -> backend -> frontend -> użytkownik**

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
│   │   ├── core/
│   │   ├── api/
│   │   ├── services/
│   │   └── schemas/
│   ├── db/
│   │   └── seed.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   ├── lib/
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
4. `frontend/src/routes/+page.ts` — jak frontend pobiera dane
5. `frontend/src/lib/components/network/NetworkGraph.svelte` — jak dane są rysowane

---

## Ważne adresy

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
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

