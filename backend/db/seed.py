import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = f"bolt://{os.getenv('MEMGRAPH_HOST', 'memgraph-db')}:{os.getenv('MEMGRAPH_PORT', '7687')}"
AUTH = (os.getenv("MEMGRAPH_USER", ""), os.getenv("MEMGRAPH_PASSWORD", ""))

CONSTRAINTS = [
    "CREATE CONSTRAINT ON (s:Station) ASSERT s.id IS UNIQUE",
    "CREATE CONSTRAINT ON (t:Train) ASSERT t.id IS UNIQUE",
    "CREATE CONSTRAINT ON (e:RailEvent) ASSERT e.id IS UNIQUE",
]

# Konurbacja katowicka (oryginalny rdzeń sieci) + rozszerzenie o resztę
# województwa śląskiego: korytarz częstochowski (linia 1), Zagłębie Dąbrowskie,
# korytarz rybnicko-raciborski (linia 140), Podbeskidzie (linia 139) i dogęszczenie GOP.
STATIONS = """
CREATE (:Station {id:'KAT', name:'Katowice', lat:50.2576, lon:19.0175,
  type:'węzeł', platforms:6, tracks:14, daily_trains:450}),
(:Station {id:'GLI', name:'Gliwice', lat:50.2977, lon:18.6714,
  type:'węzeł', platforms:5, tracks:12, daily_trains:320}),
(:Station {id:'ZAB', name:'Zabrze', lat:50.3058, lon:18.7776,
  type:'przelotowa', platforms:3, tracks:6, daily_trains:180}),
(:Station {id:'CHO', name:'Chorzów Batory', lat:50.2936, lon:18.9419,
  type:'przelotowa', platforms:2, tracks:5, daily_trains:120}),
(:Station {id:'SOS', name:'Sosnowiec Główny', lat:50.2748, lon:19.1231,
  type:'węzeł', platforms:4, tracks:9, daily_trains:280}),
(:Station {id:'DAB', name:'Dąbrowa Górnicza', lat:50.3259, lon:19.1847,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:90}),
(:Station {id:'BYT', name:'Bytom', lat:50.3474, lon:18.9350,
  type:'przelotowa', platforms:3, tracks:6, daily_trains:150}),
(:Station {id:'RYB', name:'Rybnik', lat:50.0976, lon:18.5466,
  type:'końcowa', platforms:3, tracks:5, daily_trains:110}),
(:Station {id:'TYC', name:'Tychy', lat:50.1282, lon:18.9980,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:100}),
(:Station {id:'MYS', name:'Mysłowice', lat:50.2212, lon:19.1465,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:80}),
(:Station {id:'ZAW', name:'Zawiercie', lat:50.4881, lon:19.4189,
  type:'węzeł', platforms:3, tracks:6, daily_trains:95}),
(:Station {id:'MYK', name:'Myszków', lat:50.5773, lon:19.3283,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:60}),
(:Station {id:'CZE', name:'Częstochowa', lat:50.8118, lon:19.1203,
  type:'końcowa', platforms:5, tracks:10, daily_trains:210}),
(:Station {id:'CZL', name:'Czeladź', lat:50.3227, lon:19.0870,
  type:'przelotowa', platforms:2, tracks:3, daily_trains:50}),
(:Station {id:'BED', name:'Będzin', lat:50.3300, lon:19.1225,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:70}),
(:Station {id:'RAC', name:'Racibórz', lat:50.0925, lon:18.2202,
  type:'końcowa', platforms:3, tracks:6, daily_trains:90}),
(:Station {id:'WOD', name:'Wodzisław Śląski', lat:50.0064, lon:18.4614,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:65}),
(:Station {id:'JAS', name:'Jastrzębie-Zdrój', lat:49.9500, lon:18.5750,
  type:'końcowa', platforms:2, tracks:3, daily_trains:55}),
(:Station {id:'PSZ', name:'Pszczyna', lat:49.9773, lon:18.9553,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:75}),
(:Station {id:'CZD', name:'Czechowice-Dziedzice', lat:49.9138, lon:18.9613,
  type:'węzeł', platforms:3, tracks:6, daily_trains:100}),
(:Station {id:'BBI', name:'Bielsko-Biała', lat:49.8224, lon:19.0584,
  type:'węzeł', platforms:4, tracks:8, daily_trains:160}),
(:Station {id:'ZYW', name:'Żywiec', lat:49.6875, lon:19.1900,
  type:'końcowa', platforms:2, tracks:4, daily_trains:70}),
(:Station {id:'CIE', name:'Cieszyn', lat:49.7500, lon:18.6300,
  type:'końcowa', platforms:2, tracks:3, daily_trains:60}),
(:Station {id:'RUD', name:'Ruda Śląska', lat:50.2560, lon:18.8560,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:85}),
(:Station {id:'SWI', name:'Świętochłowice', lat:50.2977, lon:18.9089,
  type:'przelotowa', platforms:2, tracks:3, daily_trains:55}),
(:Station {id:'SIE', name:'Siemianowice Śląskie', lat:50.3006, lon:19.0294,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:70}),
(:Station {id:'PIE', name:'Piekary Śląskie', lat:50.3819, lon:18.9453,
  type:'końcowa', platforms:2, tracks:3, daily_trains:60}),
(:Station {id:'MIK', name:'Mikołów', lat:50.1667, lon:18.9017,
  type:'przelotowa', platforms:2, tracks:4, daily_trains:65}),
(:Station {id:'KNU', name:'Knurów', lat:50.2186, lon:18.6644,
  type:'przelotowa', platforms:2, tracks:3, daily_trains:55}),
(:Station {id:'JAW', name:'Jaworzno', lat:50.2044, lon:19.2758,
  type:'końcowa', platforms:2, tracks:4, daily_trains:75})
"""

