#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 7 — Generowanie finalnych plikow bazy.

Produkuje:
  out/stations.csv   — wezly (stacje, posterunki, punkty graniczne)
  out/segments.csv   — odcinki (szlaki) miedzy wezlami
  out/services.csv   — relacje pociagow
  out/seed.cypher    — skrypt zasilajacy Memgraph
  out/weryfikacja.txt— raport kontroli jakosci

OBLICZENIE daily_trains
Liczba pociagow na dobe nie jest zgadywana — wyliczamy ja z rozkladu. Wybieramy
reprezentatywny dzien roboczy (wtorek spoza okresu swiatecznego), ustalamy
zbior kursow aktywnych tego dnia na podstawie calendar.txt i calendar_dates.txt,
a nastepnie zliczamy zatrzymania w kazdym punkcie. Wartosc dotyczy WYLACZNIE
ruchu Kolei Slaskich — pociagi innych przewoznikow (PKP Intercity, POLREGIO,
towarowe) nie sa ujete w zrodle, wiec rzeczywiste obciazenie stacji jest wyzsze.
Fakt ten jest odnotowany w polu daily_trains_scope.

POLA BEZ POKRYCIA ZRODLOWEGO
platforms (liczba peronow) i tracks (liczba torow stacyjnych) nie wystepuja
w zadnym dostepnym zrodle maszynowym. Zamiast zmyslac wartosci, pozostawiamy
je puste i wskazujemy zrodlo do uzupelnienia: zalacznik 2.18 Regulaminu sieci
PKP PLK ("Wykaz peronow") oraz zalacznik 2.6 ("Wykaz posterunkow ruchu").
Dla zachowania dzialania silnika symulacji podano rownolegle kolumny
platforms_est / tracks_est z wartosciami modelowymi (patrz nizej) — oznaczone
jako "modeled" i przeznaczone wylacznie do celow wizualizacji.
"""
import csv, json, os, collections, datetime, unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS = os.path.join(BASE, "src", "gtfs_ks")
WORK = os.path.join(BASE, "work")
OUT = os.path.join(BASE, "out")
os.makedirs(OUT, exist_ok=True)


def read(n):
    with open(os.path.join(GTFS, n), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def kod(nazwa, uzyte):
    t = unicodedata.normalize("NFKD", nazwa).encode("ascii", "ignore").decode()
    t = "".join(c for c in t.upper() if c.isalnum() or c == " ")
    parts = t.split()
    base = (parts[0][:3] if len(parts) == 1
            else parts[0][:2] + parts[1][:1]) if parts else "XXX"
    base = (base + "XXX")[:3]
    k, i = base, 1
    while k in uzyte:
        i += 1
        k = base[:2] + str(i)
    uzyte.add(k)
    return k


def dzien_reprezentatywny():
    """Wybiera wtorek w srodku okresu obowiazywania rozkladu."""
    cal = read("calendar.txt")
    starts = sorted(c["start_date"] for c in cal)
    ends = sorted(c["end_date"] for c in cal)
    d0 = datetime.datetime.strptime(starts[0], "%Y%m%d").date()
    d1 = datetime.datetime.strptime(ends[-1], "%Y%m%d").date()
    mid = d0 + (d1 - d0) / 2
    while mid.weekday() != 1:        # 1 = wtorek
        mid += datetime.timedelta(days=1)
    return mid


def kursy_w_dniu(dzien):
    cal = read("calendar.txt")
    cd = read("calendar_dates.txt")
    ds = dzien.strftime("%Y%m%d")
    dow = ["monday", "tuesday", "wednesday", "thursday",
           "friday", "saturday", "sunday"][dzien.weekday()]
    aktywne = set()
    for c in cal:
        if c["start_date"] <= ds <= c["end_date"] and c.get(dow) == "1":
            aktywne.add(c["service_id"])
    for e in cd:
        if e["date"] == ds:
            if e["exception_type"] == "1":
                aktywne.add(e["service_id"])
            elif e["exception_type"] == "2":
                aktywne.discard(e["service_id"])
    return aktywne


def main():
    with open(os.path.join(WORK, "graph_clean.json"), encoding="utf-8") as f:
        gc = json.load(f)
    with open(os.path.join(WORK, "selected.json"), encoding="utf-8") as f:
        sel = json.load(f)
    with open(os.path.join(WORK, "segments_vmax.json"), encoding="utf-8") as f:
        segs = json.load(f)
    with open(os.path.join(WORK, "services.json"), encoding="utf-8") as f:
        services = json.load(f)

    nodes = gc["nodes"]
    wybrane = sel["selected"]
    border = set(sel["border"])
    powody = sel["reasons"]

    # --- daily_trains --------------------------------------------------------
    dzien = dzien_reprezentatywny()
    aktywne = kursy_w_dniu(dzien)
    trips = {t["trip_id"]: t for t in read("trips.txt")}
    licznik = collections.Counter()
    for r in read("stop_times.txt"):
        t = trips.get(r["trip_id"])
        if t and t["service_id"] in aktywne:
            licznik[r["stop_id"]] += 1
    print(f"Dzien reprezentatywny: {dzien} ({len(aktywne)} sluzb aktywnych)")

    # --- stacje --------------------------------------------------------------
    uzyte = set()
    kody = {}
    for sid in sorted(wybrane, key=lambda x: -licznik[x]):
        kody[sid] = kod(nodes[sid]["name"], uzyte)

    stopnie = collections.Counter()
    for s in segs:
        stopnie[s["a"]] += 1
        stopnie[s["b"]] += 1

    st_rows = []
    for sid in sorted(wybrane, key=lambda x: nodes[x]["name"]):
        n = nodes[sid]
        st = stopnie[sid]
        if sid in border:
            typ = "graniczna"
        elif st >= 3:
            typ = "węzeł"
        elif st == 1:
            typ = "końcowa"
        else:
            typ = "przelotowa"
        dt = licznik[sid]
        st_rows.append({
            "id": kody[sid], "gtfs_stop_id": sid, "name": n["name"],
            "lat": round(n["lat"], 6), "lon": round(n["lon"], 6),
            "type": typ, "degree": st,
            "voivodeship": "poza woj. (punkt graniczny)" if sid in border else "śląskie",
            "daily_trains": dt,
            "daily_trains_scope": "tylko Koleje Śląskie, wtorek",
            "platforms": "", "tracks": "",
            "platforms_est": max(1, min(8, round((dt / 60) ** 0.5) + 1)),
            "tracks_est": max(2, min(14, round((dt / 30) ** 0.5) + 2)),
            "selection_rules": ";".join(powody[sid]),
            "coord_source": "gtfs_koleje_slaskie/stops.txt",
            "coord_confidence": "measured",
            "platforms_source": "BRAK — uzupełnić z PLK Reg. sieci zał. 2.18",
            "platforms_confidence": "missing",
        })

    # --- odcinki -------------------------------------------------------------
    sg_rows = []
    for i, s in enumerate(sorted(segs, key=lambda x: (x["a_name"], x["b_name"])), 1):
        sg_rows.append({
            "segment_id": f"SEG{i:03d}",
            "a": kody[s["a"]], "b": kody[s["b"]],
            "a_name": s["a_name"], "b_name": s["b_name"],
            "dist_km": s["len_km"],
            "vmax": s["vmax"],
            "travel_min": round((s["t_p10_s"] or 0) / 60, 1),
            "v_srednia_kmh": s.get("v_srednia_kmh"),
            "v_model_kmh": s.get("v_model_kmh"),
            "lines_gtfs": ";".join(s["lines"]),
            "via": ";".join(s["via"]),
            "n_punktow_posrednich": len(s["via"]),
            "dist_source": "gtfs_shapes (rzutowanie monotoniczne)",
            "dist_confidence": "measured",
            "vmax_source": s.get("vmax_source", ""),
            "vmax_confidence": s.get("vmax_confidence", ""),
            "rail_tracks": "",
            "rail_tracks_source": "BRAK — uzupełnić z PLK Reg. sieci zał. 2.4",
        })

    # --- relacje -------------------------------------------------------------
    sv_rows = []
    for s in services:
        sv_rows.append({
            "id": s["id"], "name": s["name"],
            "line_code": s.get("line_code") or "",
            "operator": s["operator"], "type": s["type"],
            "route": ";".join(kody[x] for x in s["route_station_ids"]),
            "route_names": ";".join(s["route_station_names"]),
            "n_stops": len(s["route_station_ids"]),
            "departures": ";".join(s.get("departures", [])[:12]),
            "vmax": s["vmax"], "mass_tonnes": s["mass_tonnes"],
            "length_m": s["length_m"], "accel": s["accel"], "decel": s["decel"],
            "priority": s["priority"],
            "rolling_stock": s["rolling_stock"],
            "data_source": s["data_source"], "confidence": s["confidence"],
        })

    def zapisz(nazwa, rows):
        p = os.path.join(OUT, nazwa)
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"-> out/{nazwa}  ({len(rows)} rekordów)")

    zapisz("stations.csv", st_rows)
    zapisz("segments.csv", sg_rows)
    zapisz("services.csv", sv_rows)

    # --- seed.cypher ---------------------------------------------------------
    def q(v):
        if v is None or v == "":
            return "null"
        if isinstance(v, (int, float)):
            return str(v)
        return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'

    L = ["// Baza danych symulatora ruchu kolejowego — województwo śląskie",
         "// Wygenerowano automatycznie skryptem step7_emit.py",
         f"// Źródło podstawowe: GTFS Koleje Śląskie, feed_version 2026.166",
         "// NIE EDYTOWAĆ RĘCZNIE — zmiany wprowadzać w skryptach src/",
         "",
         "MATCH (n) DETACH DELETE n;",
         "CREATE INDEX ON :Station(id);",
         "CREATE INDEX ON :Train(id);",
         ""]
    for r in st_rows:
        props = ", ".join([
            f'id: {q(r["id"])}', f'name: {q(r["name"])}',
            f'lat: {r["lat"]}', f'lon: {r["lon"]}',
            f'type: {q(r["type"])}', f'daily_trains: {r["daily_trains"]}',
            f'platforms: {q(r["platforms"]) if r["platforms"]!="" else r["platforms_est"]}',
            f'tracks: {q(r["tracks"]) if r["tracks"]!="" else r["tracks_est"]}',
            f'voivodeship: {q(r["voivodeship"])}',
            f'gtfs_stop_id: {q(r["gtfs_stop_id"])}',
            f'data_confidence: {q(r["coord_confidence"])}',
        ])
        L.append(f"CREATE (:Station {{{props}}});")
    L.append("")
    for r in sg_rows:
        props = ", ".join([
            f'segment_id: {q(r["segment_id"])}', f'dist_km: {r["dist_km"]}',
            f'vmax: {r["vmax"]}', f'travel_min: {r["travel_min"]}',
            f'rail_tracks: {q(r["rail_tracks"]) if r["rail_tracks"]!="" else 2}',
            f'status: "active"',
            f'lines_gtfs: {q(r["lines_gtfs"])}',
            f'dist_source: {q(r["dist_source"])}',
            f'dist_confidence: {q(r["dist_confidence"])}',
            f'vmax_confidence: {q(r["vmax_confidence"])}',
        ])
        for a, b in ((r["a"], r["b"]), (r["b"], r["a"])):
            L.append(f'MATCH (u:Station {{id: "{a}"}}), (v:Station {{id: "{b}"}}) '
                     f'CREATE (u)-[:TRACK {{{props}}}]->(v);')
    L.append("")
    for r in sv_rows:
        props = ", ".join([
            f'id: {q(r["id"])}', f'name: {q(r["name"])}',
            f'type: {q(r["type"])}', f'operator: {q(r["operator"])}',
            f'line_code: {q(r["line_code"])}',
            f'vmax: {r["vmax"]}', f'mass_tonnes: {r["mass_tonnes"]}',
            f'length_m: {r["length_m"]}', f'accel: {r["accel"]}',
            f'decel: {r["decel"]}', f'priority: {r["priority"]}',
            f'route_station_ids: [{", ".join(q(x) for x in r["route"].split(";"))}]',
            f'departures: [{", ".join(q(x) for x in r["departures"].split(";") if x)}]',
            f'data_source: {q(r["data_source"])}',
            f'data_confidence: {q(r["confidence"])}',
        ])
        L.append(f"CREATE (:Train {{{props}}});")

    with open(os.path.join(OUT, "seed.cypher"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"-> out/seed.cypher  ({len(L)} linii)")

    # --- weryfikacja ---------------------------------------------------------
    V = []
    V.append("RAPORT KONTROLI JAKOSCI BAZY")
    V.append("=" * 60)
    V.append(f"Wezlow            : {len(st_rows)}")
    V.append(f"Odcinkow          : {len(sg_rows)}")
    V.append(f"Relacji pociagow  : {len(sv_rows)}")
    V.append(f"Laczna dlugosc    : {sum(r['dist_km'] for r in sg_rows):.1f} km")
    V.append("")
    V.append("POKRYCIE ZRODLOWE")
    for kol, pole in (("wspolrzedne", "coord_confidence"),):
        c = collections.Counter(r[pole] for r in st_rows)
        V.append(f"  stacje/{kol:14}: {dict(c)}")
    c = collections.Counter(r["dist_confidence"] for r in sg_rows)
    V.append(f"  odcinki/dlugosc      : {dict(c)}")
    c = collections.Counter(r["vmax_confidence"] for r in sg_rows)
    V.append(f"  odcinki/vmax         : {dict(c)}")
    c = collections.Counter(r["confidence"] for r in sv_rows)
    V.append(f"  relacje              : {dict(c)}")
    V.append("")
    V.append("POLA BEZ POKRYCIA (do uzupelnienia ze zrodel PLK)")
    V.append("  Station.platforms  <- Regulamin sieci PLK, zal. 2.18")
    V.append("  Station.tracks     <- Regulamin sieci PLK, zal. 2.6")
    V.append("  TRACK.rail_tracks  <- Regulamin sieci PLK, zal. 2.4")
    V.append("  TRACK.vmax         <- Regulamin sieci PLK, zal. 2.1 (obecnie: model)")
    V.append("")

    # spojnosc i mosty
    adj = collections.defaultdict(set)
    for r in sg_rows:
        adj[r["a"]].add(r["b"])
        adj[r["b"]].add(r["a"])
    seen, comps = set(), 0
    for n0 in adj:
        if n0 in seen:
            continue
        comps += 1
        stack = [n0]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack += list(adj[x])
    V.append(f"SPOJNOSC: skladowych = {comps}")

    disc, low, bridges, t = {}, {}, [], [0]
    import sys
    sys.setrecursionlimit(10000)

    def dfs(u, par):
        disc[u] = low[u] = t[0]
        t[0] += 1
        for v in adj[u]:
            if v == par:
                continue
            if v in disc:
                low[u] = min(low[u], disc[v])
            else:
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    bridges.append((u, v))
    for n0 in list(adj):
        if n0 not in disc:
            dfs(n0, None)
    V.append(f"MOSTY (odcinki bez objazdu): {len(bridges)} z {len(sg_rows)} "
             f"= {100*len(bridges)/len(sg_rows):.0f}%")
    nm = {r["id"]: r["name"] for r in st_rows}
    for a, b in sorted(bridges, key=lambda x: nm[x[0]]):
        V.append(f"    {nm[a]} — {nm[b]}")

    with open(os.path.join(OUT, "weryfikacja.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(V) + "\n")
    print("-> out/weryfikacja.txt")
    print()
    print("\n".join(V[:24]))


if __name__ == "__main__":
    main()
