import heapq
from neo4j import Session

from app.core.haversine import haversine_time_heuristic_min
from app.schemas.network import StationNode, TrackSegment
from app.schemas.routing import FastestRouteResponse
from app.services.network_service import segment_payload, station_payload


def get_train_vmax(train_type: str, custom_vmax: int | None = None) -> float:
	if custom_vmax is not None and custom_vmax > 0:
		return float(custom_vmax)
	t = (train_type or "IC").upper()
	if t in ("IC", "INTERCITY"):
		return 160.0
	elif t in ("REGIONAL", "REGIO", "REG"):
		return 120.0
	elif t in ("FREIGHT", "TOWAROWY"):
		return 80.0
	return 160.0


def find_fastest_route_astar(
	session: Session,
	from_station_id: str,
	to_station_id: str,
	train_type: str = "IC",
	custom_vmax: int | None = None,
) -> FastestRouteResponse:
	vmax_train = get_train_vmax(train_type, custom_vmax)
	is_regional = (train_type or "IC").upper() in ("REGIONAL", "REGIO", "REG")

	# 1. Pobierz stacje
	station_records = session.run("MATCH (n:Station) RETURN n")
	stations_by_id: dict[str, StationNode] = {}
	for record in station_records:
		node = record["n"]
		st = station_payload(node)
		stations_by_id[st.id] = st

	if from_station_id not in stations_by_id or to_station_id not in stations_by_id:
		return FastestRouteResponse(
			found=False,
			fromStation=from_station_id,
			toStation=to_station_id,
			trainType=train_type,
			path=[],
			segments=[],
			totalTravelMin=0.0,
			totalDistKm=0.0,
			exploredNodesCount=0,
			message="Nie odnaleziono stacji początkowej lub docelowej w bazie.",
		)

	if from_station_id == to_station_id:
		st = stations_by_id[from_station_id]
		return FastestRouteResponse(
			found=True,
			fromStation=from_station_id,
			toStation=to_station_id,
			trainType=train_type,
			path=[st],
			segments=[],
			totalTravelMin=0.0,
			totalDistKm=0.0,
			exploredNodesCount=0,
			message="Stacja początkowa i docelowa są takie same.",
		)

	# 2. Pobierz aktywne odcinki torów
	# Uwaga: pomijamy odcinki o statusie innym niż 'active' (obsługa awarii / reroutingu)
	rel_records = session.run(
		"""
		MATCH (u:Station)-[r:TRACK]->(v:Station)
		WHERE r.status = 'active'
		RETURN u, r, v
		"""
	)

	adj: dict[str, list[tuple[str, TrackSegment, dict]]] = {
		s_id: [] for s_id in stations_by_id
	}
	for record in rel_records:
		u_node = record["u"]
		v_node = record["v"]
		rel = record["r"]
		seg = segment_payload(u_node, rel, v_node)
		adj[u_node["id"]].append((v_node["id"], seg, dict(rel)))

	goal_st = stations_by_id[to_station_id]

	# 3. Algorytm A*
	# Kolejka priorytetowa krotek: (f_score, g_score, current_id)
	pq: list[tuple[float, float, str]] = []
	g_scores: dict[str, float] = {from_station_id: 0.0}
	came_from: dict[str, tuple[str, TrackSegment]] = {}
	explored_nodes: set[str] = set()

	start_st = stations_by_id[from_station_id]
	h_start = haversine_time_heuristic_min(
		start_st.lat, start_st.lon, goal_st.lat, goal_st.lon, vmax_train
	)
	heapq.heappush(pq, (h_start, 0.0, from_station_id))

	found = False

	while pq:
		f_curr, g_curr, u = heapq.heappop(pq)

		if g_curr > g_scores.get(u, float("inf")):
			continue

		explored_nodes.add(u)

		if u == to_station_id:
			found = True
			break

		for v, seg, rel_props in adj.get(u, []):
			dist_km = float(seg.distKm)
			track_vmax = float(seg.vmax)
			effective_speed = min(track_vmax, vmax_train)

			# Podstawowy czas jazdy na odcinku w minutach
			travel_min = (dist_km / effective_speed) * 60.0

			# Fundament pod opóźnienia: dodanie delay_min z właściwości toru (domyślnie 0)
			delay_min = float(rel_props.get("delay_min", 0.0))

			# Kara za postój na stacji pośredniej dla pociągu regionalnego (+1 min)
			stop_penalty = 1.0 if (is_regional and v != to_station_id) else 0.0

			step_cost = travel_min + delay_min + stop_penalty
			tentative_g = g_curr + step_cost

			if tentative_g < g_scores.get(v, float("inf")):
				g_scores[v] = tentative_g
				came_from[v] = (u, seg)
				v_st = stations_by_id[v]
				h = haversine_time_heuristic_min(
					v_st.lat, v_st.lon, goal_st.lat, goal_st.lon, vmax_train
				)
				heapq.heappush(pq, (tentative_g + h, tentative_g, v))

	if not found:
		return FastestRouteResponse(
			found=False,
			fromStation=from_station_id,
			toStation=to_station_id,
			trainType=train_type,
			path=[],
			segments=[],
			totalTravelMin=0.0,
			totalDistKm=0.0,
			exploredNodesCount=len(explored_nodes),
			message="Nie odnaleziono połączenia pomiędzy wskazanymi stacjami.",
		)

	# Rezygnacja ścieżki (reconstruction)
	curr = to_station_id
	path_stations: list[StationNode] = [stations_by_id[curr]]
	path_segments: list[TrackSegment] = []

	while curr != from_station_id:
		prev, seg = came_from[curr]
		path_segments.append(seg)
		path_stations.append(stations_by_id[prev])
		curr = prev

	path_stations.reverse()
	path_segments.reverse()

	total_dist_km = sum(s.distKm for s in path_segments)
	total_travel_min = round(g_scores[to_station_id], 2)

	return FastestRouteResponse(
		found=True,
		fromStation=from_station_id,
		toStation=to_station_id,
		trainType=train_type,
		path=path_stations,
		segments=path_segments,
		totalTravelMin=total_travel_min,
		totalDistKm=round(total_dist_km, 2),
		algorithm="A*",
		exploredNodesCount=len(explored_nodes),
	)
