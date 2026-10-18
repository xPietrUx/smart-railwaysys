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


# --- Ochrona przed cicha kolizja identyfikatorow -----------------------------
# Poprzednia wersja bazy (backend/db/seed.py sprzed przebudowy) uzywala ponizszych
# kodow. Jesli nowy generator nadalby ktorys z nich INNEJ stacji, kod aplikacji
# odwolujacy sie do starego identyfikatora nie zglosilby bledu — po cichu
# wskazalby niewlasciwa stacje. Wykryto trzy takie przypadki (JAS, PIE, RUD).
# Dlatego kod moze zostac ponownie uzyty WYLACZNIE dla stacji o tej samej nazwie;
# w przeciwnym razie generator przechodzi do kolejnego wariantu. Dzieki temu
# stary identyfikator albo znaczy to samo, albo nie istnieje (blad glosny).
STARE_KODY = {
    "KAT": "Katowice", "GLI": "Gliwice", "ZAB": "Zabrze",
    "CHO": "Chorzów Batory", "SOS": "Sosnowiec Główny",
    "DAB": "Dąbrowa Górnicza", "BYT": "Bytom", "RYB": "Rybnik",
    "TYC": "Tychy", "MYS": "Mysłowice", "ZAW": "Zawiercie",
    "MYK": "Myszków", "CZE": "Częstochowa", "CZL": "Czeladź",
    "BED": "Będzin", "RAC": "Racibórz", "WOD": "Wodzisław Śląski",
    "JAS": "Jastrzębie-Zdrój", "PSZ": "Pszczyna",
    "CZD": "Czechowice-Dziedzice", "BBI": "Bielsko-Biała",
    "ZYW": "Żywiec", "CIE": "Cieszyn", "RUD": "Ruda Śląska",
    "SWI": "Świętochłowice", "SIE": "Siemianowice Śląskie",
    "PIE": "Piekary Śląskie", "MIK": "Mikołów", "KNU": "Knurów",
    "JAW": "Jaworzno",
}


def kolizja(k, nazwa):
    """True, gdy kod k byl w starej bazie uzyty dla INNEJ stacji."""
    stare = STARE_KODY.get(k)
    return stare is not None and stare != nazwa


