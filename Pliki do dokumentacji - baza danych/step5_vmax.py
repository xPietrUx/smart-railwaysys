#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 5 — Predkosc maksymalna odcinka.

SYTUACJA ZRODLOWA
Wartoscia autorytatywna dla vmax jest zalacznik 2.1 Regulaminu sieci PKP PLK
("Wykaz maksymalnych predkosci"). Nie byl on dostepny przy budowie bazy, wiec
vmax wyznaczono POSREDNIO z rozkladu jazdy. Kazdy rekord ma znacznik zrodla
i wiarygodnosci: wartosci sa oznaczone jako "derived", nie "measured", i przy
aktualizacji bazy powinny zostac zastapione danymi PLK.

MODEL FIZYCZNY
Naiwne v = L/t daje predkosc handlowa (srednia), nie maksymalna: pociag rusza
z postoju, rozpedza sie, jedzie ze stala predkoscia i hamuje. Przyjmujemy
trapezowy profil predkosci (ruch jednostajnie przyspieszony, jednostajny,
jednostajnie opozniony):

    t  =  L/v  +  v/(2a)  +  v/(2b)

    t — czas przejazdu miedzy zatrzymaniami [s]
    L — dlugosc odcinka [m]
    v — predkosc maksymalna osiagana na odcinku [m/s]
    a — przyspieszenie rozruchu  [m/s^2]
    b — opoznienie hamowania     [m/s^2]

Skladniki v/(2a) i v/(2b) to straty czasu na rozruch i hamowanie: dla ruchu
jednostajnie zmiennego droga rozpedzania wynosi v^2/(2a), a czas jej przebycia
v/a, podczas gdy ta sama droga przy stalej predkosci zajelaby v/(2a) — roznica
wynosi wiec dokladnie v/(2a).

Mnozac obustronnie przez v i porzadkujac otrzymujemy rownanie kwadratowe:

    k = 1/(2a) + 1/(2b)
    k*v^2 - t*v + L = 0
    v = ( t - sqrt(t^2 - 4kL) ) / (2k)

Wybieramy pierwiastek z minusem — odpowiada rozwiazaniu fizycznemu. Gdy
wyroznik t^2 - 4kL < 0, odcinek jest zbyt krotki, by osiagnac predkosc
ustalona (profil trojkatny); wowczas v = t/(2k).

DLACZEGO POMIAR NA KRAWEDZIACH ELEMENTARNYCH
Pierwsza wersja (step5_vmax_v1_po_kontrakcji.py) stosowala model do odcinkow
JUZ SKONTRAHOWANYCH. Bylo to bledne: czas przejazdu takiego odcinka zawiera
postoje na wszystkich przystankach posrednich oraz wielokrotne rozruchy
i hamowania, ktorych model z jednym rozruchem nie uwzglednia. Skutek: dla
odcinka Zawiercie - Czestochowa (linia nr 1, predkosc szlakowa 140-160 km/h)
model dawal 70 km/h. Predkosc wyznaczamy wiec na krawedziach elementarnych.

WYKORZYSTANIE PRZEJAZDOW BEZPOSTOJOWYCH
Pociag zatrzymujacy sie co 3-4 km nie zdazy rozpedzic sie do predkosci
szlakowej, wiec estymata z takich przejazdow jest zanizona. Lepszym swiadectwem
sa kursy przyspieszone, ktore pokonuja kilka szlakow bez zatrzymania — to
wlasnie te przejazdy zostaly w kroku 2 usuniete z grafu jako "krawedzie-skroty".
Odrzucilismy je jako krawedzie infrastruktury, ale ich CZASY pozostaja cenna
informacja: przejazd A->C bez postoju posrednich ma jeden rozruch i jedno
hamowanie na calej dlugosci, wiec model trapezowy stosuje sie do niego wprost
i daje estymate znacznie blizsza predkosci szlakowej.

