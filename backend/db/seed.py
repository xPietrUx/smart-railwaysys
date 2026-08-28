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
CREATE (:Station {id:'BAL', name:'Balin', lat:50.17897, lon:19.383175, type:'przystanek osobowy publiczny', platforms:2, tracks:2, daily_trains:3, type_plk:'PO', plk_lines:'133', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'77537', voivodeship:'poza woj. (punkt graniczny)', data_source:'gtfs+plk'}),
(:Station {id:'BIG', name:'Bielsko-Biała Gł.', lat:49.83071, lon:19.045582, type:'stacja', platforms:4, tracks:6, daily_trains:44, type_plk:'ST', plk_lines:'117;139;190', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'76109', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'BOH', name:'Bohumin', lat:49.900745, lon:18.359324, type:'stacja', platforms:1, tracks:3, daily_trains:10, type_plk:'ST', plk_lines:'479;593', has_platform:'NIE', platform_manager:'', platforms_confidence:'derived', type_source:'PLK_zal_2.6', gtfs_stop_id:'179223', voivodeship:'poza woj. (punkt graniczny)', data_source:'gtfs+plk'}),
(:Station {id:'BYT', name:'Bytom', lat:50.34315, lon:18.915182, type:'stacja', platforms:3, tracks:6, daily_trains:106, type_plk:'ST', plk_lines:'131;132', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'72306', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'CHA', name:'Chałupki', lat:49.925488, lon:18.311747, type:'stacja', platforms:2, tracks:4, daily_trains:46, type_plk:'ST', plk_lines:'151;158;479;592;679', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'67900', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'CHB', name:'Chorzów Batory', lat:50.27835, lon:18.944881, type:'stacja', platforms:2, tracks:4, daily_trains:148, type_plk:'ST', plk_lines:'131;137;164;651;708;713;895', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'73106', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'CHY', name:'Chybie', lat:49.893017, lon:18.811628, type:'stacja', platforms:2, tracks:4, daily_trains:10, type_plk:'ST', plk_lines:'150;157;93', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75796', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'CHM', name:'Chybie Mnich', lat:49.88754, lon:18.820902, type:'przystanek osobowy publiczny', platforms:1, tracks:1, daily_trains:20, type_plk:'PO', plk_lines:'157', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75820', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'CIE', name:'Cieszyn', lat:49.750988, lon:18.637894, type:'stacja', platforms:2, tracks:3, daily_trains:36, type_plk:'ST', plk_lines:'190;480;695;90', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75655', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'CZ2', name:'Czechowice-Dziedzice', lat:49.915104, lon:19.00499, type:'stacja', platforms:2, tracks:4, daily_trains:74, type_plk:'ST', plk_lines:'139;150;693;790;93', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'76000', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'CZE', name:'Częstochowa', lat:50.808548, lon:19.121357, type:'stacja', platforms:5, tracks:8, daily_trains:102, type_plk:'ST', plk_lines:'1;700;701;703', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'62653', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'DZI', name:'Działoszyn', lat:51.11762, lon:18.91327, type:'stacja', platforms:2, tracks:2, daily_trains:14, type_plk:'ST', plk_lines:'131', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'72025', voivodeship:'poza woj. (punkt graniczny)', data_source:'gtfs+plk'}),
(:Station {id:'DA2', name:'Dąbrowa Górnicza', lat:50.330185, lon:19.185402, type:'stacja', platforms:2, tracks:3, daily_trains:74, type_plk:'ST', plk_lines:'1', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'74583', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'DAG', name:'Dąbrowa Górnicza Ząbkowice', lat:50.36687, lon:19.264938, type:'stacja', platforms:3, tracks:5, daily_trains:80, type_plk:'ST', plk_lines:'1;133;160;183;186', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'74500', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'GLI', name:'Gliwice', lat:50.300957, lon:18.676891, type:'stacja', platforms:4, tracks:8, daily_trains:130, type_plk:'ST', plk_lines:'137;141;147;168;200;671;711', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'69708', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'GOC', name:'Goczałkowice-Zdrój', lat:49.935333, lon:18.977055, type:'przystanek osobowy publiczny', platforms:2, tracks:2, daily_trains:43, type_plk:'PO', plk_lines:'139', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75952', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'GOL', name:'Goleszów', lat:49.746777, lon:18.749159, type:'stacja', platforms:2, tracks:4, daily_trains:44, type_plk:'ST', plk_lines:'190;191', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'76901', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'JA2', name:'Jaworzno Szczakowa', lat:50.246464, lon:19.296741, type:'stacja', platforms:2, tracks:4, daily_trains:16, type_plk:'ST', plk_lines:'133;134;156;666;668;669;670;714;715', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'73908', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'KA2', name:'Kalety', lat:50.56582, lon:18.888542, type:'stacja', platforms:2, tracks:3, daily_trains:54, type_plk:'ST', plk_lines:'130;131;143', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'72108', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'KAT', name:'Katowice', lat:50.25785, lon:19.017132, type:'stacja', platforms:3, tracks:6, daily_trains:180, type_plk:'ST', plk_lines:'1;137;138;139;656;713', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'73312', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'KAL', name:'Katowice Ligota', lat:50.225918, lon:18.977833, type:'stacja', platforms:3, tracks:6, daily_trains:86, type_plk:'ST', plk_lines:'139;140;141;142;864', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'72900', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'KAP', name:'Katowice Piotrowice', lat:50.213337, lon:18.970453, type:'przystanek osobowy publiczny', platforms:3, tracks:3, daily_trains:95, type_plk:'PO', plk_lines:'139;140', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'72967', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'KAS', name:'Katowice Szopienice Południowe', lat:50.258842, lon:19.091688, type:'posterunek odgałęźny', platforms:2, tracks:4, daily_trains:84, type_plk:'PODG', plk_lines:'1;138;660', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'73650', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'KET', name:'Kęty', lat:49.880672, lon:19.225807, type:'stacja', platforms:1, tracks:2, daily_trains:0, type_plk:'ST', plk_lines:'117', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'76232', voivodeship:'poza woj. (punkt graniczny)', data_source:'gtfs+plk'}),
(:Station {id:'KOB', name:'Kłobuck', lat:50.908463, lon:18.923552, type:'stacja', platforms:2, tracks:2, daily_trains:16, type_plk:'ST', plk_lines:'131', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'71944', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'LES', name:'Leszczyny', lat:50.139557, lon:18.617472, type:'stacja', platforms:1, tracks:2, daily_trains:64, type_plk:'ST', plk_lines:'140;149', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'68064', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'LUB', name:'Lubliniec', lat:50.672432, lon:18.691446, type:'stacja', platforms:2, tracks:4, daily_trains:56, type_plk:'ST', plk_lines:'143;152;61', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'71407', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'MIK', name:'Mikołów', lat:50.17288, lon:18.899258, type:'stacja', platforms:2, tracks:3, daily_trains:43, type_plk:'ST', plk_lines:'140', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'69062', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'MYS', name:'Mysłowice', lat:50.237465, lon:19.141726, type:'stacja', platforms:3, tracks:5, daily_trains:43, type_plk:'ST', plk_lines:'134;138;655', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'73502', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'ORJ', name:'Orzesze Jaśkowice', lat:50.144848, lon:18.740936, type:'stacja', platforms:2, tracks:4, daily_trains:66, type_plk:'ST', plk_lines:'140;169', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'68148', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'OSW', name:'Oświęcim', lat:50.041603, lon:19.200062, type:'stacja', platforms:4, tracks:7, daily_trains:34, type_plk:'ST', plk_lines:'138;699;882;93;94', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'77107', voivodeship:'poza woj. (punkt graniczny)', data_source:'gtfs+plk'}),
(:Station {id:'PI2', name:'Pierściec', lat:49.83056, lon:18.81342, type:'stacja', platforms:1, tracks:2, daily_trains:20, type_plk:'ST', plk_lines:'157', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75762', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'POR', name:'Poręba', lat:50.483883, lon:19.332548, type:'mijanka i przystanek osobowy', platforms:1, tracks:2, daily_trains:24, type_plk:'MPO', plk_lines:'182', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'178588', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'PSZ', name:'Pszczyna', lat:49.975582, lon:18.953398, type:'stacja', platforms:2, tracks:3, daily_trains:47, type_plk:'ST', plk_lines:'139;148', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75903', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'RAC', name:'Racibórz', lat:50.090294, lon:18.226595, type:'stacja', platforms:3, tracks:5, daily_trains:60, type_plk:'ST', plk_lines:'151;177', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'68700', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'RUS', name:'Ruda Śląska', lat:50.315914, lon:18.850834, type:'przystanek osobowy publiczny', platforms:1, tracks:2, daily_trains:76, type_plk:'PO', plk_lines:'137', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'69849', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'RU2', name:'Rudyszwałd', lat:49.939697, lon:18.303295, type:'przystanek osobowy publiczny', platforms:3, tracks:3, daily_trains:46, type_plk:'PO', plk_lines:'151;158', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'67942', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'RYB', name:'Rybnik', lat:50.088924, lon:18.547441, type:'stacja', platforms:3, tracks:5, daily_trains:89, type_plk:'ST', plk_lines:'140;148;173;688;957', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'68205', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'RYT', name:'Rybnik Towarowy', lat:50.06658, lon:18.51534, type:'stacja', platforms:2, tracks:3, daily_trains:72, type_plk:'ST', plk_lines:'140;158;688;862;957;958;959', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'68007', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'SKS', name:'Skalite Serafinov', lat:49.501614, lon:18.964785, type:'przystanek osobowy publiczny', platforms:2, tracks:3, daily_trains:20, type_plk:'PO', plk_lines:'489', has_platform:'NIE', platform_manager:'', platforms_confidence:'derived', type_source:'PLK_zal_2.6', gtfs_stop_id:'190033', voivodeship:'poza woj. (punkt graniczny)', data_source:'gtfs+plk'}),
(:Station {id:'SKO', name:'Skoczów', lat:49.79355, lon:18.790192, type:'stacja', platforms:2, tracks:3, daily_trains:24, type_plk:'ST', plk_lines:'157;190', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75788', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'SOG', name:'Sosnowiec Główny', lat:50.278786, lon:19.126204, type:'stacja', platforms:1, tracks:2, daily_trains:73, type_plk:'ST', plk_lines:'1;62;659;660', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'74658', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'TAG', name:'Tarnowskie Góry', lat:50.446827, lon:18.865116, type:'stacja', platforms:2, tracks:4, daily_trains:79, type_plk:'ST', plk_lines:'127;129;130;131;144;182;856;892;950;951;954;979', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'71001', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'TYC', name:'Tychy', lat:50.136185, lon:18.964157, type:'stacja', platforms:3, tracks:6, daily_trains:141, type_plk:'ST', plk_lines:'139;142;169;179', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'73700', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'TYL', name:'Tychy Lodowisko', lat:50.10768, lon:19.000523, type:'przystanek osobowy publiczny', platforms:1, tracks:1, daily_trains:64, type_plk:'PO', plk_lines:'696', has_platform:'TAK', platform_manager:'UM Tychy', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'242839', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'WIG', name:'Wisła Głębce', lat:49.621803, lon:18.875376, type:'stacja', platforms:3, tracks:4, daily_trains:18, type_plk:'ST', plk_lines:'191', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'77040', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'WOS', name:'Wodzisław Śląski', lat:50.00784, lon:18.476183, type:'stacja', platforms:2, tracks:3, daily_trains:38, type_plk:'ST', plk_lines:'158;876', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'68403', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'WEG', name:'Węgierska Górka', lat:49.60341, lon:19.11787, type:'stacja', platforms:1, tracks:2, daily_trains:28, type_plk:'ST', plk_lines:'139', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'76737', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'ZAB', name:'Zabrze', lat:50.305305, lon:18.78715, type:'stacja', platforms:1, tracks:2, daily_trains:76, type_plk:'ST', plk_lines:'137', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'69823', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'ZA2', name:'Zabrzeg', lat:49.907684, lon:18.939075, type:'przystanek osobowy publiczny', platforms:2, tracks:2, daily_trains:30, type_plk:'PO', plk_lines:'150;93', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75739', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'ZAW', name:'Zawiercie', lat:50.481148, lon:19.423216, type:'stacja', platforms:3, tracks:5, daily_trains:94, type_plk:'ST', plk_lines:'1;160;182;186;4;705', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75309', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'ZWA', name:'Zwardoń', lat:49.504494, lon:18.977837, type:'stacja', platforms:2, tracks:3, daily_trains:48, type_plk:'ST', plk_lines:'139', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'76869', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'AZY', name:'Łazy', lat:50.43009, lon:19.39202, type:'stacja', platforms:2, tracks:4, daily_trains:70, type_plk:'ST', plk_lines:'1;154;160;186', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'75200', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'ODY', name:'Łodygowice', lat:49.72534, lon:19.141006, type:'stacja', platforms:1, tracks:2, daily_trains:45, type_plk:'ST', plk_lines:'139', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'76422', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'SWI', name:'Świętochłowice', lat:50.28906, lon:18.9182, type:'przystanek osobowy publiczny', platforms:1, tracks:2, daily_trains:76, type_plk:'PO', plk_lines:'137', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'73148', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'ZOR', name:'Żory', lat:50.05171, lon:18.702848, type:'stacja', platforms:2, tracks:3, daily_trains:18, type_plk:'ST', plk_lines:'148;159', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'69203', voivodeship:'śląskie', data_source:'gtfs+plk'}),
(:Station {id:'ZYW', name:'Żywiec', lat:49.67983, lon:19.18592, type:'stacja', platforms:3, tracks:5, daily_trains:44, type_plk:'ST', plk_lines:'139;97', has_platform:'TAK', platform_manager:'', platforms_confidence:'measured', type_source:'PLK_zal_2.6', gtfs_stop_id:'76604', voivodeship:'śląskie', data_source:'gtfs+plk'})
"""

# Format krotki (wstecznie zgodny z oryginalem — pierwsze 7 pol bez zmian):
#   (from, to, line, dist_km, vmax, rail_tracks, travel_min,
#    vmax_ezt, vmax_wagon, vmax_towar, plk_klasa, plk_line, vmax_confidence,
#    lines_gtfs, rail_tracks_confidence)
# Pola 8-13 pochodza z wykazow PLK (predkosci wg kategorii, klasa odcinka).
# line = glowny numer linii PLK (0 dla 5 odcinkow bez jednoznacznego dopasowania).
TRACKS = [
    ("CHA", "BOH", 479, 5.028, 90, 1, 6, 90, 90, 90, "D3", "479", "measured", "S71", "measured"),
    ("CHA", "RU2", 151, 1.706, 100, 2, 3, 100, 100, 100, "D3", "151", "measured", "S71;S78", "measured"),
    ("CHB", "BYT", 131, 11.349, 100, 2, 9, 100, 100, 100, "D4", "131", "measured", "S1;S8;S82;S9", "measured"),
    ("CHY", "CHM", 157, 1.668, 40, 2, 4, 40, 40, 30, "D3", "157", "measured", "S1/S6;S6;S6/S1;S6/S62;S61", "measured"),
    ("CHY", "ZA2", 93, 9.283, 120, 2, 12, 120, 120, 90, "D3", "93", "measured", "S1/S6;S6;S6/S1;S6/S62;S61;S75", "measured"),
    ("CHM", "ZA2", 0, 8.966, 60, 1, 12, None, None, None, "", "", "derived", "S1/S6;S6;S6/S1;S6/S62;S61", "assumed"),
    ("CIE", "CHY", 90, 32.017, 80, 2, 47, 80, 80, 80, "D3", "90;93", "measured", "NA;S61", "measured"),
    ("CIE", "GOL", 190, 9.891, 70, 1, 11, 70, 70, 70, "D4", "190", "measured", "S6;S6/S62;S61;S62;S62/S6", "measured"),
    ("CZ2", "BIG", 139, 11.852, 100, 2, 11, 100, 100, 70, "D3", "139", "measured", "KSL;S1/S5;S5;S5/S1;S51;S72", "measured"),
    ("CZ2", "OSW", 93, 21.412, 120, 2, 14, 120, 120, 80, "D3", "93", "measured", "S6;S6/S62", "measured"),
    ("CZ2", "ZA2", 93, 4.797, 160, 2, 4, 160, 160, 120, "D3", "93", "measured", "S6;S6/S62;S61;S75", "measured"),
    ("DZI", "KOB", 131, 23.697, 130, 2, 13, 130, 130, 110, "D3", "131", "measured", "S82", "measured"),
    ("DA2", "DAG", 1, 7.222, 110, 2, 6, 110, 110, 80, "D3", "1", "measured", "S1;S1/S5;S1/S6;S6/S1;S9", "measured"),
    ("DA2", "SOG", 1, 8.946, 100, 2, 9, 100, 100, 80, "D3", "1", "measured", "S1;S1/S5;S1/S6;S5/S1;S51;S6/S1;S9", "measured"),
    ("DAG", "MYS", 0, 16.913, 50, 1, 19, None, None, None, "", "", "derived", "S1/S5;S5/S1;S51", "assumed"),
    ("GLI", "BYT", 147, 18.469, 80, 2, 16, 80, 80, 80, "D3", "147", "measured", "S1;S18", "measured"),
    ("GLI", "LES", 149, 28.14, 60, 2, 36, 60, 60, 60, "D3", "149", "measured", "S17;S17/S7;S7/S17;S75;S76", "measured"),
    ("GLI", "ZAB", 137, 8.188, 110, 2, 6, 110, 110, 90, "D3", "137", "measured", "S1", "measured"),
    ("GOC", "CZ2", 139, 3.337, 110, 2, 3, 110, 110, 100, "D3", "139", "measured", "S1/S5;S5;S5/S1;S51;S6;S72", "measured"),
    ("GOC", "PSZ", 139, 4.991, 130, 2, 4, 130, 130, 120, "D3", "139", "measured", "S1/S5;S1/S6;S5;S5/S1;S51;S6;S6/S1;S6/S62;S72", "measured"),
    ("GOC", "ZA2", 0, 5.735, 100, 1, 4, None, None, None, "", "", "derived", "S6;S6/S62", "assumed"),
    ("JA2", "BAL", 133, 9.926, 140, 2, 6, 140, 140, 120, "D3", "133", "measured", "S3", "measured"),
    ("JA2", "DAG", 133, 15.134, 100, 2, 12, 100, 100, 90, "D3", "133", "measured", "S1;S34;S5/S1", "measured"),
    ("JA2", "MYS", 134, 12.328, 130, 2, 10, 130, 130, 110, "D3", "134", "measured", "S1;S3;S5/S1", "measured"),
    ("KA2", "KOB", 131, 40.686, 110, 2, 25, 110, 110, 100, "D3", "131", "measured", "S82", "measured"),
    ("KA2", "LUB", 143, 19.686, 120, 2, 14, 120, 120, 100, "D3", "143", "measured", "S8", "measured"),
    ("KAT", "CHB", 137, 5.657, 90, 2, 6, 90, 90, 80, "D3", "137", "measured", "S1;S8;S82;S9", "measured"),
    ("KAT", "KAS", 138, 5.469, 100, 2, 8, 100, 100, 100, "D3", "138", "measured", "S1;S1/S5;S1/S6;S3;S31;S5/S1;S6/S1;S9", "measured"),
    ("KAL", "KAT", 139, 5.715, 80, 2, 8, 80, 80, 70, "D3", "139", "measured", "KSL;S1/S5;S1/S6;S4;S5;S5/S1;S51;S6;S6/S1;S6/S62;S7;S71", "measured"),
    ("KAL", "KAP", 139, 1.7, 80, 2, 3, 80, 80, 60, "D3", "139", "measured", "S1/S5;S1/S6;S4;S5;S5/S1;S51;S6;S6/S1;S6/S62;S7;S71", "measured"),
    ("KAS", "MYS", 138, 4.685, 90, 2, 5, 90, 90, 90, "D3", "138", "measured", "S1;S3;S31;S5/S1", "measured"),
    ("KAS", "SOG", 1, 3.458, 100, 2, 4, 100, 100, 80, "D3", "1", "measured", "S1;S1/S5;S1/S6;S6/S1;S9", "measured"),
    ("KET", "BIG", 117, 16.355, 70, 1, 16, 70, 70, 50, "C3", "117", "measured", "S51", "measured"),
    ("LES", "RYB", 140, 7.967, 90, 2, 7, 90, 90, 90, "D3", "140", "measured", "S17;S17/S7;S7;S7/S17;S71;S74", "measured"),
    ("LUB", "CZE", 61, 38.804, 120, 2, 29, 120, 120, 110, "D3", "61;700", "measured", "S13", "measured"),
    ("MIK", "KAP", 140, 7.42, 100, 1, 6, 100, 100, 100, "D3", "140", "measured", "S7;S71", "measured"),
    ("ORJ", "LES", 140, 10.425, 100, 2, 8, 100, 100, 100, "D3", "140", "measured", "S7;S71;S74", "measured"),
    ("ORJ", "MIK", 140, 12.915, 90, 1, 13, 90, 90, 90, "D3", "140", "measured", "S7;S71", "measured"),
    ("ORJ", "TYC", 169, 17.102, 100, 1, 14, 100, 100, 100, "D3", "169", "measured", "S74", "measured"),
    ("OSW", "MYS", 138, 23.627, 80, 2, 30, 80, 80, 60, "D3", "138", "measured", "S31", "measured"),
    ("PI2", "CHM", 157, 6.725, 100, 1, 6, 100, 100, 80, "D4", "157", "measured", "S6;S6/S62;S61", "measured"),
    ("PI2", "SKO", 157, 4.678, 100, 1, 4, 100, 100, 70, "D4", "157", "measured", "S6;S6/S62;S61;S62", "measured"),
    ("POR", "ZAW", 182, 6.513, 120, 1, 5, 120, 120, 90, "D3", "182", "measured", "S9", "measured"),
    ("POR", "AZY", 0, 11.124, 80, 1, 8, None, None, None, "", "", "derived", "S9", "assumed"),
    ("PSZ", "TYC", 139, 18.837, 130, 2, 16, 130, 130, 110, "D3", "139", "measured", "S1/S5;S5;S5/S1;S51;S6;S6/S62", "measured"),
    ("RAC", "RU2", 151, 19.468, 110, 2, 15, 110, 110, 110, "D3", "151", "measured", "S78", "measured"),
    ("RAC", "RYT", 140, 33.121, 100, 2, 33, 100, 100, 100, "D3", "140;151", "measured", "S17/S7;S7;S7/S17;S7/S72;S72/S7", "measured"),
    ("RYT", "RYB", 140, 3.643, 70, 2, 4, 70, 70, 70, "D3", "140", "measured", "S17;S17/S7;S7;S7/S17;S7/S72;S71;S71/S72;S72/S7;S72/S71", "measured"),
    ("SKO", "GOL", 190, 6.255, 70, 1, 7, 70, 70, 70, "D4", "190", "measured", "S6;S6/S62;S61;S62", "measured"),
    ("TAG", "BYT", 127, 16.509, 80, 2, 14, 80, 80, 80, "D4", "127;128;131", "measured", "S8;S82;S9", "measured"),
    ("TAG", "KA2", 131, 14.057, 100, 2, 10, 100, 100, 100, "D3", "131", "measured", "S8;S82", "measured"),
    ("TAG", "POR", 182, 35.88, 120, 1, 25, 120, 120, 100, "D3", "182", "measured", "S9", "measured"),
    ("TYC", "KAP", 139, 9.236, 120, 2, 7, 120, 120, 80, "D3", "139", "measured", "S1/S5;S4;S5;S5/S1;S51;S6;S6/S1;S6/S62", "measured"),
    ("TYL", "TYC", 179, 4.576, 60, 2, 7, 60, 60, 60, "C3", "179", "measured", "S4", "measured"),
    ("WIG", "GOL", 191, 19.676, 70, 1, 22, 70, 70, 40, "D4", "191", "measured", "S1/S6;S6;S6/S1;S6/S62;S62;S62/S6;S76;S77", "measured"),
    ("WOS", "RU2", 158, 15.935, 90, 1, 16, 90, 90, 90, "D3", "158", "measured", "S71", "measured"),
    ("WOS", "RYT", 158, 7.831, 70, 2, 11, 70, 70, 70, "D3", "158", "measured", "S17;S71;S71/S72;S72/S71", "measured"),
    ("ZAB", "RUS", 137, 4.771, 110, 2, 4, 110, 110, 100, "D3", "137", "measured", "S1", "measured"),
    ("ZAW", "CZE", 1, 44.776, 140, 2, 36, 140, 140, 110, "D3", "1", "measured", "S1;S1/S5;S1/S6;S34;S5/S1;S51;S6/S1;S9", "measured"),
    ("ZAW", "AZY", 1, 6.729, 120, 2, 4, 120, 120, 120, "D3", "1", "measured", "S1;S1/S5;S1/S6;S34;S5/S1;S51;S6/S1;S9", "measured"),
    ("ZWA", "SKS", 0, 1.029, 30, 1, 2, None, None, None, "", "", "derived", "ZSSK", "assumed"),
    ("ZWA", "WEG", 139, 26.429, 70, 1, 28, 70, 70, 50, "D3", "139", "measured", "S1/S5;S5;S5/S1;S75", "measured"),
    ("AZY", "DAG", 1, 12.27, 110, 2, 10, 110, 110, 100, "D3", "1;186", "measured", "KSL;S1;S9", "measured"),
    ("ODY", "BIG", 139, 15.459, 110, 2, 14, 110, 110, 70, "D3", "139", "measured", "KSL;S1/S5;S5;S5/S1;S72;S75", "measured"),
    ("ODY", "ZYW", 139, 6.55, 120, 1, 6, 120, 120, 60, "D4", "139", "measured", "KSL;S1/S5;S5;S5/S1;S72", "measured"),
    ("SWI", "CHB", 137, 2.366, 100, 2, 2, 100, 100, 100, "D3", "137", "measured", "S1", "measured"),
    ("SWI", "RUS", 137, 5.715, 90, 2, 5, 90, 90, 90, "D3", "137", "measured", "S1", "measured"),
    ("ZOR", "CHY", 157, 21.754, 100, 2, 16, 100, 100, 80, "D3", "157;159", "measured", "S75;S76;S77", "measured"),
    ("ZOR", "PSZ", 148, 22.635, 130, 1, 19, 130, 130, 100, "D3", "148", "measured", "S72", "measured"),
    ("ZOR", "RYB", 148, 13.825, 110, 2, 13, 110, 110, 110, "D3", "148", "measured", "S7/S72;S71/S72;S72;S72/S7;S72/S71", "measured"),
    ("ZYW", "WEG", 139, 10.405, 90, 1, 10, 90, 90, 60, "D4", "139", "measured", "S1/S5;S5;S5/S1;S75", "measured"),
]

# segment_id wspolne dla obu kierunkow odcinka (blokada kierunkowa niezalezna).
# restricted_vmax/active_event_id startuja jako null — wypelnia je silnik zdarzen.
# Pola PLK (vmax_ezt itd.) dopisane do relacji jako nadmiarowe.
TRACK_QUERY = """
MATCH (a:Station {id:$from}), (b:Station {id:$to})
CREATE (a)-[:TRACK {segment_id:$seg, line:$line, dist_km:$dist, vmax:$vmax,
       rail_tracks:$rail, travel_min:$min, status:'active',
       restricted_vmax: null, active_event_id: null,
       vmax_ezt:$vmax_ezt, vmax_wagon:$vmax_wagon, vmax_towar:$vmax_towar,
       plk_klasa:$klasa, plk_line:$plk_line, lines_gtfs:$lines_gtfs,
       dist_source:'gtfs_shapes (rzutowanie monotoniczne)', dist_confidence:'measured',
       vmax_source:'PLK_zal_2.1', vmax_confidence:$conf,
       rail_tracks_confidence:$rtconf, data_confidence:$conf}]->(b),
       (b)-[:TRACK {segment_id:$seg, line:$line, dist_km:$dist, vmax:$vmax,
       rail_tracks:$rail, travel_min:$min, status:'active',
       restricted_vmax: null, active_event_id: null,
       vmax_ezt:$vmax_ezt, vmax_wagon:$vmax_wagon, vmax_towar:$vmax_towar,
       plk_klasa:$klasa, plk_line:$plk_line, lines_gtfs:$lines_gtfs,
       dist_source:'gtfs_shapes (rzutowanie monotoniczne)', dist_confidence:'measured',
       vmax_source:'PLK_zal_2.1', vmax_confidence:$conf,
       rail_tracks_confidence:$rtconf, data_confidence:$conf}]->(a)
"""

# Kazdy pociag ma stala pare stacji (origin/destination). Startuje ze
# status='waiting' — pierwszy tick silnika sam wylicza trase A* i rusza go
# (app/services/train_service.dispatch_or_wait). route_station_ids puste
# CELOWO — nie wpisujemy trasy, silnik ja liczy.
# Format: (id, name, type, origin, destination, vmax, priority, mass_tonnes,
#          length_m, accel, decel, operator, line_code, data_source, data_confidence)
TRAINS = [
    ("KS_KSL_CZE_ZYW", "KSL Czechowice-Dziedzice – Żywiec", "REGIONAL", "CZ2", "ZYW", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "KSL", "gtfs_koleje_slaskie", "measured"),
    ("KS_S1X_GLI_CZE", "S1 Gliwice – Częstochowa", "REGIONAL", "GLI", "CZE", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S1", "gtfs_koleje_slaskie", "measured"),
    ("KS_S1X_GLI_DAB", "S1 Gliwice – Dąbrowa Górnicza Ząbkowice", "REGIONAL", "GLI", "DAG", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S1", "gtfs_koleje_slaskie", "measured"),
    ("KS_S1X_KAT_GLI", "S1 Katowice – Gliwice", "REGIONAL", "KAT", "GLI", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S1", "gtfs_koleje_slaskie", "measured"),
    ("KS_S13_CZE_LUB", "S13 Częstochowa – Lubliniec", "REGIONAL", "CZE", "LUB", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S13", "gtfs_koleje_slaskie", "measured"),
    ("KS_S17_WOD_GLI", "S17 Wodzisław Śląski – Gliwice", "REGIONAL", "WOS", "GLI", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S17", "gtfs_koleje_slaskie", "measured"),
    ("KS_S17_GLI_RYB", "S17 Gliwice – Rybnik", "REGIONAL", "GLI", "RYB", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S17", "gtfs_koleje_slaskie", "measured"),
    ("KS_S18_GLI_BYT", "S18 Gliwice – Bytom", "REGIONAL", "GLI", "BYT", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S18", "gtfs_koleje_slaskie", "measured"),
    ("KS_S3X_KAT_JAW", "S3 Katowice – Jaworzno Szczakowa", "REGIONAL", "KAT", "JA2", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S3", "gtfs_koleje_slaskie", "measured"),
    ("KS_S3X_BAL_KAT", "S3 Balin – Katowice", "REGIONAL", "BAL", "KAT", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S3", "gtfs_koleje_slaskie", "measured"),
    ("KS_S31_MYS_OSW", "S31 Mysłowice – Oświęcim", "REGIONAL", "MYS", "OSW", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S31", "gtfs_koleje_slaskie", "measured"),
    ("KS_S31_OSW_KAT", "S31 Oświęcim – Katowice", "REGIONAL", "OSW", "KAT", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S31", "gtfs_koleje_slaskie", "measured"),
    ("KS_S34_CZE_JAW", "S34 Częstochowa – Jaworzno Szczakowa", "REGIONAL", "CZE", "JA2", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S34", "gtfs_koleje_slaskie", "measured"),
    ("KS_S4X_TYC_TYC", "S4 Tychy – Tychy Lodowisko", "REGIONAL", "TYC", "TYL", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S4", "gtfs_koleje_slaskie", "measured"),
    ("KS_S4X_KAT_TYC", "S4 Katowice – Tychy Lodowisko", "REGIONAL", "KAT", "TYL", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S4", "gtfs_koleje_slaskie", "measured"),
    ("KS_S4X_TYC_KAT", "S4 Tychy Lodowisko – Katowice Ligota", "REGIONAL", "TYL", "KAL", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S4", "gtfs_koleje_slaskie", "measured"),
    ("KS_S5X_ZWA_KAT", "S5 Zwardoń – Katowice", "REGIONAL", "ZWA", "KAT", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S5", "gtfs_koleje_slaskie", "measured"),
    ("KS_S5X_KAT_ZYW", "S5 Katowice – Żywiec", "REGIONAL", "KAT", "ZYW", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S5", "gtfs_koleje_slaskie", "measured"),
    ("KS_S6X_WIS_KAT", "S6 Wisła Głębce – Katowice", "REGIONAL", "WIG", "KAT", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S6", "gtfs_koleje_slaskie", "measured"),
    ("KS_S6X_WIS_CZE", "S6 Wisła Głębce – Czechowice-Dziedzice", "REGIONAL", "WIG", "CZ2", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S6", "gtfs_koleje_slaskie", "measured"),
    ("KS_S61_CIE_CZE", "S61 Cieszyn – Czechowice-Dziedzice", "REGIONAL", "CIE", "CZ2", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S61", "gtfs_koleje_slaskie", "measured"),
    ("KS_S62_GOL_CIE", "S62 Goleszów – Cieszyn", "REGIONAL", "GOL", "CIE", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S62", "gtfs_koleje_slaskie", "measured"),
    ("KS_S62_GOL_WIS", "S62 Goleszów – Wisła Głębce", "REGIONAL", "GOL", "WIG", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S62", "gtfs_koleje_slaskie", "measured"),
    ("KS_S62_CIE_SKO", "S62 Cieszyn – Skoczów", "REGIONAL", "CIE", "SKO", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S62", "gtfs_koleje_slaskie", "measured"),
    ("KS_S7X_KAT_RAC", "S7 Katowice – Racibórz", "REGIONAL", "KAT", "RAC", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S7", "gtfs_koleje_slaskie", "measured"),
    ("KS_S7X_RYB_RAC", "S7 Rybnik – Racibórz", "REGIONAL", "RYB", "RAC", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S7", "gtfs_koleje_slaskie", "measured"),
    ("KS_S7X_KAT_RAC_2", "S7 Katowice Ligota – Racibórz", "REGIONAL", "KAL", "RAC", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S7", "gtfs_koleje_slaskie", "measured"),
    ("KS_S71_KAT_CHA", "S71 Katowice – Chałupki", "REGIONAL", "KAT", "CHA", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S71", "gtfs_koleje_slaskie", "measured"),
    ("KS_S71_BOH_KAT", "S71 Bohumin – Katowice", "REGIONAL", "BOH", "KAT", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S71", "gtfs_koleje_slaskie", "measured"),
    ("KS_S71_RYB_WOD", "S71 Rybnik – Wodzisław Śląski", "REGIONAL", "RYB", "WOS", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S71", "gtfs_koleje_slaskie", "measured"),
    ("KS_S72_ZOR_RYB", "S72 Żory – Rybnik", "REGIONAL", "ZOR", "RYB", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S72", "gtfs_koleje_slaskie", "measured"),
    ("KS_S74_ORZ_TYC", "S74 Orzesze Jaśkowice – Tychy", "REGIONAL", "ORJ", "TYC", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S74", "gtfs_koleje_slaskie", "measured"),
    ("KS_S78_RAC_CHA", "S78 Racibórz – Chałupki", "REGIONAL", "RAC", "CHA", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S78", "gtfs_koleje_slaskie", "measured"),
    ("KS_S8X_CHO_LUB", "S8 Chorzów Batory – Lubliniec", "REGIONAL", "CHB", "LUB", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S8", "gtfs_koleje_slaskie", "measured"),
    ("KS_S8X_BYT_LUB", "S8 Bytom – Lubliniec", "REGIONAL", "BYT", "LUB", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S8", "gtfs_koleje_slaskie", "measured"),
    ("KS_S8X_KAT_LUB", "S8 Katowice – Lubliniec", "REGIONAL", "KAT", "LUB", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S8", "gtfs_koleje_slaskie", "measured"),
    ("KS_S82_DZI_CHO", "S82 Działoszyn – Chorzów Batory", "REGIONAL", "DZI", "CHB", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S82", "gtfs_koleje_slaskie", "measured"),
    ("KS_S82_KOB_CHO", "S82 Kłobuck – Chorzów Batory", "REGIONAL", "KOB", "CHB", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S82", "gtfs_koleje_slaskie", "measured"),
    ("KS_S9X_CHO_CZE", "S9 Chorzów Batory – Częstochowa", "REGIONAL", "CHB", "CZE", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S9", "gtfs_koleje_slaskie", "measured"),
    ("KS_S9X_TAR_CZE", "S9 Tarnowskie Góry – Częstochowa", "REGIONAL", "TAG", "CZE", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S9", "gtfs_koleje_slaskie", "measured"),
    ("KS_S9X_CZE_KAT", "S9 Częstochowa – Katowice", "REGIONAL", "CZE", "KAT", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "S9", "gtfs_koleje_slaskie", "measured"),
    ("KS_ZSS_SKA_ZWA", "ZSSK Skalite Serafinov – Zwardoń", "REGIONAL", "SKS", "ZWA", 120, 2, 120, 60, 0.6, 0.9, "Koleje Śląskie", "ZSSK", "gtfs_koleje_slaskie", "measured"),
    ("IC_SLASK", "IC Ślązak", "IC", "BIG", "KAT", 160, 3, 420, 200, 0.5, 0.8, "PKP Intercity", "", "modeled_znane_relacje", "modeled"),
    ("IC_ONDRASZEK", "IC Ondraszek", "IC", "BIG", "SOG", 160, 3, 420, 200, 0.5, 0.8, "PKP Intercity", "", "modeled_znane_relacje", "modeled"),
    ("IC_SILESIA", "EC Silesia", "IC", "KAT", "CHY", 160, 3, 420, 200, 0.5, 0.8, "PKP Intercity", "", "modeled_znane_relacje", "modeled"),
    ("IC_SOBIESKI", "EC Sobieski", "IC", "KAT", "GLI", 160, 3, 420, 200, 0.5, 0.8, "PKP Intercity", "", "modeled_znane_relacje", "modeled"),
    ("IC_JASNOGORA", "TLK Jasna Góra", "IC", "KAT", "CZE", 160, 3, 420, 200, 0.5, 0.8, "PKP Intercity", "", "modeled_znane_relacje", "modeled"),
    ("IC_ODRA", "IC Odra", "IC", "KAT", "GLI", 160, 3, 420, 200, 0.5, 0.8, "PKP Intercity", "", "modeled_znane_relacje", "modeled"),
    ("TW_WEGIEL_PLN", "Towarowy węglowy północ", "FREIGHT", "RYT", "GLI", 80, 1, 1800, 550, 0.25, 0.4, "przewoźnik towarowy (modelowy)", "", "modeled_korytarze_towarowe", "modeled"),
    ("TW_TRANZYT_CZ", "Towarowy tranzytowy CZ", "FREIGHT", "CHA", "RYT", 80, 1, 1800, 550, 0.25, 0.4, "przewoźnik towarowy (modelowy)", "", "modeled_korytarze_towarowe", "modeled"),
    ("TW_HUTA", "Towarowy hutniczy", "FREIGHT", "DAG", "SOG", 80, 1, 1800, 550, 0.25, 0.4, "przewoźnik towarowy (modelowy)", "", "modeled_korytarze_towarowe", "modeled"),
    ("TW_MAGISTRALA", "Towarowy magistralny", "FREIGHT", "TAG", "LUB", 80, 1, 1800, 550, 0.25, 0.4, "przewoźnik towarowy (modelowy)", "", "modeled_korytarze_towarowe", "modeled"),
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
    dwell_until: null, delayed_by_event_id: null, updated_at: 0.0,
    operator: $operator, line_code: $line_code,
    data_source: $data_source, data_confidence: $conf
})
"""


def load_data(session):
    # 0. Czyszczenie i constrainty (idempotentnosc)
    # Zachowujemy konta (:User) i role (:Role) — reseed sieci kolejowej nie może
    # kasować danych logowania, inaczej znika m.in. konto administratora.
    session.run("MATCH (n) WHERE NOT n:User AND NOT n:Role DETACH DELETE n")
    for constraint in CONSTRAINTS:
        try:
            session.run(constraint)
        except Exception:
            pass  # constraint juz istnieje
    print("✓ Baza wyczyszczona, constrainty gotowe")

    # 1. Wezly stacji
    session.run(STATIONS)
    print(f"✓ Stacje utworzone ({STATIONS.count('(:Station')})")

    # 2. Relacje torow — kazda osobno (MATCH wymaga istniejacych wezlow).
    #    enumerate nadaje obu kierunkom to samo segment_id (SEG01..SEG71).
    for idx, tr in enumerate(TRACKS, start=1):
        (frm, to, line, dist, vmax, rail, mins,
         vmax_ezt, vmax_wagon, vmax_towar, klasa, plk_line, conf,
         lines_gtfs, rtconf) = tr
        seg_id = f"SEG{idx:02d}"
        session.run(TRACK_QUERY, **{
            "seg": seg_id,
            "from": frm, "to": to, "line": line,
            "dist": dist, "vmax": vmax, "rail": rail, "min": mins,
            "vmax_ezt": vmax_ezt, "vmax_wagon": vmax_wagon, "vmax_towar": vmax_towar,
            "klasa": klasa, "plk_line": plk_line, "conf": conf,
            "lines_gtfs": lines_gtfs, "rtconf": rtconf,
        })
    print(f"✓ Tory utworzone ({len(TRACKS)} odcinkow)")

    # 3. Pociagi
    for tr in TRAINS:
        (train_id, name, ttype, origin, destination, vmax, priority, mass,
         length, accel, decel, operator, line_code, data_source, conf) = tr
        session.run(TRAIN_QUERY, id=train_id, name=name, type=ttype, origin=origin,
                    destination=destination, vmax=vmax, priority=priority, mass=mass,
                    length=length, accel=accel, decel=decel,
                    operator=operator, line_code=line_code,
                    data_source=data_source, conf=conf)
    print(f"✓ Pociagi utworzone ({len(TRAINS)})")

    # 4. Role i konto administratora
    try:
        from app.services import auth_service
        auth_service.ensure_roles(session)
        created_admin = auth_service.ensure_admin_user(session)
        if created_admin:
            print(f"✓ Konto administratora gotowe: {created_admin}")
    except Exception as exc:
        print(f"⚠ Pomijam zasiew ról/admina w seed.py: {exc}")



if __name__ == "__main__":
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            load_data(session)
    print("✅ Dane wgrane pomyslnie!")
