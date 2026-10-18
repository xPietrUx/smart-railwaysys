#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 8d — Kontrola krzyzowa dlugosci: pomiar z GTFS vs kilometraz PKP PLK.

Teraz, gdy dysponujemy kilometrazem osi kazdego punktu (zal. 2.6), mozemy
niezaleznie zweryfikowac dlugosci zmierzone z geometrii GTFS (krok 3). Dla
kazdego odcinka lezacego na wspolnej linii roznica kilometrazu koncow jest
oficjalna dlugoscia tego odcinka wg zarzadcy infrastruktury.

Porownanie obejmuje wylacznie odcinki elementarne (bez punktow posrednich),
bo tylko dla nich r
oznica km jest jednoznaczna. Wynik to walidacja metody
pomiarowej — jesli obie wartosci sa zgodne, pomiar z GTFS jest wiarygodny.
"""
import json, os, unicodedata, statistics, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")


def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = s.replace("glowna", "gl").replace("gl.", "gl")
    s = s.replace(".", " ").replace("-", " ")
    return " ".join(s.split())


def variants(name):
    n = norm(name)
    out = [n]
    if n.endswith(" g"):
        out += [n[:-2] + " gl", n[:-2] + " gowna"]
    return out


def main():
    with open(os.path.join(WORK, "plk.json"), encoding="utf-8") as f:
        plk = json.load(f)
    with open(os.path.join(WORK, "segments_plk.json"), encoding="utf-8") as f:
        segs = json.load(f)
    post = plk["posterunki"]

    def km_na_linii(name):
        for v in variants(name):
            if v in post:
                return {p["linia"]: p["km"] for p in post[v]}
        return {}

    pary = []
    for s in segs:
        if s["via"]:                       # tylko odcinki elementarne
            continue
        ka = km_na_linii(s["a_name"])
        kb = km_na_linii(s["b_name"])
        wsp = set(ka) & set(kb)
        if not wsp:
            continue
        # linia z kilometrazem najblizszym pomiarowi
        best = min(wsp, key=lambda l: abs(abs(ka[l] - kb[l]) - s["len_km"]))
        km_plk = abs(ka[best] - kb[best])
        pary.append((s["a_name"], s["b_name"], s["len_km"], km_plk,
                     s["len_km"] - km_plk, best))

    print(f"Odcinkow porownanych: {len(pary)}")
    roz = [abs(p[4]) for p in pary]
    print(f"\nRoznica |GTFS - PLK|:")
    print(f"  srednia : {statistics.mean(roz):.3f} km")
    print(f"  mediana : {statistics.median(roz):.3f} km")
    print(f"  90 perc.: {sorted(roz)[int(0.9*len(roz))]:.3f} km")
    print(f"  maks    : {max(roz):.3f} km")
    wzgl = [abs(p[4]) / p[3] * 100 for p in pary if p[3] > 0.1]
    print(f"  sredni blad wzgledny: {statistics.mean(wzgl):.1f} %")

    print("\nNajwieksze roznice (kandydaci do kontroli):")
    for a, b, g, plk_km, d, lin in sorted(pary, key=lambda x: -abs(x[4]))[:10]:
        print(f"  {a:26} - {b:24} GTFS={g:6.2f} PLK={plk_km:6.2f} "
              f"Δ={d:+.2f} (l.{lin})")

    with open(os.path.join(WORK, "walidacja_km.json"), "w", encoding="utf-8") as f:
        json.dump([{"a": p[0], "b": p[1], "gtfs_km": p[2], "plk_km": p[3],
                    "roznica": round(p[4], 3), "linia": p[5]} for p in pary],
                  f, ensure_ascii=False, indent=1)
    print(f"\n-> work/walidacja_km.json ({len(pary)} par)")


if __name__ == "__main__":
    main()
