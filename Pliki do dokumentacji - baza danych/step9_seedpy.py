#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KROK 9 — Generowanie nowego backend/db/seed.py w strukturze oryginalu zespolu.

Zachowuje DOKLADNIE format istniejacego seed.py:
  - STATIONS jako jeden string Cypher (:Station {...})
  - TRACKS jako lista krotek (from, to, line, dist_km, vmax, rail_tracks, travel_min)
  - TRAINS jako lista krotek z para origin/destination
  - te same CONSTRAINTS, TRACK_QUERY, TRAIN_QUERY, load_data(), __main__

Podmienia tylko DANE na rzeczywiste (57 stacji, 71 odcinkow, 52 pociagi)
oraz dodaje pola nadmiarowe z PLK (vmax_ezt/wagon/towar, plk_klasa, platforms,
tracks z 2.18 itd.) do wezlow Station i relacji TRACK — jako pola dodatkowe,
nie zmieniajac istniejacego mechanizmu.
"""
import csv, json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "out")


def rd(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def esc(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'")


def i(v, default=0):
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return default


def f(v, default=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def main():
    stations = rd("stations.csv")
    segments = rd("segments.csv")
    services = rd("services.csv")

    # ---- STATIONS jako string Cypher -----------------------------------
    st_lines = []
    for s in stations:
        # pola nadmiarowe z PLK dodane obok oryginalnych
        extra = (f"type_plk:'{esc(s['type_plk'])}', "
                 f"plk_lines:'{esc(s['plk_lines'])}', "
                 f"has_platform:'{esc(s['has_platform'])}', "
                 f"platform_manager:'{esc(s['platform_manager'])}', "
                 f"platforms_confidence:'{esc(s['platforms_confidence'])}', "
                 f"type_source:'{esc(s['type_source'])}', "
                 f"gtfs_stop_id:'{esc(s['gtfs_stop_id'])}', "
                 f"voivodeship:'{esc(s['voivodeship'])}', "
                 f"data_source:'gtfs+plk'")
        st_lines.append(
            f"(:Station {{id:'{esc(s['id'])}', name:'{esc(s['name'])}', "
            f"lat:{f(s['lat'])}, lon:{f(s['lon'])}, "
            f"type:'{esc(s['type'])}', platforms:{i(s['platforms'] or s['platforms_est'])}, "
            f"tracks:{i(s['tracks'] or s['tracks_est'])}, daily_trains:{i(s['daily_trains'])}, "
            f"{extra}}})"
        )
    stations_cypher = "CREATE " + ",\n".join(st_lines)

    # ---- TRACKS jako lista krotek --------------------------------------
    # format oryginalu: (from, to, line, dist_km, vmax, rail_tracks, travel_min)
    # rozszerzamy o pola PLK jako kolejne elementy krotki (wstecznie zgodne —
    # load_data rozpakowuje pierwsze 7, reszta idzie do zapytania osobno)
    track_rows = []
    for s in segments:
        # glowny numer linii: pierwszy z plk_line, fallback 0
        plk = (s["plk_line"] or "").split(";")[0]
        line = i(plk, 0)
        vmax = i(s["vmax"], 80)
        rail = i(s["rail_tracks"], 1) or 1
        mins = i(round(f(s["travel_min"])), 1) or 1
        track_rows.append({
            "frm": s["a"], "to": s["b"], "line": line,
            "dist": round(f(s["dist_km"]), 3), "vmax": vmax,
            "rail": rail, "min": mins,
            # pola nadmiarowe PLK
            "vmax_ezt": i(s["vmax_ezt"]) if s["vmax_ezt"] else "None",
            "vmax_wagon": i(s["vmax_wagon"]) if s["vmax_wagon"] else "None",
            "vmax_towar": i(s["vmax_towar"]) if s["vmax_towar"] else "None",
            "klasa": s["plk_klasa"] or "",
            "plk_line": s["plk_line"] or "",
            "conf": s["vmax_confidence"] or "",
            "lines_gtfs": s["lines_gtfs"] or "",
            "rtconf": s["rail_tracks_confidence"] or "",
        })

    def krotka(t):
        return (f'    ("{t["frm"]}", "{t["to"]}", {t["line"]}, {t["dist"]}, '
                f'{t["vmax"]}, {t["rail"]}, {t["min"]}, '
                f'{t["vmax_ezt"]}, {t["vmax_wagon"]}, {t["vmax_towar"]}, '
                f'"{esc(t["klasa"])}", "{esc(t["plk_line"])}", "{esc(t["conf"])}", '
                f'"{esc(t["lines_gtfs"])}", "{esc(t["rtconf"])}"),')

    tracks_block = "\n".join(krotka(t) for t in track_rows)

    # ---- TRAINS jako lista krotek --------------------------------------
    train_rows = []
    for s in services:
        route = s["route"].split(";")
        origin, dest = route[0], route[-1]
        train_rows.append({
            "id": s["id"], "name": s["name"], "type": s["type"],
            "origin": origin, "dest": dest,
            "vmax": i(s["vmax"], 120), "prio": i(s["priority"], 2),
            "mass": i(s["mass_tonnes"], 150), "len": i(s["length_m"], 120),
            "accel": f(s["accel"], 0.5), "decel": f(s["decel"], 0.8),
            "operator": s["operator"], "line_code": s["line_code"],
            "src": s["data_source"], "conf": s["confidence"],
        })

    def train_krotka(t):
        return (f'    ("{t["id"]}", "{esc(t["name"])}", "{t["type"]}", '
                f'"{t["origin"]}", "{t["dest"]}", {t["vmax"]}, {t["prio"]}, '
                f'{t["mass"]}, {t["len"]}, {t["accel"]}, {t["decel"]}, '
                f'"{esc(t["operator"])}", "{esc(t["line_code"])}", '
                f'"{esc(t["src"])}", "{t["conf"]}"),')

    trains_block = "\n".join(train_krotka(t) for t in train_rows)

    # ---- skladanie pliku ------------------------------------------------
    py = f'''import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = f"bolt://{{os.getenv('MEMGRAPH_HOST', 'memgraph-db')}}:{{os.getenv('MEMGRAPH_PORT', '7687')}}"
AUTH = (os.getenv("MEMGRAPH_USER", ""), os.getenv("MEMGRAPH_PASSWORD", ""))

CONSTRAINTS = [
    "CREATE CONSTRAINT ON (s:Station) ASSERT s.id IS UNIQUE",
    "CREATE CONSTRAINT ON (t:Train) ASSERT t.id IS UNIQUE",
    "CREATE CONSTRAINT ON (e:RailEvent) ASSERT e.id IS UNIQUE",
]

# =====================================================================
# BAZA DANYCH SIECI KOLEJOWEJ WOJEWODZTWA SLASKIEGO
# Zrodla: GTFS Koleje Slaskie (feed 2026.166) + Regulamin sieci PKP PLK
#         2025/2026 (zal. 1, 2.1, 2.4, 2.6, 2.18, stan 30.08.2026).
# Wygenerowano automatycznie — metodyka w "Pliki do dokumentacji - baza
# danych/DOKUMENTACJA_BAZY.md". NIE EDYTOWAC RECZNIE.
#
# 57 stacji, 71 odcinkow, 52 pociagi. Pola nadmiarowe z PLK (type_plk,
# plk_lines, vmax_ezt/wagon/towar, plk_klasa) dodane obok pol oryginalnych;
# silnik moze je ignorowac — nie zmieniaja jego dzialania.
# =====================================================================
STATIONS = """
{stations_cypher}
"""

# Format krotki (wstecznie zgodny z oryginalem — pierwsze 7 pol bez zmian):
#   (from, to, line, dist_km, vmax, rail_tracks, travel_min,
#    vmax_ezt, vmax_wagon, vmax_towar, plk_klasa, plk_line, vmax_confidence,
#    lines_gtfs, rail_tracks_confidence)
# Pola 8-13 pochodza z wykazow PLK (predkosci wg kategorii, klasa odcinka).
# line = glowny numer linii PLK (0 dla 5 odcinkow bez jednoznacznego dopasowania).
TRACKS = [
{tracks_block}
]

# segment_id wspolne dla obu kierunkow odcinka (blokada kierunkowa niezalezna).
# restricted_vmax/active_event_id startuja jako null — wypelnia je silnik zdarzen.
# Pola PLK (vmax_ezt itd.) dopisane do relacji jako nadmiarowe.
TRACK_QUERY = """
MATCH (a:Station {{id:$from}}), (b:Station {{id:$to}})
CREATE (a)-[:TRACK {{segment_id:$seg, line:$line, dist_km:$dist, vmax:$vmax,
       rail_tracks:$rail, travel_min:$min, status:'active',
       restricted_vmax: null, active_event_id: null,
       vmax_ezt:$vmax_ezt, vmax_wagon:$vmax_wagon, vmax_towar:$vmax_towar,
       plk_klasa:$klasa, plk_line:$plk_line, lines_gtfs:$lines_gtfs,
       dist_source:'gtfs_shapes (rzutowanie monotoniczne)', dist_confidence:'measured',
       vmax_source:'PLK_zal_2.1', vmax_confidence:$conf,
       rail_tracks_confidence:$rtconf, data_confidence:$conf}}]->(b),
       (b)-[:TRACK {{segment_id:$seg, line:$line, dist_km:$dist, vmax:$vmax,
       rail_tracks:$rail, travel_min:$min, status:'active',
       restricted_vmax: null, active_event_id: null,
       vmax_ezt:$vmax_ezt, vmax_wagon:$vmax_wagon, vmax_towar:$vmax_towar,
       plk_klasa:$klasa, plk_line:$plk_line, lines_gtfs:$lines_gtfs,
       dist_source:'gtfs_shapes (rzutowanie monotoniczne)', dist_confidence:'measured',
       vmax_source:'PLK_zal_2.1', vmax_confidence:$conf,
       rail_tracks_confidence:$rtconf, data_confidence:$conf}}]->(a)
