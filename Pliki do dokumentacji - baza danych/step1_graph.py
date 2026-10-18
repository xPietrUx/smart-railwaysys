#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 1 — Budowa pełnego grafu przystankowego z feedu GTFS.

Wejscie : src/gtfs_ks/*.txt  (oficjalny feed GTFS Kolei Slaskich)
Wyjscie : work/graph_full.json — graf wszystkich punktow eksploatacyjnych
          wraz ze stopniami wierzcholkow i liczba kursow na krawedziach.

Metoda:
  1. Dla kazdego kursu (trip) odczytujemy uporzadkowana sekwencje przystankow.
  2. Kazda para kolejnych przystankow (s_i, s_i+1) tworzy krawedz nieskierowana.
  3. Zliczamy liczbe kursow przez kazda krawedz (waga ruchu).
  4. Stopien wierzcholka = liczba roznych sasiadow (nie liczba kursow).

Stopien wierzcholka jest kluczowy: wierzcholki stopnia >= 3 sa wezlami
topologicznymi sieci (rozgalezienia), stopnia 1 — stacjami koncowymi,
stopnia 2 — punktami posrednimi na szlaku.
"""
import csv, json, collections, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS = os.path.join(BASE, "src", "gtfs_ks")
WORK = os.path.join(BASE, "work")
os.makedirs(WORK, exist_ok=True)


def read(name):
    with open(os.path.join(GTFS, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    stops = {r["stop_id"]: r for r in read("stops.txt")}
    trips = {r["trip_id"]: r for r in read("trips.txt")}
    routes = {r["route_id"]: r for r in read("routes.txt")}

    # sekwencje przystankow dla kazdego kursu
    seq = collections.defaultdict(list)
    for r in read("stop_times.txt"):
        seq[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"],
                                  r["arrival_time"], r["departure_time"]))
    for k in seq:
        seq[k].sort()

    edge_trips = collections.Counter()       # (a,b) -> liczba kursow
    edge_lines = collections.defaultdict(set)  # (a,b) -> {oznaczenia linii S}
    stop_stops = collections.Counter()       # przystanek -> liczba zatrzyman
    neigh = collections.defaultdict(set)

    for tid, items in seq.items():
        rid = trips[tid]["route_id"]
        line = routes[rid]["route_short_name"]
        for (_, sid, _, _) in items:
            stop_stops[sid] += 1
        for i in range(len(items) - 1):
            a, b = items[i][1], items[i + 1][1]
            if a == b:
                continue
            key = tuple(sorted((a, b)))
            edge_trips[key] += 1
            edge_lines[key].add(line)
            neigh[a].add(b)
            neigh[b].add(a)

    nodes = {}
    for sid, s in stops.items():
        if sid not in neigh and stop_stops[sid] == 0:
            continue
        nodes[sid] = {
            "stop_id": sid,
            "name": s["stop_name"],
            "lat": float(s["stop_lat"]),
            "lon": float(s["stop_lon"]),
            "degree": len(neigh[sid]),
            "stops_in_timetable": stop_stops[sid],
            "neighbours": sorted(neigh[sid]),
        }

    edges = []
    for (a, b), n in sorted(edge_trips.items(), key=lambda x: -x[1]):
        edges.append({
            "a": a, "b": b,
            "trips": n,
            "lines": sorted(edge_lines[(a, b)]),
        })

    out = {"nodes": nodes, "edges": edges}
    with open(os.path.join(WORK, "graph_full.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    deg = collections.Counter(n["degree"] for n in nodes.values())
    print(f"Wierzcholkow: {len(nodes)}   Krawedzi: {len(edges)}")
    print("\nRozklad stopni wierzcholkow:")
    for d in sorted(deg):
        print(f"  stopien {d}: {deg[d]:3} wierzcholkow")

    print("\nWierzcholki stopnia >= 3 (wezly topologiczne):")
    for n in sorted(nodes.values(), key=lambda x: (-x["degree"], x["name"])):
        if n["degree"] >= 3:
            print(f"  {n['name']:34} st={n['degree']}  zatrzyman={n['stops_in_timetable']}")

    print("\nWierzcholki stopnia 1 (stacje koncowe):")
    for n in sorted(nodes.values(), key=lambda x: x["name"]):
        if n["degree"] == 1:
            print(f"  {n['name']:34} zatrzyman={n['stops_in_timetable']}")


if __name__ == "__main__":
    main()