TRACKS = [
    # --- rdzeń konurbacji katowickiej (oryginalne 12 odcinków) ---
    ("GLI", "ZAB", 137, 9.8,  120, 2, 7),
    ("ZAB", "CHO", 137, 12.1, 120, 2, 9),
    ("CHO", "KAT", 137, 8.4,  120, 2, 6),
    ("KAT", "SOS", 1,   7.2,  160, 2, 5),
    ("SOS", "DAB", 1,   8.9,  120, 2, 7),
    ("KAT", "MYS", 179, 9.5,  100, 2, 9),
    ("MYS", "SOS", 179, 5.3,  100, 2, 5),
    ("KAT", "BYT", 164, 11.4, 80,  1, 14),
    ("BYT", "ZAB", 164, 10.9, 80,  1, 13),
    ("GLI", "RYB", 140, 28.6, 100, 2, 28),
    ("KAT", "TYC", 139, 16.2, 80,  1, 19),
    ("SOS", "CHO", 161, 13.8, 80,  1, 17),
    # --- korytarz częstochowski (linia 1 przedłużona na północ) ---
    ("DAB", "ZAW", 1,   28.2, 140, 2, 14),
    ("ZAW", "MYK", 1,   15.4, 140, 2, 8),
    ("MYK", "CZE", 1,   32.8, 140, 2, 16),
    # --- Zagłębie Dąbrowskie (druga, wolniejsza trasa SOS<->DAB) ---
    ("SOS", "CZL", 178, 6.3,  90,  1, 6),
    ("CZL", "BED", 178, 4.4,  90,  1, 5),
    ("BED", "DAB", 178, 4.0,  90,  1, 4),
    # --- korytarz rybnicko-raciborski (linia 140 przedłużona) ---
    ("RYB", "RAC", 140, 28.0, 100, 2, 19),
    ("RYB", "WOD", 158, 13.8, 90,  1, 11),
    ("WOD", "JAS", 158, 11.2, 90,  1, 9),
    # --- Podbeskidzie (linia 139 przedłużona) — najdłuższy jednotorowy łańcuch w sieci ---
    ("TYC", "PSZ", 139, 19.6, 90,  1, 15),
    ("PSZ", "CZD", 139, 8.2,  90,  1, 7),
    ("CZD", "BBI", 139, 14.6, 90,  1, 11),
    ("BBI", "ZYW", 139, 23.3, 80,  1, 19),
    ("CZD", "CIE", 190, 34.0, 80,  1, 28),
    # --- dogęszczenie GOP: alternatywy wokół istniejących jednotorówek ---
    ("ZAB", "RUD", 686, 8.7,  100, 2, 6),
    ("RUD", "CHO", 686, 8.3,  100, 2, 6),
    ("CHO", "SWI", 686, 2.5,  90,  2, 3),
    ("SWI", "BYT", 686, 6.6,  100, 2, 5),
    ("KAT", "SIE", 686, 5.5,  90,  2, 4),
    ("SIE", "BYT", 686, 9.8,  90,  2, 7),
    ("BYT", "PIE", 686, 4.4,  80,  1, 5),
    ("TYC", "MIK", 691, 9.5,  90,  2, 8),
    ("MIK", "GLI", 691, 25.0, 90,  1, 17),
    ("GLI", "KNU", 691, 10.1, 100, 2, 7),
    ("KNU", "RYB", 691, 18.2, 100, 2, 13),
    # --- wschód ---
    ("MYS", "JAW", 662, 10.7, 90,  1, 9),
]

# segment_id jest wspólne dla obu kierunków tego samego odcinka, dzięki czemu
# blokadę/ograniczenie zakłada się na wybranym kierunku niezależnie od drugiego.
# restricted_vmax/active_event_id startują jako null — wypełnia je silnik zdarzeń
# losowych (app/services/event_service.py) w trakcie działania symulacji.
TRACK_QUERY = """
MATCH (a:Station {id:$from}), (b:Station {id:$to})
CREATE (a)-[:TRACK {segment_id:$seg, line:$line, dist_km:$dist, vmax:$vmax,
       rail_tracks:$rail, travel_min:$min, status:'active',
       restricted_vmax: null, active_event_id: null}]->(b),
       (b)-[:TRACK {segment_id:$seg, line:$line, dist_km:$dist, vmax:$vmax,
       rail_tracks:$rail, travel_min:$min, status:'active',
       restricted_vmax: null, active_event_id: null}]->(a)
"""

