import heapq

from neo4j import Session

from app.core.haversine import haversine_time_heuristic_min
from app.schemas.network import StationNode
from app.schemas.routing import FastestRouteResult
from app.services.network_service import station_payload

_VMAX_BY_TYPE = {
	"IC": 160.0,
	"INTERCITY": 160.0,
	"REGIONAL": 120.0,
	"REGIO": 120.0,
	"REG": 120.0,
	"FREIGHT": 80.0,
	"TOWAROWY": 80.0,
}


def get_train_vmax(train_type: str, custom_vmax: int | None = None) -> float:
	if custom_vmax is not None and custom_vmax > 0:
		return float(custom_vmax)
	return _VMAX_BY_TYPE.get((train_type or "IC").upper(), 160.0)


def _not_found(
	from_id: str, to_id: str, train_type: str, explored: int, message: str
) -> FastestRouteResult:
	return FastestRouteResult(
		found=False,
		fromStation=from_id,
		toStation=to_id,
		trainType=train_type,
		path=[],
		segmentIds=[],
		totalTravelMin=0.0,
		totalDistKm=0.0,
		exploredNodesCount=explored,
		message=message,
	)


def find_fastest_route_astar(
	session: Session,
	from_station_id: str,
	to_station_id: str,
	train_type: str = "IC",
	custom_vmax: int | None = None,
) -> FastestRouteResult:
	"""
	A* nad grafem stacji. Odcinki 'blocked' są całkowicie wykluczone; 'restricted'
	zostają w grafie, ale liczone z obniżonym efektywnym vmax (r.restricted_vmax),
	więc trasa omija je tylko wtedy, gdy realnie się to opłaca czasowo.
	Blokada jest kierunkowa — filtr działa na pojedynczej skierowanej relacji, więc
	zablokowanie jednego kierunku dwutorowego odcinka nie wyklucza drugiego.
	"""
	vmax_train = get_train_vmax(train_type, custom_vmax)
	is_regional = (train_type or "IC").upper() in ("REGIONAL", "REGIO", "REG")

	station_records = session.run("MATCH (n:Station) RETURN n")
	stations_by_id: dict[str, StationNode] = {
		record["n"]["id"]: station_payload(record["n"]) for record in station_records
	}

	if from_station_id not in stations_by_id or to_station_id not in stations_by_id:
		return _not_found(
			from_station_id,
			to_station_id,
			train_type,
			0,
			"Nie odnaleziono stacji początkowej lub docelowej w bazie.",
		)

	if from_station_id == to_station_id:
		return FastestRouteResult(
			found=True,
			fromStation=from_station_id,
			toStation=to_station_id,
			trainType=train_type,
			path=[stations_by_id[from_station_id]],
			segmentIds=[],
			totalTravelMin=0.0,
			totalDistKm=0.0,
			exploredNodesCount=0,
			message="Stacja początkowa i docelowa są takie same.",
		)

	rel_records = session.run(
		"""
		MATCH (u:Station)-[r:TRACK]->(v:Station)
		WHERE r.status IN ['active', 'restricted']
		RETURN u.id AS uId, v.id AS vId, r.segment_id AS segmentId, r.dist_km AS distKm,
		       r.vmax AS vmax, r.status AS status, r.restricted_vmax AS restrictedVmax
		"""
	)

	adj: dict[str, list[dict]] = {s_id: [] for s_id in stations_by_id}
	for record in rel_records:
		effective_vmax = record["vmax"]
		if record["status"] == "restricted" and record["restrictedVmax"]:
			effective_vmax = record["restrictedVmax"]
		adj[record["uId"]].append(
			{
				"to": record["vId"],
				"segmentId": record["segmentId"],
				"distKm": record["distKm"],
				"effectiveVmax": effective_vmax,
			}
		)

	goal_st = stations_by_id[to_station_id]

	pq: list[tuple[float, float, str]] = []
	g_scores: dict[str, float] = {from_station_id: 0.0}
	came_from: dict[str, tuple[str, dict]] = {}
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

		for edge in adj.get(u, []):
			v = edge["to"]
			effective_speed = min(edge["effectiveVmax"], vmax_train)
			travel_min = (edge["distKm"] / effective_speed) * 60.0
			stop_penalty = 1.0 if (is_regional and v != to_station_id) else 0.0
			tentative_g = g_curr + travel_min + stop_penalty

			if tentative_g < g_scores.get(v, float("inf")):
				g_scores[v] = tentative_g
				came_from[v] = (u, edge)
				v_st = stations_by_id[v]
				h = haversine_time_heuristic_min(
					v_st.lat, v_st.lon, goal_st.lat, goal_st.lon, vmax_train
				)
				heapq.heappush(pq, (tentative_g + h, tentative_g, v))

	if not found:
		return _not_found(
			from_station_id,
			to_station_id,
			train_type,
			len(explored_nodes),
			"Nie odnaleziono połączenia pomiędzy wskazanymi stacjami.",
		)

	curr = to_station_id
	path_ids = [curr]
	segment_ids: list[str] = []
	total_dist_km = 0.0
	while curr != from_station_id:
		prev, edge = came_from[curr]
		segment_ids.append(edge["segmentId"])
		total_dist_km += edge["distKm"]
		path_ids.append(prev)
		curr = prev

	path_ids.reverse()
	segment_ids.reverse()

	return FastestRouteResult(
		found=True,
		fromStation=from_station_id,
		toStation=to_station_id,
		trainType=train_type,
		path=[stations_by_id[sid] for sid in path_ids],
		segmentIds=segment_ids,
		totalTravelMin=round(g_scores[to_station_id], 2),
		totalDistKm=round(total_dist_km, 2),
		exploredNodesCount=len(explored_nodes),
	)
