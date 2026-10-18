#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 2 — Usuniecie krawedzi-skrotow metoda geometrii toru.

PROBLEM
Feed GTFS opisuje kursy, nie infrastrukture. Pociag przyspieszony jadacy z A do C
bez zatrzymania w B generuje krawedz (A,C) rownolegla do sciezki A-B-C. Taka
krawedz nie odpowiada odrebnemu szlakowi — jest artefaktem rozkladu.

DLACZEGO NIE WYSTARCZY KRYTERIUM ODLEGLOSCIOWE
Pierwsze podejscie (step2_clean_v1_odleglosciowy.py) usuwalo (A,C), gdy
d(A,B)+d(B,C) <= 1.3*d(A,C). Kryterium to jest jednak nieodroznialne od sytuacji,
w ktorej miedzy A i C biegna DWIE ROZNE linie o zblizonej dlugosci — a w wezle
slaskim to przypadek czesty (np. Bytom – Chorzow Batory: bezposrednio linia 131
albo przez Chorzow Miasto). Kryterium odleglosciowe kasowaloby wtedy prawdziwy
objazd, czyli niszczylo dokladnie te wlasnosc sieci, ktora ma badac symulator.

KRYTERIUM WLASCIWE — PRZYNALEZNOSC DO PRZEBIEGU TORU
Feed zawiera shapes.txt: rzeczywista geometrie przejazdu kazdego kursu. Jesli
pociag jadacy z A do C fizycznie mija posterunek B, to B lezy na tej geometrii.
Jesli natomiast jedzie inna linia, geometria omija B szerokim lukiem.

Krawedz (A,C) usuwamy zatem wtedy i tylko wtedy, gdy istnieje wierzcholek B
grafu taki, ze odleglosc B od lamanej opisujacej przejazd A->C nie przekracza
TOL = 250 m. Wowczas (A,C) i A-B-C opisuja ten sam tor.

Prog 250 m dobrano jako kompromis: perony stacji leza w promieniu ok. 100-200 m
od osi toru, a rownolegle linie w wezle slaskim sa oddalone o co najmniej 400 m.
Analize wrazliwosci dla TOL w {100, 150, 250, 400, 600} m zamieszczono w raporcie.

ODLEGLOSC PUNKTU OD ODCINKA
Wspolrzedne rzutowane lokalnie (odwzorowanie rownopromienne):
  x = R * (lambda - lambda0) * cos(fi0),   y = R * (fi - fi0)
Dla odcinka PQ i punktu S:
  t = clamp( ((S-P) . (Q-P)) / |Q-P|^2 , 0, 1 )
  d = | S - (P + t*(Q-P)) |
