import math

from app.core.haversine import haversine_distance_km, haversine_time_heuristic_min


def test_haversine_distance_known_points():
	# Katowice -> Gliwice, znana odległość w linii prostej ok. 25 km
	dist = haversine_distance_km(50.2576, 19.0175, 50.2977, 18.6714)
	assert 24.0 < dist < 26.0


def test_haversine_distance_zero_for_same_point():
	dist = haversine_distance_km(50.2576, 19.0175, 50.2576, 19.0175)
	assert dist == 0.0


def test_haversine_time_heuristic_matches_formula_and_is_admissible():
	lat1, lon1 = 50.2576, 19.0175
	lat2, lon2 = 50.2977, 18.6714
	dist = haversine_distance_km(lat1, lon1, lat2, lon2)
	h_min = haversine_time_heuristic_min(lat1, lon1, lat2, lon2, vmax_kmh=160.0)
	# h(n) dla A* musi być <= rzeczywistemu kosztowi -- przy linii prostej i vmax
	# sieci to z definicji dolne ograniczenie, więc porównujemy z tą samą formułą.
	assert math.isclose(h_min, (dist / 160.0) * 60.0)


def test_haversine_time_heuristic_defaults_when_vmax_invalid():
	h_default = haversine_time_heuristic_min(50.0, 19.0, 50.1, 19.1, vmax_kmh=0)
	h_explicit = haversine_time_heuristic_min(50.0, 19.0, 50.1, 19.1, vmax_kmh=160.0)
	assert math.isclose(h_default, h_explicit)
