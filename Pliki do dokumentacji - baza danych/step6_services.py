#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 6 — Warstwa pociagow.

TRZY WARSTWY O ROZNEJ WIARYGODNOSCI
  (A) REGIONALNE — zrodlo pierwotne: feed GTFS Kolei Slaskich. Oznaczenia linii
      (S1, S5, S71...), relacje, kolejnosc postojow i godziny odjazdow pochodza
      wprost z rozkladu obowiazujacego. confidence = "measured".
  (B) DALEKOBIEZNE — rozklady PKP Intercity nie byly dostepne maszynowo
      w srodowisku budowy (brak dostepu do portalpasazera.pl, limit API).
      Relacje odtworzono na podstawie znanych, faktycznie kursujacych polaczen
      przez wezel slaski; godziny sa przyblizone. confidence = "modeled".
      Do zastapienia danymi z portalpasazera.pl przy aktualizacji bazy.
  (C) TOWAROWE — rozklady pociagow towarowych NIE SA JAWNE (stanowia informacje
      handlowa przewoznikow). Odtworzono realne korytarze przewozowe wystepujace
      w regionie; numery i godziny sa modelowe. confidence = "modeled".

WYBOR WARIANTU TRASY (warstwa A)
Jedna linia S wystepuje w rozkladzie w wielu wariantach (rozne dlugosci relacji,
kursy skrocone). Dla kazdej relacji wybieramy wariant DOMINUJACY — sekwencje
postojow powtarzajaca sie w najwiekszej liczbie kursow. Jest to wariant
najbardziej reprezentatywny dla danej linii.

RZUTOWANIE NA WEZLY BAZY
Trasa z GTFS zawiera wszystkie przystanki; baza zawiera tylko wybrane wezly
(krok 4). Trase rzutujemy zachowujac wylacznie te przystanki, ktore sa wezlami
bazy, z zachowaniem kolejnosci. Relacje, ktore po rzutowaniu maja mniej niz
2 wezly, sa pomijane.

