import math
from unittest.mock import MagicMock

from app.services.routing_service import find_fastest_route_astar


def _station_row(station_id, lat, lon):
	return {
		"id": station_id, "name": station_id, "lat": lat, "lon": lon,
		"type": "przelotowa", "platforms": 2, "tracks": 4, "daily_trains": 50,
	}


def _make_session(station_rows, edge_rows):
	def run_side_effect(query, **params):
		if "MATCH (n:Station) RETURN n" in query:
			return [{"n": dict(row)} for row in station_rows]
		if "MATCH (u:Station)-[r:TRACK]->(v:Station)" in query:
			return [dict(row) for row in edge_rows]
		raise AssertionError(f"Nieoczekiwane zapytanie w teście: {query}")

	session = MagicMock()
	session.run.side_effect = run_side_effect
	return session


def test_blocked_direction_does_not_affect_opposite_direction():
	# Odcinek dwutorowy: A->B jest odfiltrowane (symuluje status='blocked' -- taki
	# wiersz nigdy nie przejdzie przez WHERE r.status IN ['active','restricted'] w
	# prawdziwym Cypherze, więc go tu po prostu pomijamy), B->A zostaje aktywne.
	stations = [_station_row("A", 50.0, 19.0), _station_row("B", 50.1, 19.0)]
	edges = [
		{"uId": "B", "vId": "A", "segmentId": "SEG1", "distKm": 10.0, "vmax": 100,
		 "status": "active", "restrictedVmax": None},
	]
	session = _make_session(stations, edges)

	forward = find_fastest_route_astar(session, "A", "B", train_type="IC")
	assert forward.found is False

	backward = find_fastest_route_astar(session, "B", "A", train_type="IC")
	assert backward.found is True
	assert backward.segmentIds == ["SEG1"]


def test_restricted_segment_stays_routable_with_reduced_effective_speed():
	stations = [_station_row("A", 50.0, 19.0), _station_row("B", 50.1, 19.0)]
	edges = [
		{"uId": "A", "vId": "B", "segmentId": "SEG1", "distKm": 10.0, "vmax": 100,
		 "status": "restricted", "restrictedVmax": 40},
	]
	session = _make_session(stations, edges)

	route = find_fastest_route_astar(session, "A", "B", train_type="IC")

	assert route.found is True
	# 10km przy 40 km/h (restricted_vmax), nie przy 100 km/h (zwykłe vmax) => 15 min
	assert math.isclose(route.totalTravelMin, 15.0, rel_tol=1e-6)


def test_missing_station_reports_not_found_without_crashing():
	stations = [_station_row("A", 50.0, 19.0)]
	session = _make_session(stations, [])

	route = find_fastest_route_astar(session, "A", "NIEISTNIEJACA", train_type="IC")

	assert route.found is False
	assert route.path == []
