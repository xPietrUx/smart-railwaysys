#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 3 — Rzeczywista dlugosc kazdej krawedzi oraz czas jazdy z rozkladu.

METODA WYZNACZANIA DLUGOSCI
Plik shapes.txt zawiera dla kazdego kursu lamana opisujaca faktyczny przebieg
toru wraz z kolumna shape_dist_traveled — narastajaca odlegloscia [m] liczona
wzdluz tej lamanej od jej poczatku.

Dla krawedzi (A,B) i konkretnego kursu:
  1. rzutujemy A i B na lamana: szukamy punktu lamanej najblizszego stacji,
     P(A) = argmin_i |L_i - A|,  P(B) = argmin_i |L_i - B|
  2. dlugosc odcinka = |shape_dist_traveled[P(B)] - shape_dist_traveled[P(A)]|

Otrzymujemy dlugosc mierzona wzdluz toru, a nie w linii prostej — a wiec
wielkosc odpowiadajaca kilometrazowi kolejowemu, nie odleglosci ortodromicznej.

AGREGACJA I ODPORNOSC
Ta sama krawedz wystepuje w wielu kursach, ktore moga korzystac z roznych
lamanych (np. rozne tory). Jako wartosc koncowa przyjmujemy MEDIANE po
wszystkich kursach — miare odporna na wartosci odstajace, wynikajace np.
z kursow prowadzonych objazdem. Zapisujemy tez rozstep i liczbe obserwacji,
co pozwala ocenic niepewnosc kazdego pomiaru.

WERYFIKACJA
Wynik porownano z oficjalnym kilometrazem PKP PLK (Regulamin sieci, zal. 2.6)
dla odcinkow linii nr 1 o znanych kilometrach osi stacji — patrz raport
w work/weryfikacja_dlugosci.txt.