"""

# Kazdy pociag ma stala pare stacji (origin/destination). Startuje ze
# status='waiting' — pierwszy tick silnika sam wylicza trase A* i rusza go
# (app/services/train_service.dispatch_or_wait). route_station_ids puste
# CELOWO — nie wpisujemy trasy, silnik ja liczy.
# Format: (id, name, type, origin, destination, vmax, priority, mass_tonnes,
#          length_m, accel, decel, operator, line_code, data_source, data_confidence)
TRAINS = [
{trains_block}
]

TRAIN_QUERY = """
CREATE (:Train {{
    id: $id, name: $name, type: $type,
    origin_station_id: $origin, destination_station_id: $destination, direction: 'outbound',
    current_station_id: $origin, next_station_id: null, current_segment_id: null,
    progress: 0.0, status: 'waiting',
    route_station_ids: [], route_segment_ids: [], route_index: 0,
    vmax: $vmax, priority: $priority, mass_tonnes: $mass, length_m: $length,
    accel: $accel, decel: $decel,
    dwell_until: null, delayed_by_event_id: null, updated_at: 0.0,
    operator: $operator, line_code: $line_code,
    data_source: $data_source, data_confidence: $conf
}})
"""


def load_data(session):
    # 0. Czyszczenie i constrainty (idempotentnosc)
    session.run("MATCH (n) DETACH DELETE n")
    for constraint in CONSTRAINTS:
        try:
            session.run(constraint)
        except Exception:
            pass  # constraint juz istnieje
    print("\u2713 Baza wyczyszczona, constrainty gotowe")

    # 1. Wezly stacji
    session.run(STATIONS)
    print(f"\u2713 Stacje utworzone ({{STATIONS.count('(:Station')}})")

    # 2. Relacje torow — kazda osobno (MATCH wymaga istniejacych wezlow).
    #    enumerate nadaje obu kierunkom to samo segment_id (SEG01..SEG71).
    for idx, tr in enumerate(TRACKS, start=1):
        (frm, to, line, dist, vmax, rail, mins,
         vmax_ezt, vmax_wagon, vmax_towar, klasa, plk_line, conf,
         lines_gtfs, rtconf) = tr
        seg_id = f"SEG{{idx:02d}}"
        session.run(TRACK_QUERY, **{{
            "seg": seg_id,
            "from": frm, "to": to, "line": line,
            "dist": dist, "vmax": vmax, "rail": rail, "min": mins,
            "vmax_ezt": vmax_ezt, "vmax_wagon": vmax_wagon, "vmax_towar": vmax_towar,
            "klasa": klasa, "plk_line": plk_line, "conf": conf,
            "lines_gtfs": lines_gtfs, "rtconf": rtconf,
        }})
    print(f"\u2713 Tory utworzone ({{len(TRACKS)}} odcinkow)")

    # 3. Pociagi
    for tr in TRAINS:
        (train_id, name, ttype, origin, destination, vmax, priority, mass,
         length, accel, decel, operator, line_code, data_source, conf) = tr
        session.run(TRAIN_QUERY, id=train_id, name=name, type=ttype, origin=origin,
                    destination=destination, vmax=vmax, priority=priority, mass=mass,
                    length=length, accel=accel, decel=decel,
                    operator=operator, line_code=line_code,
                    data_source=data_source, conf=conf)
    print(f"\u2713 Pociagi utworzone ({{len(TRAINS)}})")


if __name__ == "__main__":
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            load_data(session)
    print("\u2705 Dane wgrane pomyslnie!")
'''

    with open(os.path.join(OUT, "seed.py"), "w", encoding="utf-8") as fh:
        fh.write(py)
    print(f"-> out/seed.py  ({len(py.splitlines())} linii)")
    print(f"   stacje: {len(stations)}, odcinki: {len(track_rows)}, pociagi: {len(train_rows)}")


if __name__ == "__main__":
    main()
