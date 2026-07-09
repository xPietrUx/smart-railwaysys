import time
from typing import Optional
from neo4j import Driver
from app.schemas.simulation import TrainCreateRequest, TrainState, SimulationStateResponse
from app.services.routing_service import find_fastest_route_astar

ACTIVE_TRAINS: dict[str, TrainState] = {}


def get_all_trains() -> list[TrainState]:
	return list(ACTIVE_TRAINS.values())


def clear_all_trains() -> int:
	count = len(ACTIVE_TRAINS)
	ACTIVE_TRAINS.clear()
	return count


def add_train(driver: Driver, payload: TrainCreateRequest) -> TrainState:
	speed = payload.speedKmh
	if speed is None or speed <= 0:
		speeds = {"IC": 140, "REGIONAL": 100, "FREIGHT": 70}
		speed = speeds.get(payload.trainType.upper(), 100)

	with driver.session() as session:
		route = find_fastest_route_astar(
			session=session,
			from_station_id=payload.fromStation,
			to_station_id=payload.toStation,
			train_type=payload.trainType,
		)

	if not route or not route.path:
		raise ValueError(f"Brak trasy A* z {payload.fromStation} do {payload.toStation}")

	next_station = route.path[1].id if len(route.path) > 1 else None
	current_seg = route.segments[0].segmentId if len(route.segments) > 0 else None
	status = "running" if next_station else "arrived"

	train = TrainState(
		trainId=payload.trainId,
		name=payload.name,
		trainType=payload.trainType.upper(),
		fromStation=payload.fromStation,
		toStation=payload.toStation,
		currentStationId=payload.fromStation,
		nextStationId=next_station,
		currentSegmentId=current_seg,
		progress=0.0,
		status=status,
		route=route,
		currentRouteIndex=0,
		speedKmh=speed,
		rerouteMessage=None,
	)
	ACTIVE_TRAINS[train.trainId] = train
	return train


def spawn_demo_trains(driver: Driver) -> list[TrainState]:
	clear_all_trains()
	demos = [
		TrainCreateRequest(
			trainId="IC_WYSPIANSKI",
			name="IC Wyspiański",
			trainType="IC",
			fromStation="KAT",
			toStation="WRO",
			speedKmh=140,
		),
		TrainCreateRequest(
			trainId="REG_SLASKI",
			name="KŚ Regionalny",
			trainType="REGIONAL",
			fromStation="KAT",
			toStation="GLI",
			speedKmh=100,
		),
		TrainCreateRequest(
			trainId="TOW_CARGO",
			name="PKP Cargo Towarowy",
			trainType="FREIGHT",
			fromStation="TCH",
			toStation="OPO",
			speedKmh=70,
		),
	]
	created = []
	for req in demos:
		try:
			created.append(add_train(driver, req))
		except Exception:
			pass
	return created


def tick_simulation(
	driver: Driver, delta_sec: float = 1.0, time_scale: float = 60.0
) -> SimulationStateResponse:
	for train in ACTIVE_TRAINS.values():
		if train.status in ("arrived", "blocked"):
			continue

		if not train.route or train.currentRouteIndex >= len(train.route.segments):
			train.status = "arrived"
			train.progress = 1.0
			continue

		seg_id = train.currentSegmentId
		# Przyjmujemy domyślny dystans odcinka 20 km jeśli brak szczegółów
		dist_km = 20.0
		if train.route and train.currentRouteIndex < len(train.route.segments):
			# Zwiększamy progress (time_scale 60 = 1 sekunda w symulatorze to 1 minuta w rzeczywistości)
			speed = train.speedKmh
			dist_per_sec_km = (speed * time_scale) / 3600.0
			delta_prog = (dist_per_sec_km * delta_sec) / dist_km
			train.progress += delta_prog

		if train.progress >= 1.0:
			train.currentRouteIndex += 1
			if train.route and train.currentRouteIndex < len(train.route.segments):
				train.currentStationId = train.route.path[train.currentRouteIndex].id
				train.nextStationId = train.route.path[train.currentRouteIndex + 1].id
				train.currentSegmentId = train.route.segments[train.currentRouteIndex].segmentId
				train.progress = 0.0
			else:
				if train.route and len(train.route.path) > 0:
					train.currentStationId = train.route.path[-1].id
				train.nextStationId = None
				train.currentSegmentId = None
				train.progress = 1.0
				train.status = "arrived"

	return SimulationStateResponse(
		trains=list(ACTIVE_TRAINS.values()), timestamp=time.time()
	)


def check_and_reroute_trains_on_blockade(
	driver: Driver, blocked_segment_id: str
) -> list[str]:
	rerouted_ids = []
	for train in ACTIVE_TRAINS.values():
		if train.status in ("arrived", "blocked") or not train.route:
			continue

		remaining_segments = [seg.segmentId for seg in train.route.segments[train.currentRouteIndex :]]
		if blocked_segment_id in remaining_segments:
			# Wywołanie natychmiastowego reroutingu A* z obecnej stacji do stacji docelowej
			with driver.session() as session:
				new_route = find_fastest_route_astar(
					session=session,
					from_station_id=train.currentStationId,
					to_station_id=train.toStation,
					train_type=train.trainType,
				)

			if new_route and new_route.path:
				train.route = new_route
				train.currentRouteIndex = 0
				train.nextStationId = (
					new_route.path[1].id if len(new_route.path) > 1 else None
				)
				train.currentSegmentId = (
					new_route.segments[0].segmentId if len(new_route.segments) > 0 else None
				)
				train.progress = 0.0
				train.status = "rerouted"
				train.rerouteMessage = (
					f"AWARIA na {blocked_segment_id}! A* przeliczył nową trasę: "
					f"{' -> '.join(st.id for st in new_route.path)} (czas: {new_route.totalTravelMin} min)"
				)
				rerouted_ids.append(train.trainId)
			else:
				train.status = "blocked"
				train.rerouteMessage = (
					f"AWARIA na {blocked_segment_id}! Brak alternatywnej trasy A* do {train.toStation}."
				)
				rerouted_ids.append(train.trainId)

	return rerouted_ids
