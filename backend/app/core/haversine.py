import math


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	"""
	Oblicza odległość sferyczną w kilometrach pomiędzy dwoma punktami (lat1, lon1) i (lat2, lon2)
	przy użyciu matematycznego wzoru Haversine'a.
	"""
	r_earth_km = 6371.0

	phi1 = math.radians(lat1)
	phi2 = math.radians(lat2)
	delta_phi = math.radians(lat2 - lat1)
	delta_lambda = math.radians(lon2 - lon1)

	a = (
		math.sin(delta_phi / 2.0) ** 2
		+ math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
	)
	c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

	return r_earth_km * c


def haversine_time_heuristic_min(
	lat1: float,
	lon1: float,
	lat2: float,
	lon2: float,
	vmax_kmh: float = 160.0,
) -> float:
	"""
	Oblicza dolne, optymistyczne oszacowanie czasu przejazdu w minutach (heurystyka h(n) dla A*)
	na podstawie odległości w linii prostej i maksymalnej prędkości w sieci.
	Gwarantuje admisyjność heurystyki (h(n) <= h*(n)).
	"""
	if vmax_kmh <= 0:
		vmax_kmh = 160.0
	dist_km = haversine_distance_km(lat1, lon1, lat2, lon2)
	return (dist_km / vmax_kmh) * 60.0