Dla kazdej krawedzi elementarnej zbieramy zatem estymaty z dwoch zrodel:
  (E1) przejazdy miedzy sasiednimi zatrzymaniami (dolne ograniczenie),
  (E2) przejazdy bezpostojowe obejmujace ta krawedz (estymata lepsza),
i przyjmujemy MAKSIMUM — najlepsze swiadectwo predkosci osiagalnej.

AGREGACJA DO ODCINKA
Predkosc odcinka po kontrakcji liczymy jako srednia wazona dlugoscia krawedzi
skladowych, a nastepnie zaokraglamy W DOL do klasy ze zbioru predkosci
konstrukcyjnych {30,40,50,60,70,80,100,120,140,160}. Zaokraglenie w dol,
bo estymata z rozkladu jest wartoscia gorna faktycznie realizowana.
"""
import csv, json, math, os, collections, statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS = os.path.join(BASE, "src", "gtfs_ks")
WORK = os.path.join(BASE, "work")

A_ACC, B_DEC = 0.6, 0.9
KLASY = [30, 40, 50, 60, 70, 80, 100, 120, 140, 160]
VMAX_LIMIT = 160


def read(n):
    with open(os.path.join(GTFS, n), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sec(t):
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def vmax_z_czasu(L_m, t_s, a=A_ACC, b=B_DEC):
    k = 1.0 / (2 * a) + 1.0 / (2 * b)
    disc = t_s * t_s - 4 * k * L_m
    if disc < 0:
        return t_s / (2 * k), "trojkatny"
    return (t_s - math.sqrt(disc)) / (2 * k), "trapezowy"


def do_klasy(v):
    k = [x for x in KLASY if x <= v]
    return k[-1] if k else KLASY[0]


def main():
    with open(os.path.join(WORK, "graph_clean.json"), encoding="utf-8") as f:
        gc = json.load(f)
    with open(os.path.join(WORK, "edges_measured.json"), encoding="utf-8") as f:
        measured = json.load(f)
    with open(os.path.join(WORK, "selected.json"), encoding="utf-8") as f:
        sel = json.load(f)

    nodes = gc["nodes"]
    elen = {tuple(sorted((e["a"], e["b"]))): e for e in measured}
    kept = set(elen)
    adj = collections.defaultdict(set)
    for (a, b) in kept:
        adj[a].add(b)
        adj[b].add(a)

    est = collections.defaultdict(list)   # krawedz -> [(v_ms, zrodlo)]

    # --- E1: przejazdy miedzy sasiednimi zatrzymaniami -----------------------
    for e in measured:
        key = (e["a"], e["b"])
        t = e["t_p10_s"]
        if t and t > 0:
            v, _ = vmax_z_czasu(e["len_km"] * 1000, t)
            est[tuple(sorted(key))].append((v, "E1_miedzy_zatrzymaniami"))

    # --- E2: przejazdy bezpostojowe (dawne krawedzie-skroty) -----------------
    # dla kazdego usunietego skrotu odtwarzamy sciezke w grafie zachowanym
    def sciezka(a, b, dozwolone):
        pop = {a: None}
        q = [a]
        while q:
            v = q.pop(0)
            if v == b:
                out = []
                while v is not None:
                    out.append(v)
                    v = pop[v]
                return out[::-1]
            for w in adj[v]:
                if w not in pop and (w in dozwolone or w == b):
                    pop[w] = v
                    q.append(w)
        return None

    seq = collections.defaultdict(list)
    for r in read("stop_times.txt"):
        seq[r["trip_id"]].append((int(r["stop_sequence"]), r["stop_id"],
                                  r["arrival_time"], r["departure_time"]))
    for k in seq:
        seq[k].sort()

    skrot_czasy = collections.defaultdict(list)
    for tid, items in seq.items():
        for i in range(len(items) - 1):
            a, b = items[i][1], items[i + 1][1]
            key = tuple(sorted((a, b)))
            if key in kept:
                continue
            try:
                dt = sec(items[i + 1][2]) - sec(items[i][3])
            except Exception:
                continue
            if 20 <= dt <= 7200:
                skrot_czasy[key].append(dt)

    n_e2 = 0
    for r in gc["removed"]:
        key = tuple(sorted((r["a"], r["b"])))
        ts = sorted(skrot_czasy.get(key, []))
        if not ts:
            continue
        t = ts[max(0, int(0.10 * len(ts)))]
        path = sciezka(key[0], key[1], set(r["skipped"]))
        if not path or len(path) < 2:
            continue
        comp = [tuple(sorted((path[i], path[i + 1]))) for i in range(len(path) - 1)]
        if any(c not in elen for c in comp):
            continue
        L = sum(elen[c]["len_km"] for c in comp) * 1000
        if L <= 0:
            continue
        v, _ = vmax_z_czasu(L, t)
        for c in comp:
            est[c].append((v, "E2_bezpostojowy"))
        n_e2 += 1

    print(f"Krawedzi elementarnych: {len(elen)}")
    print(f"Przejazdow bezpostojowych wykorzystanych: {n_e2}")

    edge_v = {}
    src_cnt = collections.Counter()
    for key in elen:
        cand = est.get(key, [])
        if not cand:
            edge_v[key] = (60 / 3.6, "domyslna")
            src_cnt["domyslna"] += 1
            continue
        v, s = max(cand, key=lambda x: x[0])
        edge_v[key] = (min(v, VMAX_LIMIT / 3.6), s)
        src_cnt[s] += 1
    print("Zrodlo estymaty przyjetej na krawedzi:")
    for k, v in src_cnt.items():
        print(f"   {k:26} {v}")

    # --- agregacja do odcinkow po kontrakcji --------------------------------
    id2 = {tuple(sorted((s["a"], s["b"]))): s for s in sel["segments"]}
    for s in sel["segments"]:
        path = [s["a"]] + s["via_ids"] + [s["b"]]
        comp = [tuple(sorted((path[i], path[i + 1]))) for i in range(len(path) - 1)]
        comp = [c for c in comp if c in edge_v]
        if not comp:
            s["vmax"] = 60
            s["vmax_source"] = "domyslna"
            s["vmax_confidence"] = "assumed"
            continue
        wl = sum(elen[c]["len_km"] for c in comp)
        vw = sum(edge_v[c][0] * elen[c]["len_km"] for c in comp) / wl * 3.6
        s["v_model_kmh"] = round(vw, 1)
        s["v_srednia_kmh"] = (round(s["len_km"] / (s["t_p10_s"] / 3600.0), 1)
                              if s["t_p10_s"] else None)
        s["vmax"] = do_klasy(vw)
        s["vmax_source"] = "model_trapezowy_z_rozkladu"
        s["vmax_confidence"] = "derived"
        s["vmax_n_krawedzi"] = len(comp)

    print("\nNajdluzsze odcinki — porownanie:")
    print(f"{'odcinek':50}{'km':>7}{'v_sr':>7}{'v_mod':>7}{'vmax':>6}")
    for s in sorted(sel["segments"], key=lambda x: -x["len_km"])[:12]:
        nm = f"{s['a_name']} - {s['b_name']}"
        print(f"{nm:50}{s['len_km']:>7.2f}{s.get('v_srednia_kmh') or 0:>7.1f}"
              f"{s.get('v_model_kmh') or 0:>7.1f}{s['vmax']:>6}")

    c = collections.Counter(s["vmax"] for s in sel["segments"])
    print("\nRozklad klas vmax:")
    for k in sorted(c):
        print(f"  {k:3} km/h : {c[k]:3} odcinkow")

    with open(os.path.join(WORK, "segments_vmax.json"), "w", encoding="utf-8") as f:
        json.dump(sel["segments"], f, ensure_ascii=False, indent=1)
    print("\n-> work/segments_vmax.json")


if __name__ == "__main__":
    main()