PARAMETRY TABOROWE
Masa, dlugosc i przyspieszenia to wartosci typowe dla klas pojazdow
eksploatowanych w regionie (EZT serii EN57/EN76/45WE dla ruchu regionalnego,
sklad wagonowy z lokomotywa dla dalekobieznego, sklad wegłowy z lokomotywa
towarowa dla przewozow masowych). Sa to parametry MODELOWE — nie pochodza
z dokumentacji taborowej przewoznikow.
"""
import csv, json, os, collections, unicodedata


def ascii3(t):
    """Trzyliterowy skrot ASCII — identyfikatory musza byc wolne od znakow diakrytycznych."""
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = "".join(c for c in t.upper() if c.isalnum())
    return (t + "XXX")[:3]

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS = os.path.join(BASE, "src", "gtfs_ks")
WORK = os.path.join(BASE, "work")

# --- parametry taborowe (modelowe) -------------------------------------------
TABOR = {
    "REGIONAL": dict(vmax=120, mass_tonnes=120, length_m=60, accel=0.6, decel=0.9,
                     priority=2, opis="EZT ruchu regionalnego (klasa EN57/EN76/45WE)"),
    "IC":       dict(vmax=160, mass_tonnes=420, length_m=200, accel=0.5, decel=0.8,
                     priority=3, opis="sklad wagonowy z lokomotywa elektryczna"),
    "FREIGHT":  dict(vmax=80,  mass_tonnes=1800, length_m=550, accel=0.25, decel=0.4,
                     priority=1, opis="sklad towarowy masowy z lokomotywa towarowa"),
}


def read(n):
    with open(os.path.join(GTFS, n), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    with open(os.path.join(WORK, "selected.json"), encoding="utf-8") as f:
        sel = json.load(f)
    with open(os.path.join(WORK, "graph_clean.json"), encoding="utf-8") as f:
        nodes = json.load(f)["nodes"]

    wybrane = set(sel["selected"])
    name_of = {sid: nodes[sid]["name"] for sid in nodes}
    id_by_name = {}
    for sid in wybrane:
        id_by_name[name_of[sid]] = sid

    # graf odcinkow — do sprawdzenia, czy trasa jest przejezdna w bazie
    seg_between = set()
    for s in sel["segments"]:
        seg_between.add((s["a"], s["b"]))
        seg_between.add((s["b"], s["a"]))

    # --- rozwiniecie tras modelowanych po krawedziach grafu -----------------
    # Trasy warstw (B) i (C) podawane sa jako lista stacji charakterystycznych
    # (np. Katowice, Tychy, Czechowice), ktore NIE MUSZA byc bezposrednimi
    # sasiadami w grafie bazy — miedzy nimi leza posterunki wybrane w kroku 4.
    # Wpisanie takiej listy wprost dawaloby trase z "przeskokami" bez
    # odpowiadajacej krawedzi TRACK. Kazda pare kolejnych stacji rozwijamy
    # wiec najkrotsza sciezka w grafie (BFS po liczbie odcinkow), dzieki czemu
    # trasa jest w calosci przejezdna.
    _adj = collections.defaultdict(set)
    for (a, b) in seg_between:
        _adj[a].add(b)

    def sciezka(a, b):
        if a == b:
            return [a]
        prev = {a: None}
        q = collections.deque([a])
        while q:
            v = q.popleft()
            if v == b:
                out = []
                while v is not None:
                    out.append(v)
                    v = prev[v]
                return out[::-1]
            for w in _adj[v]:
                if w not in prev:
                    prev[w] = v
                    q.append(w)
        return None

    def rozwin(ids):
        """Zamienia liste stacji charakterystycznych na pelna, przejezdna trase."""
        pelna = [ids[0]]
        for i in range(len(ids) - 1):
            p = sciezka(ids[i], ids[i + 1])
            if p is None:
                return None
            pelna.extend(p[1:])
        return pelna

    routes = {r["route_id"]: r for r in read("routes.txt")}
    trips = list(read("trips.txt"))
    seq = collections.defaultdict(list)
    for r in read("stop_times.txt"):
        seq[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"],
                                  r["departure_time"]))
    for k in seq:
        seq[k].sort()

    # --- WARSTWA A: regionalne ----------------------------------------------
    warianty = collections.defaultdict(collections.Counter)
    odjazdy = collections.defaultdict(list)
    for t in trips:
        it = seq.get(t["trip_id"], [])
        if len(it) < 2:
            continue
        proj = tuple(s for _, s, _ in it if s in wybrane)
        if len(proj) < 2:
            continue
        r = routes[t["route_id"]]
        klucz = (r["route_short_name"], proj)
        warianty[r["route_short_name"]][proj] += 1
        odjazdy[klucz].append(it[0][2])

    services = []
    uzyte = set()
    uzyte_id = set()

    def unikalny(base):
        k, i = base, 1
        while k in uzyte_id:
            i += 1
            k = f"{base}_{i}"
        uzyte_id.add(k)
        return k

    for linia, war in sorted(warianty.items()):
        if "/" in linia or linia in ("NA", "POCIĄG"):
            continue
        # warianty dominujace: bierzemy do 2 najczestszych o roznych koncach
        for proj, n in war.most_common(6):
            konce = (proj[0], proj[-1])
            if konce in uzyte or tuple(reversed(konce)) in uzyte:
                continue
            if n < 20:
                continue
            # sprawdzenie przejezdnosci w grafie bazy
            ok = all((proj[i], proj[i + 1]) in seg_between
                     for i in range(len(proj) - 1))
            if not ok:
                continue
            uzyte.add(konce)
            t = TABOR["REGIONAL"]
            deps = sorted(set(odjazdy[(linia, proj)]))
            services.append({
                "id": unikalny(f"KS_{ascii3(linia)}_{ascii3(name_of[proj[0]])}_{ascii3(name_of[proj[-1]])}"),
                "name": f"{linia} {name_of[proj[0]]} – {name_of[proj[-1]]}",
                "line_code": linia,
                "operator": "Koleje Śląskie",
                "type": "REGIONAL",
                "route_station_ids": list(proj),
                "route_station_names": [name_of[x] for x in proj],
                "departures": deps[:24],
                "trips_per_period": n,
                "data_source": "gtfs_koleje_slaskie",
                "confidence": "measured",
                **{k: v for k, v in t.items() if k != "opis"},
                "rolling_stock": t["opis"],
            })

    print(f"Warstwa A (regionalne, z GTFS): {len(services)} relacji")
    for s in services:
        print(f"  {s['line_code']:5} {s['route_station_names'][0]:24} -> "
              f"{s['route_station_names'][-1]:24} "
              f"({len(s['route_station_ids'])} wezlow, {s['trips_per_period']} kursow)")

    # --- WARSTWA B: dalekobiezne (modelowane) -------------------------------
    IC_REL = [
        ("IC_SLASK",    "IC Ślązak",     ["Bielsko-Biała Gł.", "Czechowice-Dziedzice",
                                          "Tychy", "Katowice"], "Bielsko-Biała – Warszawa"),
        ("IC_ONDRASZEK","IC Ondraszek",  ["Bielsko-Biała Gł.", "Czechowice-Dziedzice",
                                          "Tychy", "Katowice", "Sosnowiec Główny"],
                                          "Bielsko-Biała – Warszawa"),
        ("IC_SILESIA",  "EC Silesia",    ["Katowice", "Tychy", "Czechowice-Dziedzice",
                                          "Chybie"], "Warszawa – Praha (przez Zebrzydowice)"),
        ("IC_SOBIESKI", "EC Sobieski",   ["Katowice", "Chorzów Batory", "Zabrze",
                                          "Gliwice"], "Warszawa – Wien"),
        ("IC_JASNOGORA","TLK Jasna Góra",["Katowice", "Sosnowiec Główny",
                                          "Dąbrowa Górnicza", "Zawiercie",
                                          "Częstochowa"], "Katowice – Częstochowa – Warszawa"),
        ("IC_ODRA",     "IC Odra",       ["Katowice", "Chorzów Batory", "Zabrze",
                                          "Gliwice"], "Kraków – Wrocław"),
    ]
    for sid, nazwa, stacje, rel in IC_REL:
        ids = [id_by_name.get(x) for x in stacje]
        if any(i is None for i in ids):
            print(f"  POMINIETO {nazwa}: brak wezla {[s for s,i in zip(stacje,ids) if i is None]}")
            continue
        ids = rozwin(ids)
        if ids is None:
            print(f"  POMINIETO {nazwa}: brak przejezdnej trasy w grafie")
            continue
        t = TABOR["IC"]
        services.append({
            "id": sid, "name": nazwa, "line_code": None,
            "operator": "PKP Intercity", "type": "IC",
            "route_station_ids": ids,
            "route_station_names": [name_of[x] for x in ids],
            "departures": [], "relacja_pelna": rel,
            "data_source": "modeled_znane_relacje",
            "confidence": "modeled",
            **{k: v for k, v in t.items() if k != "opis"},
            "rolling_stock": t["opis"],
        })

    # --- WARSTWA C: towarowe (modelowane) -----------------------------------
    TOW = [
        ("TW_WEGIEL_PLN", "Towarowy węglowy północ",
         ["Rybnik Towarowy", "Rybnik", "Leszczyny", "Gliwice"],
         "relacja kopalnie ROW – Gliwice"),
        ("TW_TRANZYT_CZ", "Towarowy tranzytowy CZ",
         ["Chałupki", "Rudyszwałd", "Racibórz", "Rybnik Towarowy"],
         "tranzyt do granicy państwa (Bohumin)"),
        ("TW_HUTA", "Towarowy hutniczy",
         ["Dąbrowa Górnicza Ząbkowice", "Dąbrowa Górnicza", "Sosnowiec Główny"],
         "obsługa zakładów hutniczych Zagłębia"),
        ("TW_MAGISTRALA", "Towarowy magistralny",
         ["Tarnowskie Góry", "Kalety", "Lubliniec"],
         "magistrala węglowa – kierunek Tczew"),
    ]
    for sid, nazwa, stacje, rel in TOW:
        ids = [id_by_name.get(x) for x in stacje]
        if any(i is None for i in ids):
            print(f"  POMINIETO {nazwa}: brak wezla {[s for s,i in zip(stacje,ids) if i is None]}")
            continue
        ids = rozwin(ids)
        if ids is None:
            print(f"  POMINIETO {nazwa}: brak przejezdnej trasy w grafie")
            continue
        t = TABOR["FREIGHT"]
        services.append({
            "id": sid, "name": nazwa, "line_code": None,
            "operator": "przewoźnik towarowy (modelowy)", "type": "FREIGHT",
            "route_station_ids": ids, "route_station_names": [name_of[x] for x in ids],
            "departures": [], "relacja_pelna": rel,
            "data_source": "modeled_korytarze_towarowe",
            "confidence": "modeled",
            **{k: v for k, v in t.items() if k != "opis"},
            "rolling_stock": t["opis"],
        })

    c = collections.Counter(s["type"] for s in services)
    print(f"\nRAZEM: {len(services)} relacji  {dict(c)}")
    cc = collections.Counter(s["confidence"] for s in services)
    print(f"Wiarygodnosc: {dict(cc)}")

    with open(os.path.join(WORK, "services.json"), "w", encoding="utf-8") as f:
        json.dump(services, f, ensure_ascii=False, indent=1)
    print("-> work/services.json")


if __name__ == "__main__":
    main()