Blad odwzorowania dla obszaru ok. 200 km jest rzedu pojedynczych metrow, czyli
pomijalny wobec progu 250 m.
"""
import csv, json, math, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS = os.path.join(BASE, "src", "gtfs_ks")
WORK = os.path.join(BASE, "work")
R_EARTH_M = 6371008.8
TOL_M = 250.0
LAT0, LON0 = 50.0, 19.0     # srodek odwzorowania (wojewodztwo slaskie)


def read(name):
    with open(os.path.join(GTFS, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_xy(lat, lon):
    x = R_EARTH_M * math.radians(lon - LON0) * math.cos(math.radians(LAT0))
    y = R_EARTH_M * math.radians(lat - LAT0)
    return x, y


def pt_seg_dist(sx, sy, px, py, qx, qy):
    dx, dy = qx - px, qy - py
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(sx - px, sy - py)
    t = ((sx - px) * dx + (sy - py) * dy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(sx - (px + t * dx), sy - (py + t * dy))


def main():
    with open(os.path.join(WORK, "graph_full.json"), encoding="utf-8") as f:
        g = json.load(f)
    nodes = g["nodes"]

    trips = {r["trip_id"]: r for r in read("trips.txt")}

    shapes = collections.defaultdict(list)
    for r in read("shapes.txt"):
        shapes[r["shape_id"]].append(
            (int(r["shape_pt_sequence"]), float(r["shape_pt_lat"]),
             float(r["shape_pt_lon"]), float(r["shape_dist_traveled"])))
    for k in shapes:
        shapes[k].sort()
    shape_xy = {k: [(to_xy(la, lo), d) for _, la, lo, d in v]
                for k, v in shapes.items()}

    seq = collections.defaultdict(list)
    for r in read("stop_times.txt"):
        seq[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"]))
    for k in seq:
        seq[k].sort()

    node_xy = {sid: to_xy(n["lat"], n["lon"]) for sid, n in nodes.items()}

    def proj_idx(sid_xy, pts):
        sx, sy = sid_xy
        best, bi = 1e18, 0
        for i, ((x, y), _) in enumerate(pts):
            d = (x - sx) ** 2 + (y - sy) ** 2
            if d < best:
                best, bi = d, i
        return bi

    # dla kazdej krawedzi zbieramy do 3 przykladowych wycinkow lamanej
    edge_polys = collections.defaultdict(list)
    for tid, items in seq.items():
        sh = trips[tid].get("shape_id")
        if not sh or sh not in shape_xy:
            continue
        pts = shape_xy[sh]
        idxs = [proj_idx(node_xy[s], pts) if s in node_xy else None
                for _, s in items]
        for i in range(len(items) - 1):
            a, b = items[i][1], items[i + 1][1]
            if a == b or idxs[i] is None or idxs[i + 1] is None:
                continue
            key = tuple(sorted((a, b)))
            if len(edge_polys[key]) >= 3:
                continue
            lo, hi = sorted((idxs[i], idxs[i + 1]))
            if hi - lo >= 1:
                edge_polys[key].append([p for p, _ in pts[lo:hi + 1]])

    cache = {}

    def skipped_nodes(key, tol):
        ck = (key, tol)
        if ck in cache:
            return cache[ck]
        a, b = key
        found = set()
        for poly in edge_polys.get(key, []):
            if len(poly) < 2:
                continue
            for sid, (sx, sy) in node_xy.items():
                if sid in (a, b) or sid in found:
                    continue
                m = 1e18
                for j in range(len(poly) - 1):
                    d = pt_seg_dist(sx, sy, poly[j][0], poly[j][1],
                                    poly[j + 1][0], poly[j + 1][1])
                    if d < m:
                        m = d
                        if m <= tol:
                            break
                if m <= tol:
                    found.add(sid)
        cache[ck] = found
        return found

    print("=== ANALIZA WRAZLIWOSCI NA PROG TOL ===")
    for tol in (100, 150, 250, 400, 600):
        cnt = sum(1 for e in g["edges"]
                  if skipped_nodes(tuple(sorted((e["a"], e["b"]))), tol))
        print(f"  TOL={tol:4} m -> krawedzi uznanych za skroty: {cnt:3} "
              f"(z {len(g['edges'])})")

    # ---- USUWANIE ZE STRAZNIKIEM SPOJNOSCI ------------------------------
    # Krawedz-skrot wolno usunac tylko wtedy, gdy trasa, ktora ona skraca,
    # nadal istnieje w grafie. Inaczej usuniecie skrotu odcina przystanek
    # od sieci: jesli czesc pociagow omija przystanek P, a krawedzie
    # dochodzace do P zostaly wczesniej uznane za skroty innych relacji,
    # P zostaje wierzcholkiem izolowanym. Obserwowano to dla przystankow
    # Ustron Brzegi i Wisla Glebce.
    #
    # Dlatego usuwanie prowadzimy iteracyjnie: kandydatow rozpatrujemy
    # od skrotow pomijajacych najwiecej punktow, a przed kazdym usunieciem
    # sprawdzamy, czy po nim konce krawedzi pozostana polaczone sciezka
    # przechodzaca przez pomijane punkty.
    cand = []
    for e in g["edges"]:
        key = tuple(sorted((e["a"], e["b"])))
        sk = skipped_nodes(key, TOL_M)
        if sk:
            cand.append((len(sk), key, e, sk))
    cand.sort(key=lambda x: -x[0])

    cur = {tuple(sorted((e["a"], e["b"]))): e for e in g["edges"]}

    def connected(src, dst, edges_map, banned):
        a = collections.defaultdict(set)
        for (x, y) in edges_map:
            if (x, y) == banned:
                continue
            a[x].add(y)
            a[y].add(x)
        seen, stack = {src}, [src]
        while stack:
            v = stack.pop()
            if v == dst:
                return True
            for w in a[v]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        return dst in seen

    removed, blocked = [], []
    for _, key, e, sk in cand:
        if connected(key[0], key[1], cur, key):
            del cur[key]
            removed.append({**e, "skipped": sorted(sk),
                            "skipped_names": [nodes[s]["name"] for s in sorted(sk)]})
        else:
            blocked.append({**e, "skipped_names": [nodes[s]["name"] for s in sorted(sk)]})

    kept = list(cur.values())
    if blocked:
        print(f"\nZachowano {len(blocked)} krawedzi mimo cech skrotu "
              f"(usuniecie rozspojnilo by graf):")
        for b in blocked:
            print(f"   {nodes[b['a']]['name']:26} - {nodes[b['b']]['name']:26} "
                  f"(pomija: {', '.join(b['skipped_names'][:3])})")

    adj = collections.defaultdict(set)
    for e in kept:
        adj[e["a"]].add(e["b"])
        adj[e["b"]].add(e["a"])
    for sid in nodes:
        nodes[sid]["degree"] = len(adj[sid])
        nodes[sid]["neighbours"] = sorted(adj[sid])

    print(f"\n=== WYNIK (TOL={TOL_M:.0f} m) ===")
    print(f"Krawedzi przed: {len(g['edges'])}  po: {len(kept)}  usunieto: {len(removed)}")
    print("\nPrzyklady usunietych skrotow (pomijajace najwiecej punktow):")
    for r in sorted(removed, key=lambda x: -len(x["skipped"]))[:15]:
        print(f"  {nodes[r['a']]['name']:26} - {nodes[r['b']]['name']:26} "
              f"pomija {len(r['skipped'])}: {', '.join(r['skipped_names'][:4])}")

    deg = collections.Counter(n["degree"] for n in nodes.values())
    print("\nRozklad stopni po redukcji:")
    for d in sorted(deg):
        print(f"  stopien {d}: {deg[d]:3}")
    print("\nWierzcholki stopnia >= 3 (wezly topologiczne):")
    for n in sorted(nodes.values(), key=lambda x: (-x["degree"], x["name"])):
        if n["degree"] >= 3:
            print(f"  {n['name']:34} st={n['degree']}")

    with open(os.path.join(WORK, "graph_clean.json"), "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes, "edges": kept, "removed": removed,
                   "params": {"tol_m": TOL_M, "R_earth_m": R_EARTH_M,
                              "proj": "equirectangular", "lat0": LAT0, "lon0": LON0}},
                  f, ensure_ascii=False, indent=1)
    print("\n-> work/graph_clean.json")


if __name__ == "__main__":
    main()
