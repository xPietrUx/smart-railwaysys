import math
import pytest
from unittest.mock import MagicMock

from app.core.haversine import haversine_distance_km, haversine_time_heuristic_min
from app.services.routing_service import find_fastest_route_astar, get_train_vmax


def test_haversine_distance_known_points():
	# Katowice lat=50.2576, lon=19.0175
	# Gliwice lat=50.2977, lon=18.6714
	dist = haversine_distance_km(50.2576, 19.0175, 50.2977, 18.6714)
	# Oczekiwana odległość sferyczna w linii prostej ok. 25.0 km
	assert 24.0 < dist < 26.0


def test_haversine_time_heuristic_admissible():
	lat1, lon1 = 50.2576, 19.0175
	lat2, lon2 = 50.2977, 18.6714
	# Przy vmax = 160 km/h
	dist = haversine_distance_km(lat1, lon1, lat2, lon2)
	h_min = haversine_time_heuristic_min(lat1, lon1, lat2, lon2, vmax_kmh=160.0)
	assert math.isclose(h_min, (dist / 160.0) * 60.0)


def test_get_train_vmax():
	assert get_train_vmax("IC") == 160.0
	assert get_train_vmax("regional") == 120.0
	assert get_train_vmax("freight") == 80.0
	assert get_train_vmax("IC", custom_vmax=200) == 200.0


def test_find_fastest_route_astar():
	mock_session = MagicMock()

	# Stacje: KAT -> ZAB -> GLI (szybciej) oraz KAT -> CHO -> GLI (wolniej)
	mock_stations = [
		{"id": "KAT", "name": "Katowice", "lat": 50.25, "lon": 19.01, "type": "węzeł", "platforms": 6, "tracks": 14, "daily_trains": 450},
		{"id": "ZAB", "name": "Zabrze", "lat": 50.30, "lon": 18.77, "type": "przelotowa", "platforms": 3, "tracks": 6, "daily_trains": 180},
		{"id": "GLI", "name": "Gliwice", "lat": 50.29, "lon": 18.67, "type": "węzeł", "platforms": 5, "tracks": 12, "daily_trains": 320},
	]

	mock_station_records = [{"n": s} for s in mock_stations]

	class MockRel:
		def __init__(self, id_val, props):
			self.id = id_val
			self.props = props
		def __getitem__(self, key):
			return self.props[key]
		def get(self, key, default=None):
			return self.props.get(key, default)
		def __iter__(self):
			return iter(self.props.items())

	mock_rels = [
		# KAT -> ZAB (dist=15km, vmax=160)
		{"u": mock_stations[0], "v": mock_stations[1], "r": MockRel(1, {"segment_id": "S1", "line": 1, "dist_km": 15.0, "vmax": 160, "rail_tracks": 2, "travel_min": 6, "status": "active", "delay_min": 0.0})},
		# ZAB -> GLI (dist=10km, vmax=160)
		{"u": mock_stations[1], "v": mock_stations[2], "r": MockRel(2, {"segment_id": "S2", "line": 1, "dist_km": 10.0, "vmax": 160, "rail_tracks": 2, "travel_min": 4, "status": "active", "delay_min": 0.0})},
	]

	def run_side_effect(query, *args, **kwargs):
		if "MATCH (n:Station)" in query:
			return mock_station_records
		elif "MATCH (u:Station)-[r:TRACK]->(v:Station)" in query:
			return mock_rels
		return []

	mock_session.run.side_effect = run_side_effect

	res = find_fastest_route_astar(mock_session, "KAT", "GLI", train_type="IC")
	assert res.found is True
	assert res.fromStation == "KAT"
	assert res.toStation == "GLI"
	assert len(res.path) == 3
	assert res.path[0].id == "KAT"
	assert res.path[-1].id == "GLI"
	assert res.algorithm == "A*"
	assert res.exploredNodesCount > 0
