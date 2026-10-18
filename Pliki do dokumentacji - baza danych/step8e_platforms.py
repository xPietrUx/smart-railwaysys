#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 8e — Liczba peronow i krawedzi peronowych z wykazu PLK (zal. 2.18).

Wykaz 2.18 zawiera jeden rekord na KRAWEDZ PERONOWA (para peron-tor), z polami:
nazwa punktu, wyroznik, nr peronu, nr toru, wysokosc, dlugosc.

Dla kazdego punktu wyznaczamy:
  - platforms  = liczba roznych numerow peronow (fizyczne perony),
  - platform_edges = liczba rekordow (krawedzi peronowych = torow przyperonowych),
  - platform_len_max = najwieksza dlugosc krawedzi peronowej [m] (pojemnosc
    stacji — najdluzszy sklad, jaki moze sie zatrzymac).

Pole platforms zastepuje dotychczasowa wartosc szacowana (platforms_est).
Krawedzie peronowe (platform_edges) sa dobrym przyblizeniem liczby torow
przyperonowych — uzupelniaja pole tracks, ktore rowniez bylo dotad szacowane.

Nazwy dopasowywane sa procedura z krokow 8b/8c (normalizacja + warianty "Gl").
Punkty spoza sieci PLK (Bohumin, Skalite) nie wystepuja w wykazie — pozostaja
z wartoscia szacowana, co jest odnotowane.
"""
import openpyxl, os, json, unicodedata, collections

UP = "/mnt/user-data/uploads"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")
PLIK = "N_ZAL_2_18_20252026_20260629071403.xlsx"


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


def num(x):
    if x is None:
        return None
    try:
        # dlugosc bywa zapisana jako "N: 331 \nP: 375" — bierzemy max liczbe
        s = str(x).replace(",", ".")
        vals = []
        for tok in s.replace("N:", " ").replace("P:", " ").split():
            try:
                vals.append(float(tok))
            except ValueError:
                pass
        return max(vals) if vals else None
    except Exception:
        return None


def main():
    wb = openpyxl.load_workbook(os.path.join(UP, PLIK), read_only=True, data_only=True)
    ws = [s for s in wb.worksheets if "dane" in s.title][0]
    rows = [r for r in ws.iter_rows(min_row=8, values_only=True) if r[0]]
    wb.close()

    agg = collections.defaultdict(lambda: {"perony": set(), "kraw": 0, "dl": []})
    for r in rows:
        nazwa, wyr, zlk, nrp, nrt, wys, dl = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        n = norm(nazwa)
        agg[n]["perony"].add(str(nrp))
        agg[n]["kraw"] += 1
        d = num(dl)
        if d:
            agg[n]["dl"].append(d)

    with open(os.path.join(WORK, "graph_clean.json"), encoding="utf-8") as f:
        nodes = json.load(f)["nodes"]
    with open(os.path.join(WORK, "selected.json"), encoding="utf-8") as f:
        wybrane = json.load(f)["selected"]

    out = {}
    n_ok = 0
    for sid in wybrane:
        name = nodes[sid]["name"]
        hit = None
        for v in variants(name):
            if v in agg:
                hit = v
                break
        if not hit:
            out[sid] = {"plk218_matched": False}
            continue
        n_ok += 1
        a = agg[hit]
        out[sid] = {
            "plk218_matched": True,
            "platforms": len(a["perony"]),
            "platform_edges": a["kraw"],
            "platform_len_max": max(a["dl"]) if a["dl"] else None,
        }

    print(f"Wezlow: {len(wybrane)}  dopasowanych do PLK 2.18: {n_ok}")
    niedop = [nodes[s]["name"] for s in wybrane if not out[s].get("plk218_matched")]
    print(f"Niedopasowane (spoza sieci PLK): {niedop}")
    perony = [out[s]["platforms"] for s in wybrane if out[s].get("plk218_matched")]
    print(f"Perony — min {min(perony)}, mediana {sorted(perony)[len(perony)//2]}, "
          f"max {max(perony)}")
    top = sorted(((out[s]["platforms"], nodes[s]["name"]) for s in wybrane
                  if out[s].get("plk218_matched")), reverse=True)[:6]
    print("Najwiecej peronow:", ", ".join(f"{n}({p})" for p, n in top))

    with open(os.path.join(WORK, "platforms_plk.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n-> work/platforms_plk.json")


if __name__ == "__main__":
    main()
