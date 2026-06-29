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

Prosty health check.

Używany do sprawdzenia, czy backend działa.

### `GET /api/network`

Zwraca aktualny graf z Memgraph.

Wynik zawiera:

- listę stacji
- listę unikalnych segmentów
- liczbę relacji w bazie

Frontend korzysta właśnie z tego endpointu.

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

## Seed danych

Plik `backend/db/seed.py` odpowiada za:

- utworzenie stacji
- utworzenie relacji `TRACK`
- dodanie pociągów
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
│   │   ├── config.py
│   │   └── lifespan.py
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   ├── services/
│   └── schemas/
├── db/
│   └── seed.py
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
- `app/core/lifespan.py` — start i stop backendu
- `app/api/routes/network.py` — endpoint grafu
- `app/services/network_service.py` — query do Memgraph
- `app/schemas/network.py` — format odpowiedzi
- `db/seed.py` — dane startowe

---

## Wymagane środowisko

- Python 3.12+
- Memgraph uruchomiony i dostępny pod `MEMGRAPH_HOST`
- poprawny plik `.env`

### Najważniejsze zmienne

- `MEMGRAPH_HOST`
- `MEMGRAPH_PORT`
- `MEMGRAPH_USER`
- `MEMGRAPH_PASSWORD`

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
