#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 4 — Klasyfikacja administracyjna, selekcja wezlow i kontrakcja grafu.

CEL
Pelny graf ma 239 punktow, z czego ponad 200 to przystanki osobowe lezace
w ciagu szlaku (stopien 2). Dla symulatora ruchu istotne sa punkty, w ktorych
ruch moze byc kierowany lub konczony — a wiec rozgalezienia i stacje. Przystanek
osobowy w srodku szlaku nie zmienia topologii: pociag i tak musi przejechac caly
szlak. Utrzymywanie go jako osobnego wierzcholka zwieksza rozmiar grafu bez
zwiekszenia zdolnosci modelowania.

REGULY SELEKCJI (wierzcholek wchodzi do bazy, gdy spelnia co najmniej jedna)
  R1  stopien >= 3            — posterunek odgalezny / wezel sieci
  R2  stopien == 1            — stacja koncowa lub punkt styku z sasiednia siecia
  R3  konczy bieg >= T kursow — stacja zwrotna

DROGA DOJSCIA DO REGULY R3 (dwie odrzucone wersje)
Wersja 1 — liczba zatrzyman w rozkladzie. Odrzucona: na gesto obsluzonej linii
podmiejskiej KAZDY przystanek ma wysoka liczbe zatrzyman, wiec regula wciagala
do bazy wszystkie przystanki w Tychach (po 2278 zatrzyman) mimo ze zaden nie
jest stacja. Miara opisuje czestotliwosc kursowania linii, nie range punktu.

Wersja 2 — liczba roznych linii (oznaczen S) obslugujacych punkt. Odrzucona
z tego samego powodu w innej postaci: odnoga do Wisly obsluzona jest czterema
relacjami (S6, S62, S76, S77), wiec kazdy z dziewieciu przystankow tej odnogi
mial 4 linie i wchodzil do bazy, podczas gdy Zabrze — miasto 155 tys.
mieszkancow — mialo 1 linie.

Wersja przyjeta — liczba kursow KONCZACYCH BIEG w punkcie. Uzasadnienie
ruchowe: pociag moze zakonczyc bieg i zmienic kierunek jazdy wylacznie tam,
gdzie uklad torowy na to pozwala, a wiec na stacji, nie na przystanku osobowym.
Miara jest niezalezna od czestotliwosci na szlaku i wprost odpowiada
zdolnosci technicznej punktu. Prog T odsiewa pojedyncze kursy awaryjne.
  R4  punkt graniczny         — pierwszy punkt poza woj. slaskim na danym ciagu,
                                potrzebny jako punkt koncowy pociagow tranzytowych
  R5  miasto na prawach powiatu — istotnosc administracyjna; gwarantuje obecnosc
                                miast takich jak Zabrze czy Ruda Slaska, ktore
                                leza w ciagu szlaku (stopien 2), ale sa
                                najwiekszymi osrodkami w regionie

ZASIEG GEOGRAFICZNY
Baza obejmuje wojewodztwo slaskie. Punkty poza nim sa odrzucane, z wyjatkiem
punktow granicznych (R4), oznaczonych typem "graniczna" — potrzebnych, by
pociagi tranzytowe (do Krakowa, Warszawy, Ostrawy) mialy dokad jechac.

KONTRAKCJA
Po wybraniu zbioru S wierzcholkow graf jest redukowany: kazda maksymalna sciezka
v0 - u1 - u2 - ... - uk - v1, w ktorej v0,v1 nalezą do S, a wszystkie ui nie
naleza do S i maja stopien 2, zostaje zastapiona pojedyncza krawedzia (v0,v1)
o dlugosci rownej sumie dlugosci krawedzi skladowych. Punkty posrednie sa
zachowane w polu "via" — nie zniekaja modelu, a pozwalaja odtworzyc przebieg.

