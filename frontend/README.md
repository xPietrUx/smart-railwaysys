# Frontend architecture

Frontend to część aplikacji widoczna w przeglądarce. W tym projekcie frontend ma jedno główne zadanie:

- pobrać dane z backendu
- pokazać graf kolejowy
- pozwolić użytkownikowi kliknąć stację lub połączenie

Frontend **nie zna Memgraph bezpośrednio**. Zna tylko backendowy kontrakt API.

---

## Jak frontend jest zbudowany

```text
src/
├── routes/
├── lib/
├── app.html
└── app.d.ts
```

### `src/routes/`
To warstwa stron.

W tym projekcie:

- `+page.ts` pobiera dane
- `+page.svelte` przekazuje dane do komponentu

Ta warstwa powinna być cienka. Nie wkładamy tu zbyt dużo logiki.

### `src/lib/services/`
Tu trzymamy komunikację z API.

Przykład:

- budowanie URL
- wykonanie `fetch`
- obsługa błędów

Jeśli później dodamy kolejne ekrany, ta warstwa ma ułatwić ponowne użycie logiki pobierania.

### `src/lib/types/`
Tu definiujemy typy danych wspólne dla frontendu.

Najważniejsze:

- `NetworkGraph`
- `StationNode`
- `TrackSegment`

To są typy, które opisują dane zwracane przez backend.

### `src/lib/components/`
Tu trafiają gotowe komponenty UI.

W tym projekcie najważniejszy jest komponent grafu.

To dobry podział, bo:

- strona nie staje się ogromnym plikiem
- komponent można później wykorzystać gdzie indziej
- łatwiej utrzymać styl i logikę oddzielnie

---

## Przepływ danych

1. `+page.ts` pyta backend o graf.
2. Backend zwraca JSON.
3. `+page.svelte` dostaje dane.
4. Komponent `NetworkGraph.svelte` rysuje graf.

To oznacza, że:

- logika pobierania danych jest w jednym miejscu
- logika prezentacji jest w innym
- komponent UI nie pobiera danych sam

---

## Aktualna architektura ekranu głównego

### `src/routes/+page.ts`
To loader strony.

On:

- pobiera dane
- nie renderuje UI
- nie zna szczegółów grafu

### `src/routes/+page.svelte`
To cienka strona.

Jej zadanie to:

- przyjąć dane z loadera
- przekazać je do komponentu

### `src/lib/components/network/NetworkGraph.svelte`
To główny komponent wizualny.

On:

- liczy pozycje węzłów
- rysuje relacje
- obsługuje wybór stacji i segmentów
- pokazuje szczegóły

---

## Konfiguracja API

Frontend używa zmiennej:

```env
PUBLIC_API_BASE_URL=http://localhost:8000
```

### Co ona oznacza?

To adres backendu, z którego frontend ma pobierać dane.

- lokalnie: `http://localhost:8000`
- w Dockerze: `http://backend:8000`

### Dlaczego to ważne?

W kontenerze `localhost` oznacza sam frontend, a nie cały komputer ani backend.
Dlatego w Dockerze trzeba wskazać nazwę usługi `backend`.

---

## Co jest w UI

Aktualna strona pokazuje:

- liczbę stacji
- liczbę unikalnych segmentów
- liczbę relacji w bazie
- interaktywny graf
- panel szczegółów

Użytkownik może:

- kliknąć stację
- kliknąć segment
- przejść między powiązanymi elementami

---

## Jak rozwijać frontend

Jeśli dodajesz nową funkcję:

1. jeśli to nowy ekran, dodaj nowy route
2. jeśli to logika API, dodaj serwis
3. jeśli to nowe dane, dodaj typy
4. jeśli to UI, dodaj komponent w `lib/components`

### Dobra praktyka

- nie trzymaj fetchy w komponentach
- nie trzymaj dużych danych w `+page.svelte`
- nie duplikuj typów ręcznie w wielu plikach

---

## Gdzie szukać czego

- `src/routes/+page.ts` — pobieranie danych
- `src/routes/+page.svelte` — składanie strony
- `src/lib/services/network.ts` — fetch do backendu
- `src/lib/types/network.ts` — typy odpowiedzi
- `src/lib/components/network/NetworkGraph.svelte` — graf i szczegóły

---

## Uruchamianie

### W Dockerze

```bash
docker compose up --build
```

### Lokalne sprawdzenie

Frontend działa na:

```text
http://localhost:5173
```

---

## Typowe problemy

### `fetch failed`

Najczęściej oznacza:

- backend nie działa
- zły adres API
- frontend używa `localhost` w Dockerze zamiast `backend`

### Strona się ładuje, ale graf jest pusty

Backend może zwracać pustą bazę. Wtedy uruchom seed.

### Kliknięcie nie działa

Sprawdź, czy przeglądarka nie blokuje błędów JS i czy dane przyszły poprawnie.

