#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 8b — Wzbogacenie bazy o dane PKP PLK (predkosci, klasy, liczba torow, km osi).

PROBLEM DOPASOWANIA
Wykazy PLK indeksowane sa para (numer linii, kilometraz), a nie nazwa odcinka.
Kazdy moj wezel wystepuje w wykazie 2.6 na jednej lub wielu liniach (stacja
wezlowa Chorzow Batory lezy na 7 liniach). Aby odczytac predkosc odcinka (A,B),
trzeba najpierw ustalic WSPOLNA linie, po ktorej biegnie ten odcinek, oraz
zakres kilometrazu [km(A), km(B)] na tej linii.

ALGORYTM PRZYPISANIA LINII DO ODCINKA
  1. L(A) = zbior linii, na ktorych lezy A (z wykazu 2.6)
     L(B) = zbior linii, na ktorych lezy B
  2. wspolne = L(A) ∩ L(B)
  3. Dla kazdej linii ze zbioru wspolne mamy km(A) i km(B) na tej linii.
     Sprawdzamy, czy miedzy A i B na tej linii NIE MA innego wybranego wezla —
     jesli jest, to odcinek (A,B) nie biegnie ta linia bezposrednio (istnieje
     wezel posredni), wiec linie odrzucamy.
  4. Sposrod pozostalych wybieramy linie, dla ktorej |km(B)-km(A)| jest
     najblizsze zmierzonej dlugosci odcinka (krok 3) — to najlepsze
     potwierdzenie, ze wybralismy wlasciwy szlak.
  5. Jesli wspolne == pusty zbior lub zadna linia nie przeszla kontroli:
     odcinek pozostaje z wartosciami modelowymi (vmax_confidence = derived).

ODCZYT PREDKOSCI NA ZAKRESIE
Na wybranej linii i zakresie [km0, km1] wykaz 2.1 zawiera zwykle wiele
pod-odcinkow o roznych predkosciach (linia 139 ma ich kilkadziesiat). Dla
kazdej z trzech kategorii (EZT, sklad wagonowy, towarowy) i dla kazdego toru
(N, P) wyznaczamy predkosc jako SREDNIA WAZONA DLUGOSCIA pod-odcinkow
przecinajacych sie z [km0, km1]:

    v = sum_i ( v_i * dlugosc_przeciecia_i ) / sum_i dlugosc_przeciecia_i

a nastepnie zaokraglamy w dol do klasy PLK. Srednia wazona, nie maksimum:
predkosc szlakowa odcinka to wartosc reprezentatywna dla calej jego dlugosci,
a nie chwilowe maksimum na krotkim fragmencie.

LICZBA TOROW
Wykaz 2.1 podaje predkosci osobno dla toru N (nieparzysty) i P (parzysty).
Liczba roznych oznaczen torow wystepujacych na zakresie odcinka = liczba torow
szlakowych. Odcinek z wpisami tylko dla toru N jest jednotorowy; z wpisami
N i P — dwutorowy.

