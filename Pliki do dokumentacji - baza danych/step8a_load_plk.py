#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 8a — Wczytanie oficjalnych wykazow PKP PLK (Regulamin sieci 2025/2026).

Konwertuje cztery zalaczniki XLSX do jednego pliku posredniego plk.json,
oczyszczajac naglowki i typujac wartosci. Zrodla:
  zal. 1   — Wykaz linii kolejowych (numer, nazwa, km poczatku/konca)
  zal. 2.1 — Wykaz maksymalnych predkosci (nr linii, tor, km, EZT/wagon/towar)
  zal. 2.4 — Klasy odcinkow linii (nr linii, tor, km, klasa)
  zal. 2.6 — Wykaz posterunkow ruchu (nr linii, wyroznik, nazwa, km osi, peron)

Stan wykazow: 30.08.2026 (pole "Stan na dzien" w naglowku kazdego pliku).
"""
import openpyxl, os, json, unicodedata, collections

UP = "/mnt/user-data/uploads"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")

PLIKI = {
    "linie":    "ZAL_1_Reg_25-26_v37_publ.xlsx",
    "predkosci":"N_ZAL_2_1_20252026_20260629071359.xlsx",
    "klasy":    "N_ZAL_2_4_20252026_20260629071405.xlsx",
    "posterunki":"N_ZAL_2_6_20252026_20260629071407_1_.xlsx",
}


def norm(s):
    """Normalizacja nazwy punktu: bez znakow diakrytycznych, ujednolicone 'Gl'."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = s.replace("glowna", "gl").replace("gl.", "gl")
    s = s.replace(".", " ").replace("-", " ")
    return " ".join(s.split())


def num(x):
    if x is None or x == "":
        return None
    try:
        return float(str(x).replace(",", ".").strip())
    except ValueError:
        return None


def load_dane(fname):
    wb = openpyxl.load_workbook(os.path.join(UP, fname), read_only=True, data_only=True)
    ws = [s for s in wb.worksheets if "dane" in s.title][0]
    rows = [r for r in ws.iter_rows(min_row=8, values_only=True) if r[0] is not None]
    wb.close()
    return rows


def main():
    out = {}

    # --- zal. 1: linie ------------------------------------------------------
    linie = {}
    for r in load_dane(PLIKI["linie"]):
        nr = str(r[0]).strip()
        linie[nr] = {
            "nazwa": r[1], "start": r[2], "km_start": num(r[3]),
            "koniec": r[4], "km_koniec": num(r[5]), "uwagi": r[6],
        }
    out["linie"] = linie
    print(f"zal.1  linie          : {len(linie)}")

    # --- zal. 2.6: posterunki (kluczowe — mapowanie nazwa<->(linia,km)) ------
    posterunki = collections.defaultdict(list)   # norm_nazwa -> [(linia, km, typ, peron, nazwa_org)]
    by_line = collections.defaultdict(list)       # linia -> [(km, norm_nazwa, typ)]
    for r in load_dane(PLIKI["posterunki"]):
        nr = str(r[0]).strip()
        nazwa, typ, km, peron = r[3], r[2], num(r[4]), r[5]
        if nazwa is None or km is None:
            continue
        nn = norm(nazwa)
        # Kolumna "Peron" w zal. 2.6 NIE jest binarna. Legenda arkusza podaje
        # wartosci: "TAK" (peron czynny zarzadzany przez PLK), nazwa podmiotu
        # zarzadzajacego (np. "PKP S.A.", "UM Tychy", "Port Lotniczy Lublin
        # S.A.") — rowniez oznaczajaca peron CZYNNY — albo pusta (brak peronu).
        # Sprowadzenie do "== TAK" gubilo perony zarzadzane przez inne podmioty
        # (np. Tychy Lodowisko, gdzie zarzadca jest miasto).
        peron_txt = None if peron in (None, "") else str(peron).strip()
        posterunki[nn].append({"linia": nr, "km": km, "typ": typ,
                               "peron": peron_txt is not None,
                               "peron_zarzadca": (None if peron_txt in (None, "TAK")
                                                  else peron_txt),
                               "nazwa": nazwa})
        by_line[nr].append((km, nn, typ))
    for k in by_line:
        by_line[k].sort()
    out["posterunki"] = {k: v for k, v in posterunki.items()}
    out["posterunki_by_line"] = {k: v for k, v in by_line.items()}
    print(f"zal.2.6 nazwy punktow : {len(posterunki)}  (linii z punktami: {len(by_line)})")

    # --- zal. 2.1: predkosci ------------------------------------------------
    predkosci = collections.defaultdict(list)     # linia -> [(tor, km0, km1, ezt, wagon, towar)]
    for r in load_dane(PLIKI["predkosci"]):
        nr = str(r[0]).strip()
        tor, km0, km1 = r[2], num(r[3]), num(r[4])
        ezt, wag, tow = num(r[5]), num(r[6]), num(r[7])
        if km0 is None or km1 is None:
            continue
        predkosci[nr].append({"tor": tor, "km0": min(km0, km1), "km1": max(km0, km1),
                              "ezt": ezt, "wagon": wag, "towar": tow})
    out["predkosci"] = {k: v for k, v in predkosci.items()}
    print(f"zal.2.1 linii z vmax  : {len(predkosci)}  "
          f"(rekordow: {sum(len(v) for v in predkosci.values())})")

    # --- zal. 2.4: klasy ----------------------------------------------------
    klasy = collections.defaultdict(list)
    for r in load_dane(PLIKI["klasy"]):
        nr = str(r[0]).strip()
        tor, km0, km1, kl = r[2], num(r[3]), num(r[4]), r[5]
        if km0 is None or km1 is None:
            continue
        klasy[nr].append({"tor": tor, "km0": min(km0, km1), "km1": max(km0, km1),
                          "klasa": kl})
    out["klasy"] = {k: v for k, v in klasy.items()}
    print(f"zal.2.4 linii z klasa : {len(klasy)}")

    with open(os.path.join(WORK, "plk.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print("\n-> work/plk.json")


if __name__ == "__main__":
    main()
