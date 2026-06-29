# Memgraph data and seed

Ten folder zawiera wszystko, co dotyczy danych startowych w Memgraph.

Najważniejszy plik to:

- `seed.py` — tworzy i wypełnia graf

---

## Co robi seed

Seed ustawia stan bazy od zera.

W praktyce:

1. usuwa stare dane
2. tworzy constrainty
3. dodaje stacje
4. dodaje relacje `TRACK`
5. dodaje pociągi

Dzięki temu każdy, kto uruchomi projekt, dostaje ten sam przewidywalny stan.

---

## Dlaczego seed jest ważny

Bez seeda:

- baza mogłaby być pusta
- frontend nie miałby czego narysować
- trudno byłoby debugować projekt

Seed daje powtarzalne środowisko i ułatwia pracę zespołową.

---

## Jak uruchomić seed

W katalogu głównym projektu:

```bash
docker compose exec backend python db/seed.py
```

Można uruchamiać wielokrotnie.
Skrypt najpierw czyści dane, więc zawsze zaczynasz od znanego stanu.

---

## Co znajduje się w grafie

### Węzły `Station`

Stacje mają m.in.:

- `id`
- `name`
- `type`
- `lat`
- `lon`
- `platforms`
- `tracks`
- `daily_trains`

### Relacje `TRACK`

Relacje opisują odcinek między stacjami:

- `segment_id`
- `line`
- `dist_km`
- `vmax`
- `rail_tracks`
- `travel_min`
- `status`

### Węzły `Train`

Pociągi są osobnym elementem grafu i pokazują stan ruchu:

- identyfikator
- typ
- prędkość
- pozycja
- status

---

## Memgraph Lab

Do podglądu danych używaj:

```text
http://localhost:3000
```

Tam możesz:

- podejrzeć graf
- uruchamiać zapytania Cypher
- sprawdzać, czy seed poprawnie wypełnił bazę

Przykładowe zapytanie:

```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
```

---

## Jak sprawdzić, czy baza działa

Jeśli chcesz szybko zweryfikować stan:

```cypher
MATCH (s:Station) RETURN count(s)
```

Jeśli wynik jest większy od zera, graf ma dane.

---

## Typowe użycie

Seed uruchamiasz gdy:

- pierwszy raz odpalasz projekt
- chcesz zresetować dane
- chcesz porównać zachowanie po zmianie modeli grafu

