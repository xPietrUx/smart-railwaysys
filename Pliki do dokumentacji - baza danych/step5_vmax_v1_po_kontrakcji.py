#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 5 — Wyznaczenie predkosci maksymalnej odcinka.

SYTUACJA ZRODLOWA
Wartosc autorytatywna dla vmax jest zalacznik 2.1 Regulaminu sieci PKP PLK
("Wykaz maksymalnych predkosci"). Nie byla ona dostepna przy budowie bazy, wiec
vmax wyznaczono POSREDNIO z rozkladu jazdy. Kazdy rekord ma z tego powodu
znacznik zrodla i wiarygodnosci; wartosci sa oznaczone jako "derived", a nie
"measured", i przy aktualizacji bazy powinny zostac zastapione danymi PLK.

DLACZEGO NIE WYSTARCZY PREDKOSC SREDNIA
Naiwne v = L/t daje predkosc handlowa (srednia), nie maksymalna. Pociag na
odcinku miedzy dwiema stacjami rusza z postoju, rozpedza sie, jedzie ze stala
predkoscia i hamuje do zatrzymania. Predkosc srednia jest zawsze nizsza od
maksymalnej, a roznica rosnie dla odcinkow krotkich — na 2 km odcinku predkosc
srednia bywa o polowe nizsza od rzeczywistej predkosci szlakowej.

MODEL
Przyjmujemy trapezowy profil predkosci (ruch jednostajnie przyspieszony,
jednostajny, jednostajnie opozniony):

    t  =  L/v  +  v/(2a)  +  v/(2b)

gdzie
    t — czas przejazdu miedzy zatrzymaniami [s]
    L — dlugosc odcinka [m]
    v — predkosc maksymalna osiagana na odcinku [m/s]
    a — przyspieszenie rozruchu [m/s^2]
    b — opoznienie hamowania sluzbowego [m/s^2]

Skladnik L/v to czas przy jezdzie ze stala predkoscia, a v/(2a) i v/(2b) to
straty czasu na rozruch i hamowanie (dla ruchu jednostajnie zmiennego droga
rozpedzania wynosi v^2/(2a), a strata czasu wzgledem jazdy ze stala predkoscia
to wlasnie v/(2a)).

ROZWIAZANIE WZGLEDEM v
Mnozac obustronnie przez v i porzadkujac:

    k = 1/(2a) + 1/(2b)
    k*v^2  -  t*v  +  L  =  0
    v = ( t - sqrt(t^2 - 4*k*L) ) / (2k)

Wybieramy pierwiastek mniejszy (znak minus), bo odpowiada on rozwiazaniu
fizycznemu — drugi pierwiastek daje predkosc, przy ktorej pociag nie zdazylby
wyhamowac. Gdy wyroznik t^2 - 4kL < 0, profil trapezowy jest niemozliwy:
odcinek jest zbyt krotki, by osiagnac predkosc ustalona (profil trojkatny).
Wtedy v wyznaczamy z warunku granicznego v = sqrt(t^2/(4k^2)) ... = t/(2k).

PARAMETRY
a = 0.6 m/s^2, b = 0.9 m/s^2 — wartosci przyjete dla elektrycznych zespolow
trakcyjnych ruchu regionalnego i zgodne z parametrami uzywanymi w silniku
symulacji (pola accel/decel w wezle Train).

CZAS t
Uzywamy 10. percentyla czasow przejazdu z rozkladu, nie mediany. Mediana zawiera
rezerwy rozkladowe (dodatki czasowe na niepunktualnosc), ktore zanizaja
wyliczona predkosc. 10. percentyl przybliza czas techniczny — najszybszy
realizowany przejazd.

ZAOKRAGLENIE
Wynik zaokraglamy w dol do najblizszej wartosci ze zbioru predkosci
konstrukcyjnych stosowanych w PKP PLK: {30,40,50,60,70,80,100,120,140,160}.
Zaokraglenie w DOL, bo predkosc wyliczona z rozkladu jest gorna estymata
predkosci faktycznie realizowanej.
"""
import json, math, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, "work")

A_ACC = 0.6      # m/s^2
B_DEC = 0.9      # m/s^2
KLASY = [30, 40, 50, 60, 70, 80, 100, 120, 140, 160]
VMAX_LIMIT = 160


def vmax_z_czasu(L_m, t_s, a=A_ACC, b=B_DEC):
    """Predkosc maksymalna [m/s] z modelu trapezowego."""
    k = 1.0 / (2 * a) + 1.0 / (2 * b)
    disc = t_s * t_s - 4 * k * L_m
    if disc < 0:
        # profil trojkatny — nie osiagnieto predkosci ustalonej
        return t_s / (2 * k), "trojkatny"
    v = (t_s - math.sqrt(disc)) / (2 * k)
    return v, "trapezowy"


def do_klasy(v_kmh):
    kand = [k for k in KLASY if k <= v_kmh]
    return kand[-1] if kand else KLASY[0]


def main():
    with open(os.path.join(WORK, "selected.json"), encoding="utf-8") as f:
        sel = json.load(f)
    segs = sel["segments"]

    n_tri = 0
    for s in segs:
        L_m = s["len_km"] * 1000.0
        t = s["t_p10_s"]
        if not t or t <= 0:
            s["vmax"] = 60
            s["vmax_source"] = "default"
            s["vmax_confidence"] = "assumed"
            s["v_sr_kmh"] = None
            continue
        v_ms, prof = vmax_z_czasu(L_m, t)
        if prof == "trojkatny":
            n_tri += 1
        v_kmh = v_ms * 3.6
        v_kmh = min(v_kmh, VMAX_LIMIT)
        s["v_srednia_kmh"] = round(s["len_km"] / (t / 3600.0), 1)
        s["v_model_kmh"] = round(v_kmh, 1)
        s["profil"] = prof
        s["vmax"] = do_klasy(v_kmh)
        s["vmax_source"] = "model_trapezowy_z_rozkladu"
        s["vmax_confidence"] = "derived"

    print(f"Odcinkow: {len(segs)}   profil trojkatny: {n_tri}")
    print("\nPorownanie predkosci sredniej i modelowej (10 najdluzszych):")
    print(f"{'odcinek':52}{'km':>7}{'t[s]':>7}{'v_sr':>7}{'v_mod':>7}{'vmax':>6}")
    for s in sorted(segs, key=lambda x: -x["len_km"])[:12]:
        nm = f"{s['a_name']} - {s['b_name']}"
        print(f"{nm:52}{s['len_km']:>7.2f}{s['t_p10_s'] or 0:>7}"
              f"{s.get('v_srednia_kmh') or 0:>7.1f}{s.get('v_model_kmh') or 0:>7.1f}"
              f"{s['vmax']:>6}")

    import collections
    c = collections.Counter(s["vmax"] for s in segs)
    print("\nRozklad przyznanych klas vmax:")
    for k in sorted(c):
        print(f"  {k:3} km/h : {c[k]:3} odcinkow")

    with open(os.path.join(WORK, "segments_vmax.json"), "w", encoding="utf-8") as f:
        json.dump(segs, f, ensure_ascii=False, indent=1)
    print("\n-> work/segments_vmax.json")


if __name__ == "__main__":
    main()
