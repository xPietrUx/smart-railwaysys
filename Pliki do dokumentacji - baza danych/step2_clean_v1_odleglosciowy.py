#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 2 — Usuniecie krawedzi-skrotow (redukcja przechodnia z kontrola geometryczna).

PROBLEM
Feed GTFS opisuje kursy, nie infrastrukture. Pociag przyspieszony, ktory omija
przystanek B jadac z A do C, generuje w grafie krawedz (A,C) rownolegla do
sciezki A-B-C. Taka krawedz nie odpowiada zadnemu odrebnemu szlakowi — jest
artefaktem rozkladu. Nieusunieta zawyza stopnie wierzcholkow i tworzy w grafie
fikcyjne "objazdy", ktore algorytm A* moglby wykorzystac.

KRYTERIUM USUNIECIA
Krawedz (A,C) uznajemy za skrot i usuwamy, gdy istnieje wierzcholek posredni B
taki, ze:
  (1) istnieja krawedzie (A,B) i (B,C),
  (2) d(A,B) + d(B,C) <= (1 + eps) * d(A,C),
gdzie d to odleglosc ortodromiczna (wzor haversine), a eps = 0.30.

Uzasadnienie progu: jesli trasa przez B jest nie dluzsza niz 130% odleglosci
bezposredniej, to B lezy praktycznie na linii A-C, a wiec (A,C) opisuje ten sam
szlak co A-B-C. Prawdziwe rozgalezienie prowadzi w innym kierunku i daje
naloz znacznie wiekszy. Prog 30% dobrano tak, by uwzglednic luki toru — sprawdzono
wrazliwosc dla eps w {0.15, 0.20, 0.30, 0.50} (patrz raport ponizej).

Procedura jest iterowana takze dla sciezek dwuprzystankowych (A-B1-B2-C),
poniewaz pociagi pospieszne omijaja czesto kilka przystankow z rzedu.

WZOR HAVERSINE
  a = sin^2(dfi/2) + cos(fi1) * cos(fi2) * sin^2(dlambda/2)
  d = 2 * R * arcsin(sqrt(a)),  R = 6371.0088 km (promien sredni Ziemi IUGG)
"""
import json, math, os, itertools, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")
R_EARTH_KM = 6371.0088
EPS = 0.30
MAX_SKIP = 3          # maksymalna liczba pominietych przystankow


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH_KM * math.asin(math.sqrt(a))


def build_adj(edges):
    adj = collections.defaultdict(set)
    for e in edges:
        adj[e["a"]].add(e["b"])
        adj[e["b"]].add(e["a"])
    return adj


def shortest_hops(adj, src, dst, nodes, banned_edge, max_hops):
    """Najkrotsza (wg odleglosci geo) sciezka src->dst o <= max_hops krawedziach,
    nie uzywajaca krawedzi banned_edge. Zwraca (dlugosc, sciezka) albo None."""
    best = None
    # BFS/DFS ograniczony — grafy sa male, wiec wystarczy przeszukanie w glab
    stack = [(src, [src], 0.0)]
    while stack:
        cur, path, dist = stack.pop()
        if len(path) - 1 > max_hops:
            continue
        for nxt in adj[cur]:
            if tuple(sorted((cur, nxt))) == banned_edge:
                continue
            if nxt in path:
                continue
            d = dist + haversine(nodes[cur]["lat"], nodes[cur]["lon"],
                                 nodes[nxt]["lat"], nodes[nxt]["lon"])
            if nxt == dst:
                if best is None or d < best[0]:
                    best = (d, path + [nxt])
            elif len(path) <= max_hops:
                stack.append((nxt, path + [nxt], d))
    return best


def reduce_edges(nodes, edges, eps, max_skip, verbose=False):
    edges = list(edges)
    removed = []
    changed = True
    while changed:
        changed = False
        adj = build_adj(edges)
        # najdluzsze krawedzie rozpatrujemy pierwsze — to one bywaja skrotami
        order = sorted(range(len(edges)), key=lambda i: -haversine(
            nodes[edges[i]["a"]]["lat"], nodes[edges[i]["a"]]["lon"],
            nodes[edges[i]["b"]]["lat"], nodes[edges[i]["b"]]["lon"]))
        for i in order:
            e = edges[i]
            a, b = e["a"], e["b"]
            key = tuple(sorted((a, b)))
            direct = haversine(nodes[a]["lat"], nodes[a]["lon"],
                               nodes[b]["lat"], nodes[b]["lon"])
            if direct < 0.05:
                continue
            alt = shortest_hops(adj, a, b, nodes, key, max_skip + 1)
            if alt and alt[0] <= (1 + eps) * direct:
                removed.append({
                    "a": a, "b": b,
                    "a_name": nodes[a]["name"], "b_name": nodes[b]["name"],
                    "direct_km": round(direct, 3),
                    "via_km": round(alt[0], 3),
                    "ratio": round(alt[0] / direct, 3),
                    "via": [nodes[x]["name"] for x in alt[1][1:-1]],
                    "trips": e["trips"],
                })
                edges.pop(i)
                changed = True
                break
    return edges, removed


def main():
    with open(os.path.join(WORK, "graph_full.json"), encoding="utf-8") as f:
        g = json.load(f)
    nodes, edges = g["nodes"], g["edges"]

    print("=== ANALIZA WRAZLIWOSCI NA PROG eps ===")
    for eps in (0.15, 0.20, 0.30, 0.50):
        e2, rem = reduce_edges(nodes, edges, eps, MAX_SKIP)
        deg = collections.Counter()
        adj = build_adj(e2)
        for n in nodes:
            deg[len(adj[n])] += 1
        hubs = sum(v for k, v in deg.items() if k >= 3)
        print(f"  eps={eps:<5} usunieto {len(rem):3} krawedzi -> "
              f"pozostalo {len(e2):3}, wierzcholkow st>=3: {hubs}")

    edges2, removed = reduce_edges(nodes, edges, EPS, MAX_SKIP)
    adj = build_adj(edges2)
    for sid in nodes:
        nodes[sid]["degree"] = len(adj[sid])
        nodes[sid]["neighbours"] = sorted(adj[sid])

    print(f"\n=== WYNIK (eps={EPS}) ===")
    print(f"Krawedzi przed: {len(edges)}   po redukcji: {len(edges2)}   "
          f"usunieto: {len(removed)}")
    print("\nUsuniete krawedzie-skroty:")
    for r in sorted(removed, key=lambda x: -x["direct_km"]):
        via = " > ".join(r["via"])
        print(f"  {r['a_name']:28} - {r['b_name']:28} "
              f"{r['direct_km']:6.2f} km | przez: {via} ({r['ratio']:.2f}x, {r['trips']} kursow)")

    deg = collections.Counter(n["degree"] for n in nodes.values())
    print("\nRozklad stopni po redukcji:")
    for d in sorted(deg):
        print(f"  stopien {d}: {deg[d]:3}")

    with open(os.path.join(WORK, "graph_clean.json"), "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes, "edges": edges2, "removed": removed,
                   "params": {"eps": EPS, "max_skip": MAX_SKIP,
                              "R_earth_km": R_EARTH_KM}},
                  f, ensure_ascii=False, indent=1)
    print("\n-> work/graph_clean.json")


if __name__ == "__main__":
    main()
