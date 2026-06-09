# Smart Railway System

Interaktywna aplikacja webowa do symulacji i monitorowania wirtualnego ruchu kolejowego na sieci województwa śląskiego.

## Stos technologiczny

| Warstwa     | Technologia                           | Port        |
| ----------- | ------------------------------------- | ----------- |
| Frontend    | SvelteKit + TypeScript + Tailwind CSS | 5173        |
| Backend     | Python 3.12 + FastAPI                 | 8000        |
| Baza danych | Memgraph (graf in-memory)             | 7687 (Bolt) |
| GUI bazy    | Memgraph Lab                          | 3000        |

---

## Wymagania wstępne

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — jedyna rzecz, którą trzeba zainstalować
- Git

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
docker compose exec backend python db/seed.py
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
{ "message": "Połączenie z backendem udane" }
```

Interaktywna dokumentacja API (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend

Otwórz [http://localhost:5173](http://localhost:5173) — powinna załadować się strona aplikacji.

## Zatrzymanie projektu

```bash
# Zatrzymuje kontenery, zachowuje dane w bazie
docker compose down

# Zatrzymuje kontenery i usuwa wszystkie dane (czysty start)
# NIE WYKONYWAĆ JEŚLI NIE MA PROBLEMÓW!!!
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
