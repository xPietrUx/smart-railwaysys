import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = f"bolt://{os.getenv('MEMGRAPH_HOST', 'memgraph-db')}:{os.getenv('MEMGRAPH_PORT', '7687')}"
AUTH = (os.getenv("MEMGRAPH_USER", ""), os.getenv("MEMGRAPH_PASSWORD", ""))

CONSTRAINTS = [
    "CREATE CONSTRAINT ON (s:Station) ASSERT s.id IS UNIQUE",
    "CREATE CONSTRAINT ON (t:Train) ASSERT t.id IS UNIQUE",
]

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
  type:'przelotowa', platforms:2, tracks:4, daily_trains:80})
"""

TRACKS = [
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
]

TRACK_QUERY = """
MATCH (a:Station {id:$from}), (b:Station {id:$to})
CREATE (a)-[:TRACK {line:$line, dist_km:$dist, vmax:$vmax,
       rail_tracks:$rail, travel_min:$min, status:'active'}]->(b),
       (b)-[:TRACK {line:$line, dist_km:$dist, vmax:$vmax,
       rail_tracks:$rail, travel_min:$min, status:'active'}]->(a)
"""

TRAINS = """
CREATE
(:Train {id:'IC3400',  name:'Górnik',   type:'IC',       priority:3,
  current_from:'GLI', current_to:'ZAB', progress:0.35,
  speed:110.0, vmax:160, mass_tonnes:420,  accel:0.6, decel:0.9,
  length_m:200, destination:'SOS', status:'moving'}),
(:Train {id:'REG8712', name:'REG 8712', type:'regional', priority:2,
  current_from:'KAT', current_to:'SOS', progress:0.0,
  speed:0.0,   vmax:120, mass_tonnes:180,  accel:0.5, decel:0.8,
  length_m:140, destination:'DAB', status:'waiting', depart_in_s:30}),
(:Train {id:'TW5501',  name:'TW 5501',  type:'freight',  priority:1,
  current_from:'BYT', current_to:'KAT', progress:0.6,
  speed:65.0,  vmax:80,  mass_tonnes:1200, accel:0.3, decel:0.5,
  length_m:450, destination:'TYC', status:'moving'}),
(:Train {id:'REG9003', name:'REG 9003', type:'regional', priority:2,
  current_from:'SOS', current_to:'CHO', progress:0.1,
  speed:40.0,  vmax:120, mass_tonnes:160,  accel:0.5, decel:0.8,
  length_m:120, destination:'GLI', status:'moving'})
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
    print("✓ Stacje utworzone")

    # 2. Relacje torów — każda osobno (MATCH wymaga istniejących węzłów)
    for frm, to, line, dist, vmax, rail, mins in TRACKS:
        session.run(TRACK_QUERY, **{
            "from": frm, "to": to, "line": line,
            "dist": dist, "vmax": vmax, "rail": rail, "min": mins
        })
    print("✓ Tory utworzone")

    # 3. Pociągi
    session.run(TRAINS)
    print("✓ Pociągi utworzone")


if __name__ == "__main__":
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            load_data(session)
    print("✅ Dane wgrane pomyślnie!")