CZAS JAZDY
Rownolegle wyznaczamy czas przejazdu z rozkladu: roznica miedzy przyjazdem
do B a odjazdem z A. Jako wartosc reprezentatywna bierzemy 10. percentyl
(najszybsze realizowane przejazdy), poniewaz mediana zawiera rezerwy
rozkladowe i postoje handlowe, a nas interesuje czas techniczny.
"""
import csv, json, math, os, collections, statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS = os.path.join(BASE, "src", "gtfs_ks")
WORK = os.path.join(BASE, "work")
R_EARTH_M = 6371008.8
LAT0, LON0 = 50.0, 19.0


def read(name):
    with open(os.path.join(GTFS, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_xy(lat, lon):
    return (R_EARTH_M * math.radians(lon - LON0) * math.cos(math.radians(LAT0)),
            R_EARTH_M * math.radians(lat - LAT0))


def hhmmss(t):
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def main():
    with open(os.path.join(WORK, "graph_clean.json"), encoding="utf-8") as f:
        g = json.load(f)
    nodes = g["nodes"]
    valid = {tuple(sorted((e["a"], e["b"]))) for e in g["edges"]}

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
        seq[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"],
                                  r["arrival_time"], r["departure_time"]))
    for k in seq:
        seq[k].sort()

    node_xy = {sid: to_xy(n["lat"], n["lon"]) for sid, n in nodes.items()}

    def project_trip(items, shape_id):
        """Rzutowanie MONOTONICZNE calej sekwencji przystankow na lamana.

        Rzutowanie kazdego przystanku niezaleznie (argmin po calej lamanej) jest
        bledne, gdy trasa przechodzi w poblizu tej samej stacji dwukrotnie —
        np. przy petli lub gdy stacja lezy przy rownoleglym torze. Argmin wybiera
        wtedy nieprawidlowe wystapienie, co daje absurdalne dlugosci
        (obserwowano Chybie - Chybie Mnich = 13.6 km zamiast 1.7 km).

        Rozwiazanie: przystanki rzutujemy w kolejnosci ich nastepstwa w kursie,
        przy czym rzut przystanku i+1 szukany jest wylacznie w czesci lamanej
        polozonej ZA rzutem przystanku i. Wymusza to zgodnosc kolejnosci
        przystankow z kierunkiem jazdy.
        """
        pts = shape_xy[shape_id]
        res, start = [], 0
        for _, sid, _, _ in items:
            if sid not in node_xy:
                res.append(None)
                continue
            sx, sy = node_xy[sid]
            best, bi, bd = 1e30, None, None
            for i in range(start, len(pts)):
                (x, y), d = pts[i]
                dd = (x - sx) ** 2 + (y - sy) ** 2
                if dd < best:
                    best, bi, bd = dd, i, d
            if bi is None:
                res.append(None)
            else:
                res.append((bd, math.sqrt(best)))
                start = bi
        return res

    obs_len = collections.defaultdict(list)
    obs_time = collections.defaultdict(list)

    for tid, items in seq.items():
        sh = trips[tid].get("shape_id")
        pr = project_trip(items, sh) if sh in shape_xy else [None] * len(items)
        for i in range(len(items) - 1):
            a, b = items[i][1], items[i + 1][1]
            key = tuple(sorted((a, b)))
            if key not in valid:
                continue
            if pr[i] and pr[i + 1]:
                da, ea = pr[i]
                db, eb = pr[i + 1]
                # odrzucamy rzuty odlegle od stacji > 600 m (bledna lamana)
                if ea < 600 and eb < 600:
                    L = abs(db - da) / 1000.0
                    if 0.05 < L < 80:
                        obs_len[key].append(L)
            try:
                dt = hhmmss(items[i + 1][2]) - hhmmss(items[i][3])
                if 20 <= dt <= 7200:
                    obs_time[key].append(dt)
            except Exception:
                pass

    # ---- FILTR KRETOSCI --------------------------------------------------
    # Krętość toru = dlugosc mierzona wzdluz toru / odleglosc ortodromiczna.
    # Dla kolei wartosc ta miesci sie praktycznie zawsze w przedziale 1.0-1.6;
    # wartosci powyzej ~2.5 oznaczaja blad dopasowania lamanej, a nie realny luk.
    # Obserwowano np. Chybie - Chybie Mnich: 13.60 km przy odleglosci 0.90 km
    # (kretosc 15.1) — czesc lamanych prowadzi tam trase okrezna, przez co
    # sama mediana dziedziczy blad. Odrzucamy zatem obserwacje o kretosci
    # spoza przedzialu [SIN_MIN, SIN_MAX], a dopiero z reszty liczymy mediane.
    SIN_MIN, SIN_MAX = 0.95, 2.5

    def hav_km(a, b):
        ax, ay = node_xy[a]
        bx, by = node_xy[b]
        return math.hypot(ax - bx, ay - by) / 1000.0

    out = []
    n_filtered = 0
    for e in g["edges"]:
        key = tuple(sorted((e["a"], e["b"])))
        raw = obs_len.get(key, [])
        hv = hav_km(key[0], key[1])
        Ls = [L for L in raw if hv > 0 and SIN_MIN <= L / hv <= SIN_MAX]
        if len(raw) != len(Ls):
            n_filtered += 1
        Ts = sorted(obs_time.get(key, []))

        if Ls:
            length, src, conf = round(statistics.median(Ls), 3), "gtfs_shape", "measured"
        else:
            # Fallback: brak wiarygodnego pomiaru -> odleglosc ortodromiczna
            # przemnozona przez mediane kretosci wyznaczona na calej sieci.
            length, src, conf = None, "haversine_x_sinuosity", "derived"

        rec = {
            "a": key[0], "b": key[1],
            "a_name": nodes[key[0]]["name"], "b_name": nodes[key[1]]["name"],
            "trips": e["trips"], "lines": e["lines"],
            "len_km": length, "len_source": src, "len_confidence": conf,
            "len_n": len(Ls), "len_n_raw": len(raw),
            "len_min": round(min(Ls), 3) if Ls else None,
            "len_max": round(max(Ls), 3) if Ls else None,
            "len_spread": round(max(Ls) - min(Ls), 3) if Ls else None,
            "haversine_km": round(hv, 3),
            "sinuosity": round(length / hv, 3) if (Ls and hv > 0) else None,
            "t_p10_s": Ts[max(0, int(0.10 * len(Ts)))] if Ts else None,
            "t_median_s": int(statistics.median(Ts)) if Ts else None,
            "t_n": len(Ts),
        }
        out.append(rec)

    sins = [r["sinuosity"] for r in out if r["sinuosity"]]
    med_sin = statistics.median(sins)
    for r in out:
        if r["len_km"] is None:
            r["len_km"] = round(r["haversine_km"] * med_sin, 3)
            r["sinuosity"] = round(med_sin, 3)
    print(f"Krawedzi z odrzuconymi obserwacjami: {n_filtered}")
    print(f"Mediana kretosci sieci: {med_sin:.4f}  "
          f"(1. kwartyl {sorted(sins)[len(sins)//4]:.3f}, "
          f"3. kwartyl {sorted(sins)[3*len(sins)//4]:.3f})")

    miss = [r for r in out if r["len_confidence"] == "derived"]
    print(f"\nKrawedzi: {len(out)}   z pomiaru: {len(out)-len(miss)}   "
          f"z fallbacku: {len(miss)}")
    for r in miss:
        print(f"   FALLBACK: {r['a_name']:30} - {r['b_name']:30} "
              f"-> {r['len_km']:.2f} km (haversine {r['haversine_km']:.2f})")

    spreads = [r["len_spread"] for r in out if r["len_spread"] is not None]
    print(f"\nRozrzut pomiarow dlugosci (max-min) na krawedz:")
    print(f"  mediana : {statistics.median(spreads):.3f} km")
    print(f"  90 perc.: {sorted(spreads)[int(0.9*len(spreads))]:.3f} km")
    print(f"  maks    : {max(spreads):.3f} km")
    worst = sorted([r for r in out if r["len_spread"] is not None],
                   key=lambda x: -x["len_spread"])[:8]
    print("\nNajwiekszy rozrzut (kandydaci do kontroli recznej):")
    for r in worst:
        print(f"  {r['a_name']:28} - {r['b_name']:28} "
              f"med={r['len_km']:6.2f} min={r['len_min']:6.2f} max={r['len_max']:6.2f} n={r['len_n']}")

    tot = sum(r["len_km"] for r in out if r["len_km"])
    print(f"\nLaczna dlugosc wszystkich krawedzi: {tot:.1f} km")

    with open(os.path.join(WORK, "edges_measured.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("-> work/edges_measured.json")


if __name__ == "__main__":
    main()