Operacja zachowuje dlugosci: suma dlugosci krawedzi grafu zredukowanego jest
rowna sumie dlugosci krawedzi grafu pelnego (z dokladnoscia do krawedzi
odrzuconych wraz z odcietymi galeziami poza wojewodztwem).
"""
import json, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")

# --- Punkty poza woj. slaskim -------------------------------------------------
# Klasyfikacja recznana na podstawie podzialu administracyjnego RP (TERYT).
POZA_SLASKIM = {
    # malopolskie
    "Oświęcim", "Trzebinia", "Balin", "Dulowa", "Wola Filipowska", "Krzeszowice",
    "Pisary", "Rudawa", "Zabierzów", "Zabierzów Rząska", "Kraków Mydlniki",
    "Kraków Mydlniki Wapiennik", "Kraków Bronowice", "Kraków Łobzów",
    "Kraków Główny", "Kraków Grzegórzki", "Kraków Zabłocie", "Kraków Płaszów",
    "Andrychów", "Kęty", "Wadowice", "Kalwaria Zebrzydowska Lanckorona",
    "Sucha Beskidzka Zamek", "Maków Podhalański", "Jordanów", "Chabówka Stadion",
    "Nowy Targ", "Biały Dunajec", "Poronin", "Zakopane",
    # lodzkie
    "Działoszyn", "Chorzew Siemkowice",
    # zagranica
    "Bohumin", "Skalite", "Skalite Kudlov", "Skalite Pod Pol.", "Skalite Serafinov",
}

# --- Miasta na prawach powiatu w woj. slaskim (stacje reprezentujace) ---------
MIASTA_NA_PRAWACH_POWIATU = {
    "Katowice", "Bielsko-Biała Gł.", "Bytom", "Chorzów Batory", "Częstochowa",
    "Dąbrowa Górnicza", "Gliwice", "Jaworzno Szczakowa", "Mysłowice",
    "Ruda Śląska", "Rybnik", "Sosnowiec Główny", "Świętochłowice", "Tychy",
    "Zabrze", "Żory",
}

PROG_KONCOWYCH = 5   # parametr T reguly R3: min. liczba kursow konczacych bieg


def main():
    with open(os.path.join(WORK, "graph_clean.json"), encoding="utf-8") as f:
        g = json.load(f)
    nodes = g["nodes"]
    with open(os.path.join(WORK, "edges_measured.json"), encoding="utf-8") as f:
        measured = json.load(f)

    elen = {tuple(sorted((e["a"], e["b"]))): e for e in measured}
    adj = collections.defaultdict(set)
    linie_w_punkcie = collections.defaultdict(set)
    for e in measured:
        adj[e["a"]].add(e["b"])
        adj[e["b"]].add(e["a"])
        real = {l for l in e["lines"] if l.startswith("S") and "/" not in l}
        linie_w_punkcie[e["a"]] |= real
        linie_w_punkcie[e["b"]] |= real

    # liczba kursow konczacych bieg w punkcie (z GTFS)
    import csv as _csv
    _gt = os.path.join(BASE, "src", "gtfs_ks")
    _seq = collections.defaultdict(list)
    with open(os.path.join(_gt, "stop_times.txt"), encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            _seq[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"]))
    koncowe = collections.Counter()
    for k, v in _seq.items():
        v.sort()
        koncowe[v[0][1]] += 1
        koncowe[v[-1][1]] += 1

    for sid, n in nodes.items():
        n["n_linii"] = len(linie_w_punkcie[sid])
        n["linie"] = sorted(linie_w_punkcie[sid])
        n["kursy_koncowe"] = koncowe[sid]

    # --- klasyfikacja administracyjna ---------------------------------------
    for sid, n in nodes.items():
        n["w_slaskim"] = n["name"] not in POZA_SLASKIM

    # punkty graniczne: poza woj. slaskim, ale sasiadujace z punktem w woj.
    graniczne = set()
    for sid, n in nodes.items():
        if not n["w_slaskim"]:
            if any(nodes[x]["w_slaskim"] for x in adj[sid]):
                graniczne.add(sid)

    # --- selekcja ------------------------------------------------------------
    wybrane, powody = set(), {}
    for sid, n in nodes.items():
        r = []
        if not n["w_slaskim"]:
            if sid in graniczne:
                r.append("R4_graniczna")
        else:
            if n["degree"] >= 3:
                r.append("R1_wezel")
            if n["degree"] == 1:
                r.append("R2_koncowa")
            if n["kursy_koncowe"] >= PROG_KONCOWYCH:
                r.append("R3_zwrotna")
            if n["name"] in MIASTA_NA_PRAWACH_POWIATU:
                r.append("R5_miasto")
        if r:
            wybrane.add(sid)
            powody[sid] = r

    print(f"Punktow ogolem: {len(nodes)}")
    print(f"  w woj. slaskim      : {sum(1 for n in nodes.values() if n['w_slaskim'])}")
    print(f"  poza woj. slaskim   : {sum(1 for n in nodes.values() if not n['w_slaskim'])}")
    print(f"  w tym granicznych   : {len(graniczne)}")
    print(f"\nWybranych wierzcholkow: {len(wybrane)}  (prog R3 = {PROG_KONCOWYCH} kursow konczacych)")
    cnt = collections.Counter(x for v in powody.values() for x in v)
    for k, v in sorted(cnt.items()):
        print(f"    {k:14} {v}")

    # --- kontrakcja ----------------------------------------------------------
    segments, seen = [], set()
    for s in wybrane:
        for first in adj[s]:
            path = [s, first]
            prev, cur = s, first
            while cur not in wybrane and len(adj[cur]) == 2:
                nxt = next(x for x in adj[cur] if x != prev)
                prev, cur = cur, nxt
                path.append(cur)
            if cur not in wybrane:
                continue          # sciezka wygasa poza zbiorem (odcieta galaz)
            key = (tuple(sorted((path[0], path[-1]))), tuple(sorted(path[1:-1])))
            if key in seen:
                continue
            seen.add(key)
            L, tp10, tmed, trips, lines = 0.0, 0, 0, [], set()
            ok = True
            for i in range(len(path) - 1):
                e = elen.get(tuple(sorted((path[i], path[i + 1]))))
                if not e:
                    ok = False
                    break
                L += e["len_km"]
                tp10 += e["t_p10_s"] or 0
                tmed += e["t_median_s"] or 0
                trips.append(e["trips"])
                lines |= set(e["lines"])
            if not ok:
                continue
            segments.append({
                "a": path[0], "b": path[-1],
                "a_name": nodes[path[0]]["name"], "b_name": nodes[path[-1]]["name"],
                "via": [nodes[x]["name"] for x in path[1:-1]],
                "via_ids": path[1:-1],
                "len_km": round(L, 3),
                "t_p10_s": tp10, "t_median_s": tmed,
                "trips": min(trips) if trips else 0,
                "lines": sorted(lines),
                "hops": len(path) - 1,
            })

    print(f"\nOdcinkow po kontrakcji: {len(segments)}")
    tot_full = sum(e["len_km"] for e in measured)
    tot_red = sum(s["len_km"] for s in segments)
    print(f"Dlugosc grafu pelnego     : {tot_full:8.1f} km")
    print(f"Dlugosc grafu zredukowanego: {tot_red:8.1f} km "
          f"(roznica = galezie odciete poza woj.: {tot_full-tot_red:.1f} km)")

    # spojnosc
    a2 = collections.defaultdict(set)
    for s in segments:
        a2[s["a"]].add(s["b"])
        a2[s["b"]].add(s["a"])
    seen2, comps = set(), []
    for n0 in wybrane:
        if n0 in seen2:
            continue
        stack, comp = [n0], []
        while stack:
            x = stack.pop()
            if x in seen2:
                continue
            seen2.add(x)
            comp.append(x)
            stack += list(a2[x])
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    print(f"\nSkladowe spojne: {len(comps)} "
          f"(rozmiary: {[len(c) for c in comps[:6]]})")
    for c in comps[1:]:
        print("   odizolowane:", ", ".join(nodes[x]["name"] for x in c))

    out = {"selected": sorted(wybrane), "reasons": powody,
           "border": sorted(graniczne), "segments": segments,
           "params": {"prog_koncowych": PROG_KONCOWYCH}}
    with open(os.path.join(WORK, "selected.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("\n=== WYBRANE WIERZCHOLKI ===")
    for sid in sorted(wybrane, key=lambda x: -nodes[x]["stops_in_timetable"]):
        n = nodes[sid]
        print(f"  {n['name']:32} st={n['degree']} konc={n.get('kursy_koncowe',0):5} "
              f"zatrz={n['stops_in_timetable']:5} [{','.join(powody[sid])}]")
    print("\n-> work/selected.json")


if __name__ == "__main__":
    main()
