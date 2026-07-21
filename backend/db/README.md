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

Każdy fizyczny odcinek to **dwie** skierowane relacje (tam i z powrotem) dzielące
to samo `segment_id` — dzięki temu stan można zmieniać osobno per kierunek
(jednotorowy odcinek: awaria blokuje obie relacje naraz; dwutorowy: tylko jedną).

- `segment_id`, `line`, `dist_km`, `vmax`, `rail_tracks`, `travel_min`
- `status` — `active` / `blocked` / `restricted`
- `restricted_vmax` — obniżone vmax, gdy `status='restricted'`
- `active_event_id` — powiązanie z węzłem `RailEvent`, który to spowodował

### Węzły `Train`

Pociągi żyją w grafie i są na bieżąco aktualizowane przez silnik symulacji
(`app/services/train_service.py`), nie tylko wczytywane raz przy starcie:

- `origin_station_id` / `destination_station_id` — stała para, między którą pociąg kursuje tam i z powrotem
- `direction` (`outbound` / `return`), `current_station_id`, `next_station_id`, `current_segment_id`, `progress`
- `status` — `running` / `dwelling` (przerwa po dotarciu) / `waiting` (brak trasy, próbuje ponownie co tick) / `derailed`
- `route_station_ids`, `route_segment_ids`, `route_index` — aktualnie zaplanowana trasa (A*)
- `vmax`, `priority`, `mass_tonnes`, `length_m`, `accel`, `decel`, `dwell_until`, `delayed_by_event_id`

### Węzły `RailEvent`

Historia i aktywny stan losowych zdarzeń (`app/services/event_service.py`):

- `type` — `line_failure` / `derailment` / `speed_restriction` / `signal_failure`
- `severity` (`minor`/`major`), `status` (`active`/`resolved`)
- kontekst zależny od typu: `segment_id`+`from_station_id`+`to_station_id`, `station_id`, `train_id`, `restricted_vmax`
- `message` (czytelny opis PL), `started_at`, `resolves_at`, `resolved_at`
- relacja `(:RailEvent)-[:AFFECTS]->(:Train)` dla wykolejeń

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

