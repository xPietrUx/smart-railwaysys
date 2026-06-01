# Smart Railway System

Interaktywna aplikacja webowa do symulacji i monitorowania wirtualnego ruchu kolejowego na sieci województwa śląskiego.

## Stos technologiczny

| Warstwa | Technologia | Port |
|---|---|---|
| Frontend | SvelteKit + TypeScript + Tailwind CSS | 5173 |
| Backend | Python 3.12 + FastAPI | 8000 |
| Baza danych | Memgraph (graf in-memory) | 7687 (Bolt) |
| GUI bazy | Memgraph Lab | 3000 |

---

## Wymagania wstępne

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — jedyna rzecz, którą trzeba zainstalować
- Git

Opcjonalnie do lokalnego developmentu bez Dockera:
- Python 3.12+
- Node.js 20+

---

## Pierwsze uruchomienie (tylko raz po clone)

```bash
git clone <link-do-repo>
cd smart-railwaysys
```

**1. Utwórz plik `.env` na podstawie przykładu:**

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Plik `.env` możesz zostawić bez zmian — domyślne wartości działają lokalnie.

**2. Zbuduj i uruchom kontenery:**

```bash
docker compose build --no-cache
docker compose up
```

Poczekaj aż w konsoli pojawi się:
```
backend-1   | INFO:     Application startup complete.
frontend-1  | Local:   http://localhost:5173/
```

**3. Załaduj dane startowe do bazy (w osobnym terminalu):**

```bash
docker compose exec backend python db/seed.py
```

Oczekiwany wynik:
```
✓ Baza wyczyszczona, constrainty gotowe
✓ Stacje utworzone
✓ Tory utworzone
✓ Pociągi utworzone
✅ Dane wgrane pomyślnie!
```

---

## Codzienna praca (rutynowy start)

```bash
docker compose up --watch
```

Tryb `--watch` = hot-reload: zmiany w plikach `.svelte`, `.py` są od razu widoczne bez restartu kontenerów. Zatrzymanie: `Ctrl+C`.

---

## Weryfikacja — czy wszystko działa?

Po uruchomieniu sprawdź każdy punkt po kolei:

### 1. Backend API

Otwórz w przeglądarce lub wklej w terminal:

```bash
curl http://localhost:8000/api/hello
```

Oczekiwana odpowiedź:
```json
{"message": "Połączenie z backendem udane"}
```

Interaktywna dokumentacja API (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend

Otwórz [http://localhost:5173](http://localhost:5173) — powinna załadować się strona aplikacji.

### 3. Dane w bazie (Memgraph Lab)

Otwórz [http://localhost:3000](http://localhost:3000) → kliknij **Connect** (dane połączenia są wypełnione automatycznie).

W zakładce **Query** wklej i uruchom:

```cypher
-- Podgląd całego grafu (stacje + tory)
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
```

```cypher
-- Lista stacji
MATCH (s:Station) RETURN s.id, s.name, s.type ORDER BY s.name
```

```cypher
-- Lista pociągów z aktualną pozycją
MATCH (t:Train) RETURN t.id, t.name, t.type, t.status, t.current_from, t.current_to, t.progress
```

Powinno zwrócić 10 stacji, 12 par torów (24 relacje), 4 pociągi.

---

## Ponowne wczytanie danych (reset bazy)

Seed jest **idempotentny** — czyści bazę przed załadowaniem, więc można go uruchamiać wielokrotnie:

```bash
docker compose exec backend python db/seed.py
```

---

## Zatrzymanie projektu

```bash
# Zatrzymuje kontenery, zachowuje dane w bazie
docker compose down

# Zatrzymuje kontenery i usuwa wszystkie dane (czysty start)
docker compose down -v
```

Całkowite czyszczenie cache Dockera (np. gdy coś się posypie przy budowaniu):

```bash
docker compose down -v
docker builder prune -a -f
```

---

## Struktura projektu

```
smart-railwaysys/
├── backend/
│   ├── app/
│   │   └── main.py          # FastAPI — punkt wejścia backendu
│   ├── db/
│   │   └── seed.py          # Ładowanie danych startowych do Memgraph
│   ├── routes/              # Endpointy API (w budowie)
│   ├── services/            # Logika biznesowa (w budowie)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   └── routes/          # Strony SvelteKit
│   └── Dockerfile
├── compose.yaml             # Definicja wszystkich serwisów
├── .env.example             # Szablon zmiennych środowiskowych
└── .env                     # Twój lokalny config (nie commitować!)
```

---

## Częste problemy

**`docker compose up` kończy się błędem portu:**
Inny program zajmuje port 5173, 8000 lub 3000. Zamknij inne projekty lub sprawdź `docker ps`.

**Seed kończy się błędem połączenia:**
Memgraph jeszcze się uruchamia. Poczekaj 10–15 sekund i spróbuj ponownie.

**Zmiany w kodzie nie są widoczne:**
Upewnij się, że uruchomiono `docker compose up --watch`, a nie samo `docker compose up`.

**Chcę uruchomić backend lokalnie (bez Dockera):**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Wymaga działającego kontenera Memgraph: `docker compose up memgraph-db`.