ZACHOWANIE WARTOSCI MODELOWYCH
Zgodnie z ustaleniem: vmax z modelu fizycznego (krok 5) zachowujemy w polu
vmax_model obok vmax_plk_*. Pozwala to w pracy porownac trafnosc modelu
z danymi zrodlowymi.
"""
import json, os, csv, unicodedata, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")
KLASY_V = [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 160, 200]


def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = s.replace("glowna", "gl").replace("gl.", "gl")
    s = s.replace(".", " ").replace("-", " ")
    return " ".join(s.split())


def norm_variants(name):
    n = norm(name)
    out = [n]
    if n.endswith(" g"):
        out.append(n[:-2] + " gl")
        out.append(n[:-2] + " gowna")   # GTFS "Gł." vs PLK "Główna"
    return out


def przeciecie(a0, a1, b0, b1):
    lo, hi = max(a0, b0), min(a1, b1)
    return max(0.0, hi - lo)


def do_klasy(v):
    if v is None:
        return None
    k = [x for x in KLASY_V if x <= v + 1e-6]
    return k[-1] if k else KLASY_V[0]


def main():
    with open(os.path.join(WORK, "plk.json"), encoding="utf-8") as f:
        plk = json.load(f)
    with open(os.path.join(WORK, "segments_vmax.json"), encoding="utf-8") as f:
        segs = json.load(f)
    with open(os.path.join(WORK, "graph_clean.json"), encoding="utf-8") as f:
        nodes = json.load(f)["nodes"]
    with open(os.path.join(WORK, "selected.json"), encoding="utf-8") as f:
        wybrane = set(json.load(f)["selected"])

    post = plk["posterunki"]
    predk = plk["predkosci"]
    klasy = plk["klasy"]
    by_line = plk["posterunki_by_line"]

    # nazwa wezla -> {linia: km}
    def linie_km(name):
        for v in norm_variants(name):
            if v in post:
                return {p["linia"]: p["km"] for p in post[v]}, \
                       {p["linia"]: p for p in post[v]}
        return {}, {}

    name_of = {sid: nodes[sid]["name"] for sid in nodes}
    # nazwa -> {linia: km} dla WSZYSTKICH punktow (nie tylko wybranych),
    # bo punkty posrednie odcinka (via) tez trzeba zlokalizowac na liniach
    all_km = {}
    for name in {name_of[s] for s in nodes}:
        for v in norm_variants(name):
            if v in post:
                all_km[name] = {p["linia"]: p["km"] for p in post[v]}
                break

    # id posrednich punktow (via) — sel.segments zawiera via_ids
    id_of_name = {}
    for sid, n in nodes.items():
        id_of_name.setdefault(n["name"], sid)

    def wspolna_linia(nA, nB, dlugosc):
        """Zwraca [(linia, km0, km1), ...] dla kroku A->B.

        Najpierw probuje linii wspolnej bezposrednio. Gdy A i B nie maja wspolnej
        linii (styk lezy w punkcie posrednim nie bedacym moim wezlem), szuka
        punktu P wystepujacego na linii A oraz na linii B, dla ktorego
        km(A..P)+km(P..B) jest zblizone do dlugosci kroku — i zwraca dwa
        pod-kroki. Odpowiada to sytuacji, gdy odcinek biegnie przez wezel
        rozjazdowy pominiety przy selekcji.
        """
        la, lb = all_km.get(nA, {}), all_km.get(nB, {})
        wsp = set(la) & set(lb)
        best = None
        for lin in wsp:
            lo, hi = sorted((la[lin], lb[lin]))
            odch = abs((hi - lo) - dlugosc)
            if best is None or odch < best[-1]:
                best = [(lin, lo, hi), odch]
        if best and best[-1] <= 4.0:
            return [best[0]]

        # dopasowanie dwuetapowe przez punkt styku
        best2 = None
        for linA, kmA in la.items():
            for (kmP, nP, typP) in by_line.get(linA, []):
                if nP not in all_km:
                    continue
                lbP = all_km[nP]
                for linB in set(lbP) & set(lb):
                    kmB = lb[linB]
                    d1 = abs(kmP - kmA)
                    d2 = abs(lbP[linB] - kmB)
                    odch = abs((d1 + d2) - dlugosc)
                    if d1 + d2 > 0 and (best2 is None or odch < best2[-1]):
                        best2 = [[(linA, min(kmA, kmP), max(kmA, kmP)),
                                  (linB, min(lbP[linB], kmB), max(lbP[linB], kmB))],
                                 odch]
        if best2 and best2[-1] <= 4.0:
            return best2[0]
        return None

    def dane_odcinka(seg):
        """Sumuje vmax/klase/tory wzdluz calej trasy odcinka (z via).

        Trase dzielimy na elementarne kroki po punktach posrednich. Dla kazdego
        kroku znajdujemy wspolna linie i jej zakres km, po czym czytamy dane
        z wykazow. Wielkosci lączymy: predkosci — srednia wazona dlugoscia
        kroku, tory — maksimum, klasa — dominujaca dlugoscia.
        """
        trasa_nazwy = [seg["a_name"]] + list(seg["via"]) + [seg["b_name"]]
        kroki = []
        for i in range(len(trasa_nazwy) - 1):
            nA, nB = trasa_nazwy[i], trasa_nazwy[i + 1]
            wl = wspolna_linia(nA, nB, seg["len_km"] / (len(trasa_nazwy) - 1))
            if wl:
                kroki.extend(wl)      # wl to lista pod-krokow
        if not kroki:
            return None
        # akumulacja
        akum = {f"{k}_{t}": [0.0, 0.0] for k in ("ezt", "wagon", "towar")
                for t in ("N", "P")}
        tory_all = set()
        klasa_w = collections.Counter()
        linie_uzyte = []
        for lin, km0, km1 in kroki:
            linie_uzyte.append(lin)
            for e in predk.get(lin, []):
                w = przeciecie(km0, km1, e["km0"], e["km1"])
                if w <= 0:
                    continue
                tory_all.add(e["tor"])
                for kat in ("ezt", "wagon", "towar"):
                    if e.get(kat) is not None:
                        akum[f"{kat}_{e['tor']}"][0] += e[kat] * w
                        akum[f"{kat}_{e['tor']}"][1] += w
            for e in klasy.get(lin, []):
                w = przeciecie(km0, km1, e["km0"], e["km1"])
                if w > 0:
                    klasa_w[e["klasa"]] += w
        vmax = {}
        for key, (num, den) in akum.items():
            if den > 0:
                vmax[key] = do_klasy(num / den)
        klasa = klasa_w.most_common(1)[0][0] if klasa_w else None
        return {"vmax": vmax, "tory": tory_all, "klasa": klasa,
                "linie": sorted(set(linie_uzyte))}

    n_ok, n_fail = 0, 0
    for s in segs:
        s["vmax_model"] = s.get("vmax")     # zachowanie wartosci modelowej
        d = dane_odcinka(s)
        if not d or not d["vmax"]:
            s["plk_line"] = None
            s["vmax_confidence"] = "derived"
            n_fail += 1
            continue
        vm = d["vmax"]

        def pick(kat):
            return vm.get(f"{kat}_N") or vm.get(f"{kat}_P")
        s["plk_line"] = ";".join(d["linie"])
        s["vmax_ezt"] = pick("ezt")
        s["vmax_wagon"] = pick("wagon")
        s["vmax_towar"] = pick("towar")
        s["vmax"] = s["vmax_ezt"] or s["vmax_wagon"] or s["vmax_model"]
        s["rail_tracks"] = len(d["tory"]) if d["tory"] else None
        s["plk_klasa"] = d["klasa"]
        s["vmax_source"] = "PLK_zal_2.1"
        s["vmax_confidence"] = "measured" if s["vmax_ezt"] else "derived"
        s["rail_tracks_source"] = "PLK_zal_2.1 (tory N/P)"
        n_ok += 1

    print(f"Odcinkow: {len(segs)}  dopasowanych do PLK: {n_ok}  bez dopasowania: {n_fail}")

    # jakosc: porownanie model vs PLK
    porown = [(s["vmax_model"], s["vmax_ezt"], s)
              for s in segs if s.get("vmax_ezt")]
    if porown:
        diffs = [a - b for a, b, _ in porown]
        import statistics
        print(f"\nPorownanie vmax_model vs vmax_PLK (EZT) na {len(porown)} odcinkach:")
        print(f"  sredni blad modelu   : {statistics.mean(diffs):+.1f} km/h")
        print(f"  mediana |bledu|      : {statistics.median([abs(d) for d in diffs]):.1f} km/h")
        print(f"  odchyl. std bledu    : {statistics.pstdev(diffs):.1f} km/h")
        zgodne = sum(1 for d in diffs if abs(d) <= 20)
        print(f"  w zakresie +/-20 km/h: {zgodne}/{len(porown)} "
              f"({100*zgodne/len(porown):.0f}%)")
        print("\n  Najwieksze rozbieznosci:")
        for a, b, s in sorted(porown, key=lambda x: -abs(x[0]-x[1]))[:8]:
            print(f"    {s['a_name']:22} - {s['b_name']:22} "
                  f"model={a:3} PLK={b:3} (l.{s['plk_line']})")

    rt = collections.Counter(s.get("rail_tracks") for s in segs)
    print(f"\nLiczba torow (rail_tracks): {dict(rt)}")
    kl = collections.Counter(s.get("plk_klasa") for s in segs if s.get("plk_klasa"))
    print(f"Klasy odcinkow: {dict(kl)}")

    with open(os.path.join(WORK, "segments_plk.json"), "w", encoding="utf-8") as f:
        json.dump(segs, f, ensure_ascii=False, indent=1)
    print("\n-> work/segments_plk.json")


if __name__ == "__main__":
    main()
