#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 8c — Wzbogacenie stacji o dane z wykazu posterunkow PLK (zal. 2.6).

Dla kazdego wezla odczytuje z wykazu 2.6:
  - typ punktu wg PLK (Wyroznik: ST=stacja, PODG=posterunek odgalezny,
    PO=przystanek osobowy, STTH=stacja techniczna itd.),
  - kilometraz osi na kazdej linii, na ktorej wezel lezy,
  - informacje, czy w punkcie jest czynny peron.

Typ PLK zastepuje typ wyliczony z topologii (dokladniejszy — pochodzi
z ewidencji zarzadcy infrastruktury). Zachowujemy oba: type (PLK)
i type_topologiczny (z grafu), co pozwala je porownac w pracy.

Pole platforms (liczba peronow) nadal nie ma pokrycia — wykaz 2.6 informuje
tylko o ISTNIENIU peronu (TAK/NIE), nie o ich liczbie. Liczba peronow jest
w zal. 2.18, ktory ma inna strukture (rekord per krawedz peronowa); jego
przetworzenie zostawiono jako mozliwe rozszerzenie.
"""
import json, os, unicodedata, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")

# Legenda wyroznikow wg oficjalnego objasnienia do zal. 2.6 Regulaminu sieci PLK.
# UWAGA: wczesniejsza wersja tego slownika zawierala bledne przypisania
# (L jako "ladownia", BST jako "bocznica szlakowa", PODS jako "posterunek
# odstepowy"). W obecnym zbiorze 57 wezlow wystepuja wylacznie ST/PO/PODG/MPO,
# wiec bledy nie zanieczyscily danych, ale przy rozszerzeniu bazy mialyby
# skutek. Ponizsza wersja jest zgodna z legenda zrodlowa.
TYP_PLK = {
    "ST": "stacja",
    "STTH": "stacja techniczna",
    "M": "mijanka",
    "ML": "mijanka i ładownia",
    "MLP": "mijanka, ładownia i przystanek osobowy",
    "MPO": "mijanka i przystanek osobowy",
    "PO": "przystanek osobowy publiczny",
    "PODG": "posterunek odgałęźny",
    "PODS": "przystanek osobowy i posterunek odstępowy",
    "ODST": "posterunek odstępowy",
    "ODGS": "posterunek odgałęźny i przystanek służbowy",
    "ODLP": "posterunek odstępowy, ładownia i przystanek osobowy",
    "ODPS": "posterunek odstępowy i przystanek służbowy",
    "PGR": "przejście graniczne",
    "BST": "bocznica stacyjna",
    "BSZ": "bocznica szlakowa",
    "L": "ogólnodostępna bocznica szlakowa",
    "LPO": "ogólnodostępna bocznica szlakowa i przystanek osobowy",
    "PBSP": "posterunek bocznicowy szlakowy i przystanek osobowy",
    "PBST": "posterunek bocznicowy stacyjny",
    "PBSZ": "posterunek bocznicowy szlakowy",
    "PGL": "posterunek odgałęźny i ładownia",
    "PGLP": "posterunek odgałęźny, przystanek osobowy i ładownia",
    "POGM": "posterunek odgałęźny i mijanka",
    "POGP": "przystanek osobowy i posterunek odgałęźny",
    "PK": "przystanek w kolejowej komunikacji autobusowej",
}


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
    with open(os.path.join(WORK, "graph_clean.json"), encoding="utf-8") as f:
        nodes = json.load(f)["nodes"]
    with open(os.path.join(WORK, "selected.json"), encoding="utf-8") as f:
        wybrane = json.load(f)["selected"]

    post = plk["posterunki"]

    enrich = {}
    n_ok = 0
    for sid in wybrane:
        name = nodes[sid]["name"]
        rec = None
        for v in variants(name):
            if v in post:
                rec = post[v]
                break
        if not rec:
            enrich[sid] = {"plk_matched": False}
            continue
        n_ok += 1
        # Punkt moze wystepowac w 2.6 w KILKU rekordach — na roznych liniach,
        # a niekiedy pod roznymi wyroznikami i z roznym kilometrazem osi.
        # Przyklad: Katowice Szopienice Poludniowe figuruje jako PODG
        # (linie 1, 138, 660) oraz jako PO (linie 1, 138) z kilometrazem
        # wiekszym o ok. 276 m. Reguly rozstrzygajace:
        #   (1) typ punktu — rekord o najwyzszej randze ruchowej (ST > STTH >
        #       PODG > PODS > PGR > pozostale), bo ona okresla mozliwosci
        #       prowadzenia ruchu, ktore modeluje symulator;
        #   (2) peron — czynny, jesli WYSTEPUJE W DOWOLNYM rekordzie punktu
        #       (peron nalezy do punktu, nie do konkretnej linii);
        #   (3) kilometraz — zachowywany osobno dla kazdej linii (plk_km_osi),
        #       a przy wielu rekordach na tej samej linii brany jest rekord
        #       o najwyzszej randze, spojnie z regula (1).
        rank = {"ST": 0, "STTH": 1, "PODG": 2, "PODS": 3, "PGR": 4}
        rec_sorted = sorted(rec, key=lambda p: rank.get(p["typ"], 9))
        glowny = rec_sorted[0]
        peron = any(p.get("peron") for p in rec)
        zarzadcy = sorted({p.get("peron_zarzadca") for p in rec
                           if p.get("peron_zarzadca")})
        km_osi = {}
        for p in rec_sorted[::-1]:      # nizsza ranga najpierw, wyzsza nadpisuje
            km_osi[p["linia"]] = p["km"]
        enrich[sid] = {
            "plk_matched": True,
            "plk_typ": glowny["typ"],
            "plk_typ_opis": TYP_PLK.get(glowny["typ"], glowny["typ"]),
            "plk_ma_peron": peron,
            "plk_peron_zarzadca": "; ".join(zarzadcy) if zarzadcy else None,
            "plk_wyrozniki": sorted({p["typ"] for p in rec}),
            "plk_linie": sorted({p["linia"] for p in rec}),
            "plk_km_osi": km_osi,
            "plk_nazwa": glowny["nazwa"],
        }

    print(f"Wezlow: {len(wybrane)}  dopasowanych do PLK 2.6: {n_ok}")
    typy = collections.Counter(e.get("plk_typ") for e in enrich.values()
                               if e.get("plk_matched"))
    print("Typy PLK:", dict(typy))
    perony = sum(1 for e in enrich.values() if e.get("plk_ma_peron"))
    print(f"Wezlow z czynnym peronem: {perony}")

    with open(os.path.join(WORK, "stations_plk.json"), "w", encoding="utf-8") as f:
        json.dump(enrich, f, ensure_ascii=False, indent=1)
    print("\n-> work/stations_plk.json")


if __name__ == "__main__":
    main()