# Każdy pociąg ma stałą parę stacji (origin/destination), między którymi kursuje
# tam-z-powrotem. Startują ze status='waiting' — pierwszy tick silnika symulacji
# sam wylicza im trasę A* i rusza je (app/services/train_service.dispatch_or_wait).
TRAINS = [
    # (id, name, type, origin, destination, vmax, priority, mass_tonnes, length_m, accel, decel)
    ("IC101",  "Beskid",      "IC",       "KAT", "BBI", 160, 3, 420,  200, 0.6, 0.9),
    ("IC102",  "Jasnogórski", "IC",       "KAT", "CZE", 160, 3, 420,  200, 0.6, 0.9),
    ("IC103",  "Odra",        "IC",       "GLI", "RAC", 160, 3, 400,  190, 0.6, 0.9),
    ("IC104",  "Ondraszek",   "IC",       "RYB", "KAT", 160, 3, 410,  195, 0.6, 0.9),
    ("REG201", "REG 201",     "REGIONAL", "SOS", "BED", 120, 2, 160,  120, 0.5, 0.8),
    ("REG202", "REG 202",     "REGIONAL", "KAT", "MYS", 120, 2, 150,  110, 0.5, 0.8),
    ("REG203", "REG 203",     "REGIONAL", "BYT", "PIE", 120, 2, 155,  115, 0.5, 0.8),
    ("REG204", "REG 204",     "REGIONAL", "GLI", "KNU", 120, 2, 150,  110, 0.5, 0.8),
    ("REG205", "REG 205",     "REGIONAL", "TYC", "MIK", 120, 2, 145,  105, 0.5, 0.8),
    ("REG206", "REG 206",     "REGIONAL", "CZD", "CIE", 120, 2, 170,  130, 0.5, 0.8),
    ("REG207", "REG 207",     "REGIONAL", "RYB", "WOD", 120, 2, 150,  110, 0.5, 0.8),
    ("REG208", "REG 208",     "REGIONAL", "WOD", "JAS", 120, 2, 150,  110, 0.5, 0.8),
    ("REG209", "REG 209",     "REGIONAL", "ZAW", "CZL", 120, 2, 160,  120, 0.5, 0.8),
    ("TW301",  "Cargo 301",   "FREIGHT",  "BYT", "RYB", 80,  1, 1200, 450, 0.3, 0.5),
    ("TW302",  "Cargo 302",   "FREIGHT",  "DAB", "ZAB", 80,  1, 1100, 420, 0.3, 0.5),
    ("TW303",  "Cargo 303",   "FREIGHT",  "KAT", "JAW", 80,  1, 900,  380, 0.3, 0.5),
]

TRAIN_QUERY = """
CREATE (:Train {
    id: $id, name: $name, type: $type,
    origin_station_id: $origin, destination_station_id: $destination, direction: 'outbound',
    current_station_id: $origin, next_station_id: null, current_segment_id: null,
    progress: 0.0, status: 'waiting',
    route_station_ids: [], route_segment_ids: [], route_index: 0,
    vmax: $vmax, priority: $priority, mass_tonnes: $mass, length_m: $length,
    accel: $accel, decel: $decel,
    dwell_until: null, delayed_by_event_id: null, updated_at: 0.0
})
"""


def load_data(session):
    # 0. Czyszczenie i constrainty (idempotentność)
    session.run("MATCH (n) DETACH DELETE n")
    for constraint in CONSTRAINTS:
        try:
            session.run(constraint)
        except Exception:
            pass  # constraint już istnieje
    print("✓ Baza wyczyszczona, constrainty gotowe")

    # 1. Węzły stacji
    session.run(STATIONS)
    print(f"✓ Stacje utworzone ({STATIONS.count('(:Station')})")

    # 2. Relacje torów — każda osobno (MATCH wymaga istniejących węzłów).
    #    enumerate nadaje obu kierunkom to samo segment_id (SEG01..SEG38).
    for idx, (frm, to, line, dist, vmax, rail, mins) in enumerate(TRACKS, start=1):
        seg_id = f"SEG{idx:02d}"
        session.run(TRACK_QUERY, **{
            "seg": seg_id,
            "from": frm, "to": to, "line": line,
            "dist": dist, "vmax": vmax, "rail": rail, "min": mins
        })
    print(f"✓ Tory utworzone ({len(TRACKS)} odcinków)")

    # 3. Pociągi
    for (train_id, name, ttype, origin, destination, vmax, priority, mass, length, accel, decel) in TRAINS:
        session.run(TRAIN_QUERY, id=train_id, name=name, type=ttype, origin=origin,
                    destination=destination, vmax=vmax, priority=priority, mass=mass,
                    length=length, accel=accel, decel=decel)
    print(f"✓ Pociągi utworzone ({len(TRAINS)})")


if __name__ == "__main__":
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            load_data(session)
    print("✅ Dane wgrane pomyślnie!")