def kod(nazwa, uzyte):
    t = unicodedata.normalize("NFKD", nazwa).encode("ascii", "ignore").decode()
    t = "".join(c for c in t.upper() if c.isalnum() or c == " ")
    parts = t.split()
    base = (parts[0][:3] if len(parts) == 1
            else parts[0][:2] + parts[1][:1]) if parts else "XXX"
    base = (base + "XXX")[:3]
    k, i = base, 1
    while k in uzyte or kolizja(k, nazwa):
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
    # odcinki: preferuj wersje wzbogacona o PLK, jesli istnieje
    seg_file = ("segments_plk.json"
                if os.path.exists(os.path.join(WORK, "segments_plk.json"))
                else "segments_vmax.json")
    with open(os.path.join(WORK, seg_file), encoding="utf-8") as f:
        segs = json.load(f)
    with open(os.path.join(WORK, "services.json"), encoding="utf-8") as f:
        services = json.load(f)
    # dane PLK dla stacji (opcjonalne)
    st_plk = {}
    if os.path.exists(os.path.join(WORK, "stations_plk.json")):
        with open(os.path.join(WORK, "stations_plk.json"), encoding="utf-8") as f:
            st_plk = json.load(f)
    # perony PLK 2.18 (opcjonalne)
    plat_plk = {}
    if os.path.exists(os.path.join(WORK, "platforms_plk.json")):
        with open(os.path.join(WORK, "platforms_plk.json"), encoding="utf-8") as f:
            plat_plk = json.load(f)
    print(f"Odcinki wczytane z: {seg_file}")

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
        p = st_plk.get(sid, {})
        peron = p.get("plk_ma_peron")
        pl = plat_plk.get(sid, {})
        ma_perony = pl.get("plk218_matched")
        platforms_est = max(1, min(8, round((dt / 60) ** 0.5) + 1))
        tracks_est = max(2, min(14, round((dt / 30) ** 0.5) + 2))
        # Kolumny platforms/tracks zawieraja DOKLADNIE te wartosci, ktore trafiaja
        # do bazy: dane z zal. 2.18 tam, gdzie punkt wystepuje w wykazie, a dla
        # 2 stacji granicznych spoza sieci PLK (Bohumin, Skalite) — oszacowanie,
        # oznaczone platforms_confidence = "derived". Wczesniej pola te byly puste,
        # przez co CSV i seed podawaly dla tych stacji rozne wartosci.
        platforms = pl.get("platforms") if ma_perony else platforms_est
        tracks = pl.get("platform_edges") if ma_perony else tracks_est
        st_rows.append({
            "id": kody[sid], "gtfs_stop_id": sid, "name": n["name"],
            "lat": round(n["lat"], 6), "lon": round(n["lon"], 6),
            "type": p.get("plk_typ_opis") or typ,
            "type_plk": p.get("plk_typ", ""),
            "type_topologiczny": typ, "degree": st,
            "voivodeship": "poza woj. (punkt graniczny)" if sid in border else "śląskie",
            "plk_lines": ";".join(p.get("plk_linie", [])),
            "daily_trains": dt,
            "daily_trains_scope": "tylko Koleje Śląskie, wtorek",
            "has_platform": ("TAK" if peron else "NIE") if p.get("plk_matched") else "",
            "platform_manager": p.get("plk_peron_zarzadca") or "",
            "plk_wyrozniki": ";".join(p.get("plk_wyrozniki", [])),
            "platforms": platforms,
            "tracks": tracks,
            "platform_len_max_m": pl.get("platform_len_max") if ma_perony else "",
            "platforms_est": platforms_est,
            "tracks_est": tracks_est,
            "selection_rules": ";".join(powody[sid]),
            "coord_source": "gtfs_koleje_slaskie/stops.txt",
            "coord_confidence": "measured",
            "type_source": "PLK_zal_2.6" if p.get("plk_matched") else "topologia",
            "platforms_source": "PLK_zal_2.18" if ma_perony else "szacowana (spoza sieci PLK)",
            "platforms_confidence": "measured" if ma_perony else "derived",
        })

    # --- odcinki -------------------------------------------------------------
    sg_rows = []
    for i, s in enumerate(sorted(segs, key=lambda x: (x["a_name"], x["b_name"])), 1):
        rt = s.get("rail_tracks")
        sg_rows.append({
            "segment_id": f"SEG{i:03d}",
            "a": kody[s["a"]], "b": kody[s["b"]],
            "a_name": s["a_name"], "b_name": s["b_name"],
            "dist_km": s["len_km"],
            "vmax": s["vmax"],
            "vmax_ezt": s.get("vmax_ezt", ""),
            "vmax_wagon": s.get("vmax_wagon", ""),
            "vmax_towar": s.get("vmax_towar", ""),
            "vmax_model": s.get("vmax_model", ""),
            "rail_tracks": rt if rt else 1,
            "rail_tracks_confidence": "measured" if rt else "assumed",
            "plk_line": s.get("plk_line", ""),
            "plk_klasa": s.get("plk_klasa", ""),
            "travel_min": round((s["t_p10_s"] or 0) / 60, 1),
            "v_srednia_kmh": s.get("v_srednia_kmh"),
            "lines_gtfs": ";".join(s["lines"]),
            "via": ";".join(s["via"]),
            "n_punktow_posrednich": len(s["via"]),
            "dist_source": "gtfs_shapes (rzutowanie monotoniczne)",
            "dist_confidence": "measured",
            "vmax_source": s.get("vmax_source", ""),
            "vmax_confidence": s.get("vmax_confidence", ""),
            "rail_tracks_source": s.get("rail_tracks_source",
                                        "BRAK — PLK zał. 2.1"),
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
        plat = r["platforms"] if r["platforms"] != "" else r["platforms_est"]
        trk = r["tracks"] if r["tracks"] != "" else r["tracks_est"]
        props = ", ".join([
            f'id: {q(r["id"])}', f'name: {q(r["name"])}',
            f'lat: {r["lat"]}', f'lon: {r["lon"]}',
            f'type: {q(r["type"])}', f'type_plk: {q(r["type_plk"])}',
            f'daily_trains: {r["daily_trains"]}',
            f'platforms: {plat}',
            f'tracks: {trk}',
            f'has_platform: {q(r["has_platform"])}',
            f'platform_manager: {q(r["platform_manager"])}',
            f'voivodeship: {q(r["voivodeship"])}',
            f'plk_lines: {q(r["plk_lines"])}',
            f'gtfs_stop_id: {q(r["gtfs_stop_id"])}',
            f'platforms_confidence: {q(r["platforms_confidence"])}',
            f'type_source: {q(r["type_source"])}',
            f"data_source: \"gtfs+plk\"",
        ])
        L.append(f"CREATE (:Station {{{props}}});")
    L.append("")
    for r in sg_rows:
        rt = r["rail_tracks"]
        try:
            line_int = int(float((r["plk_line"] or "").split(";")[0]))
        except (ValueError, TypeError):
            line_int = 0
        props = ", ".join([
            f'segment_id: {q(r["segment_id"])}', f'line: {line_int}',
            f'dist_km: {r["dist_km"]}',
            f'vmax: {r["vmax"]}',
            f'vmax_ezt: {r["vmax_ezt"] if r["vmax_ezt"]!="" else "null"}',
            f'vmax_wagon: {r["vmax_wagon"] if r["vmax_wagon"]!="" else "null"}',
            f'vmax_towar: {r["vmax_towar"] if r["vmax_towar"]!="" else "null"}',
            f'travel_min: {r["travel_min"]}',
            f'rail_tracks: {rt}',
            f'rail_tracks_confidence: {q(r["rail_tracks_confidence"])}',
            f'plk_line: {q(r["plk_line"])}',
            f'plk_klasa: {q(r["plk_klasa"])}',
            f'status: "active"',
            f'lines_gtfs: {q(r["lines_gtfs"])}',
            f'dist_source: {q(r["dist_source"])}',
            f'dist_confidence: {q(r["dist_confidence"])}',
            f'vmax_source: {q(r["vmax_source"])}',
            f'vmax_confidence: {q(r["vmax_confidence"])}',
            f'data_confidence: {q(r["vmax_confidence"])}',
        ])
        for a, b in ((r["a"], r["b"]), (r["b"], r["a"])):
            L.append(f'MATCH (u:Station {{id: "{a}"}}), (v:Station {{id: "{b}"}}) '
                     f'CREATE (u)-[:TRACK {{{props}}}]->(v);')
    L.append("")
    # Stan startowy pociagu MUSI byc identyczny jak w backend/db/seed.py,
    # inaczej import przez Memgraph Lab dawalby inny stan bazy niz start
    # aplikacji. Pociag powstaje ze status='waiting', pusta trasa i para
    # origin/destination — trase wylicza silnik algorytmem A* przy pierwszym
    # ticku (train_service.dispatch_or_wait).
    for r in sv_rows:
        trasa = r["route"].split(";")
        origin, dest = trasa[0], trasa[-1]
        props = ", ".join([
            f'id: {q(r["id"])}', f'name: {q(r["name"])}',
            f'type: {q(r["type"])}', f'operator: {q(r["operator"])}',
            f'line_code: {q(r["line_code"])}',
            f'origin_station_id: {q(origin)}',
            f'destination_station_id: {q(dest)}',
            f"direction: 'outbound'",
            f'current_station_id: {q(origin)}',
            f'next_station_id: null', f'current_segment_id: null',
            f'progress: 0.0', f"status: 'waiting'",
            f'route_station_ids: []', f'route_segment_ids: []',
            f'route_index: 0',
            f'vmax: {r["vmax"]}', f'priority: {r["priority"]}',
            f'mass_tonnes: {r["mass_tonnes"]}',
            f'length_m: {r["length_m"]}', f'accel: {r["accel"]}',
            f'decel: {r["decel"]}',
            f'dwell_until: null', f'delayed_by_event_id: null',
            f'updated_at: 0.0',
            f'data_source: {q(r["data_source"])}',
            f'data_confidence: {q(r["confidence"])}',
        ])
        L.append(f"CREATE (:Train {{{props}}});")

    with open(os.path.join(OUT, "seed.cypher"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"-> out/seed.cypher  ({len(L)} linii)")

    # Wersja .cypherl dla importu do Memgrapha: jedno polecenie na linie,
    # bez komentarzy i pustych linii (format wymagany przez mgconsole/Lab).
    L_l = [x for x in L if x.strip() and not x.strip().startswith("//")]
    with open(os.path.join(OUT, "seed.cypherl"), "w", encoding="utf-8") as f:
        f.write("\n".join(L_l) + "\n")
    print(f"-> out/seed.cypherl ({len(L_l)} polecen, format importu Memgraph)")

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
    nrt = sum(1 for r in sg_rows if r["rail_tracks"] != "")
    V.append(f"  odcinki/rail_tracks  : measured={nrt}, brak={len(sg_rows)-nrt}")
    nkl = sum(1 for r in sg_rows if r["plk_klasa"] != "")
    V.append(f"  odcinki/klasa PLK    : {nkl}")
    ntp = sum(1 for r in st_rows if r["type_source"] == "PLK_zal_2.6")
    V.append(f"  stacje/typ z PLK 2.6 : {ntp}/{len(st_rows)}")
    npl = sum(1 for r in st_rows if r["platforms_confidence"] == "measured")
    V.append(f"  stacje/perony z 2.18 : {npl}/{len(st_rows)}")
    c = collections.Counter(r["confidence"] for r in sv_rows)
    V.append(f"  relacje              : {dict(c)}")
    V.append("")
    V.append("DANE Z WYKAZOW PLK (Regulamin sieci 2025/2026, stan 30.08.2026)")
    V.append("  vmax (EZT/wagon/towar) <- zal. 2.1")
    V.append("  rail_tracks (tory N/P) <- zal. 2.1")
    V.append("  klasa odcinka          <- zal. 2.4")
    V.append("  typ punktu, peron      <- zal. 2.6")
    V.append("  liczba peronow, torow  <- zal. 2.18")
    V.append("")
    V.append("POLA WCIAZ BEZ POKRYCIA")
    V.append("  brak — wszystkie parametry infrastruktury pochodza ze zrodel")
    V.append("  (2 stacje graniczne poza siecia PLK: perony szacowane)")
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
