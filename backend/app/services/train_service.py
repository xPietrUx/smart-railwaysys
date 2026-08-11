import random
import time

from neo4j import Driver, Session

from app.core import config
from app.schemas.train import TrainNode
from app.services import event_service, scenario_service
from app.services.routing_service import find_fastest_route_astar


def _load_trains(session: Session) -> list[dict]:
	return [dict(record["t"]) for record in session.run("MATCH (t:Train) RETURN t")]


def _load_directed_edge_lookup(session: Session) -> dict[tuple[str, str], dict]:
	records = session.run(
		"""
		MATCH (u:Station)-[r:TRACK]->(v:Station)
		RETURN u.id AS fromId, v.id AS toId, r.dist_km AS distKm, r.vmax AS vmax,
		       r.status AS status, r.restricted_vmax AS restrictedVmax
		"""
	)
	lookup: dict[tuple[str, str], dict] = {}
	for record in records:
		effective_vmax = record["vmax"]
		if record["status"] == "restricted" and record["restrictedVmax"]:
			effective_vmax = record["restrictedVmax"]
		lookup[(record["fromId"], record["toId"])] = {
			"distKm": record["distKm"],
			"effectiveVmax": effective_vmax,
		}
	return lookup


def _start_dwell(train: dict, now: float) -> dict:
	train["status"] = "dwelling"
	train["dwell_until"] = now + random.uniform(
		config.SIM_DWELL_REAL_SECONDS_MIN, config.SIM_DWELL_REAL_SECONDS_MAX
	)
	train["next_station_id"] = None
	train["current_segment_id"] = None
	train["progress"] = 0.0
	train["route_station_ids"] = []
	train["route_segment_ids"] = []
	train["route_index"] = 0
	return train


def dispatch_or_wait(train: dict, session: Session, now: float) -> dict:
	"""Liczy trasę A* z current_station_id do stacji odpowiedniej dla aktualnego
	kierunku. Współdzielona przez: pierwszy start, odjazd po przerwie i retry
	pociągów oczekujących (status='waiting', sprawdzanych ponownie co tick)."""
	target_station = (
		train["destination_station_id"]
		if train["direction"] == "outbound"
		else train["origin_station_id"]
	)
	if train["current_station_id"] == target_station:
		return _start_dwell(train, now)

	route = find_fastest_route_astar(
		session,
		train["current_station_id"],
		target_station,
		train_type=train["type"],
		custom_vmax=train["vmax"],
	)

	if not route.found or len(route.path) < 2:
		train["status"] = "waiting"
		train["route_station_ids"] = []
		train["route_segment_ids"] = []
		train["route_index"] = 0
		train["next_station_id"] = None
		train["current_segment_id"] = None
		return train

	train["status"] = "running"
	train["route_station_ids"] = [station.id for station in route.path]
	train["route_segment_ids"] = route.segmentIds
	train["route_index"] = 0
	train["next_station_id"] = route.path[1].id
	train["current_segment_id"] = route.segmentIds[0]
	train["progress"] = 0.0
	return train


def advance_train(train: dict, dt_sim_s: float, now: float, edge_lookup: dict) -> dict:
	edge = edge_lookup.get((train["current_station_id"], train["next_station_id"]))
	if edge is None or edge["distKm"] <= 0:
		return train

	speed_kmh = min(edge["effectiveVmax"], train["vmax"])
	dist_per_sim_s_km = speed_kmh / 3600.0
	delta_progress = (dist_per_sim_s_km * dt_sim_s) / edge["distKm"]
	train["progress"] = min(1.0, train["progress"] + delta_progress)

	if train["progress"] < 1.0:
		return train

	train["current_station_id"] = train["next_station_id"]
	train["route_index"] += 1
	route_station_ids = train.get("route_station_ids") or []
	route_segment_ids = train.get("route_segment_ids") or []
	idx = train["route_index"]

	if idx < len(route_segment_ids):
		train["next_station_id"] = route_station_ids[idx + 1]
		train["current_segment_id"] = route_segment_ids[idx]
		train["progress"] = 0.0
		return train

	return _start_dwell(train, now)


def _halt_waiting(train: dict) -> dict:
	train["status"] = "waiting"
	train["progress"] = 0.0
	train["current_segment_id"] = None
	train["next_station_id"] = None
	train["route_station_ids"] = []
	train["route_segment_ids"] = []
	train["route_index"] = 0
	return train


def _replan_from_next_station(train: dict, session: Session) -> dict:
	"""Bieżący (wciąż aktywny) odcinek trasa zostaje dokończona bez przerywania —
	zablokowany odcinek jest gdzieś dalej w planie, więc przeliczamy tylko resztę
	trasy od stacji, do której pociąg właśnie zmierza."""
	target_station = (
		train["destination_station_id"]
		if train["direction"] == "outbound"
		else train["origin_station_id"]
	)
	route = find_fastest_route_astar(
		session,
		train["next_station_id"],
		target_station,
		train_type=train["type"],
		custom_vmax=train["vmax"],
	)
	if route.found:
		train["route_station_ids"] = [train["current_station_id"]] + [s.id for s in route.path]
		train["route_segment_ids"] = [train["current_segment_id"]] + route.segmentIds
		train["route_index"] = 0
	return train


def reroute_affected_trains(
	trains: list[dict], session: Session, segment_id: str
) -> list[dict]:
	updated = []
	for train in trains:
		if train["status"] != "running":
			updated.append(train)
			continue

		remaining = (train.get("route_segment_ids") or [])[train.get("route_index") or 0 :]
		if segment_id not in remaining:
			updated.append(train)
			continue

		if train.get("current_segment_id") == segment_id:
			updated.append(_halt_waiting(train))
		else:
			updated.append(_replan_from_next_station(train, session))
	return updated


def _advance_or_dispatch_one(
	train: dict, session: Session, now: float, dt_sim_s: float, edge_lookup: dict
) -> dict:
	if train["status"] == "dwelling":
		if train.get("dwell_until") is not None and now >= train["dwell_until"]:
			train["direction"] = "return" if train["direction"] == "outbound" else "outbound"
			train["dwell_until"] = None
			return dispatch_or_wait(train, session, now)
		return train

	if train["status"] == "waiting":
		return dispatch_or_wait(train, session, now)

	if train["status"] == "running":
		return advance_train(train, dt_sim_s, now, edge_lookup)

	# 'derailed' — zamrożony w miejscu, czeka na resolve_due_events
	return train


def _to_write_row(train: dict, now: float) -> dict:
	return {
		"id": train["id"],
		"direction": train["direction"],
		"currentStationId": train["current_station_id"],
		"nextStationId": train.get("next_station_id"),
		"currentSegmentId": train.get("current_segment_id"),
		"progress": train["progress"],
		"status": train["status"],
		"routeStationIds": train.get("route_station_ids") or [],
		"routeSegmentIds": train.get("route_segment_ids") or [],
		"routeIndex": train.get("route_index") or 0,
		"dwellUntil": train.get("dwell_until"),
		"delayedByEventId": train.get("delayed_by_event_id"),
		"updatedAt": now,
	}


def _write_back_trains(session: Session, trains: list[dict], now: float) -> None:
	if not trains:
		return
	session.run(
		"""
		UNWIND $rows AS row
		MATCH (t:Train {id: row.id})
		SET t.direction = row.direction,
		    t.current_station_id = row.currentStationId,
		    t.next_station_id = row.nextStationId,
		    t.current_segment_id = row.currentSegmentId,
		    t.progress = row.progress,
		    t.status = row.status,
		    t.route_station_ids = row.routeStationIds,
		    t.route_segment_ids = row.routeSegmentIds,
		    t.route_index = row.routeIndex,
		    t.dwell_until = row.dwellUntil,
		    t.delayed_by_event_id = row.delayedByEventId,
		    t.updated_at = row.updatedAt
		""",
		rows=[_to_write_row(t, now) for t in trains],
	)


def _train_node_from_dict(train: dict, now: float) -> TrainNode:
	return TrainNode(
		id=train["id"],
		name=train["name"],
		type=train["type"],
		originStationId=train["origin_station_id"],
		destinationStationId=train["destination_station_id"],
		direction=train["direction"],
		currentStationId=train["current_station_id"],
		nextStationId=train.get("next_station_id"),
		currentSegmentId=train.get("current_segment_id"),
		progress=train["progress"],
		status=train["status"],
		routeStationIds=train.get("route_station_ids") or [],
		routeSegmentIds=train.get("route_segment_ids") or [],
		routeIndex=train.get("route_index") or 0,
		vmax=train["vmax"],
		priority=train["priority"],
		massTonnes=train["mass_tonnes"],
		lengthM=train["length_m"],
		accel=train["accel"],
		decel=train["decel"],
		dwellUntil=train.get("dwell_until"),
		delayedByEventId=train.get("delayed_by_event_id"),
		updatedAt=train.get("updated_at") or now,
	)


def load_trains_snapshot(driver: Driver) -> list[TrainNode]:
	with driver.session() as session:
		trains = _load_trains(session)
	now = time.time()
	return [_train_node_from_dict(t, now) for t in trains]


def run_tick_sync(driver: Driver, app_state) -> dict:
	"""Wykonuje jeden krok symulacji: (1) rozwiązuje zdarzenia, którym minął czas,
	(2) wprowadza na sieć pociągi rozkładu, którym minął czas odjazdu, (3) przesuwa/
	dysponuje pociągi względem odświeżonego stanu torów, (4) ewentualnie losuje
	jedno nowe zdarzenie i przelicza trasy dotkniętych pociągów. Przy wstrzymanej
	symulacji niczego nie mutuje — tylko odczytuje bieżący stan do broadcastu."""
	now = time.time()
	paused = getattr(app_state, "sim_paused", False)

	# Realny czas działania symulacji: suma odstępów między tickami z pominięciem
	# pauz (tick w pauzie tylko przesuwa punkt odniesienia, nic nie dolicza).
	last_tick_at = getattr(app_state, "sim_last_tick_at", None)
	if not paused and last_tick_at is not None:
		app_state.sim_elapsed_real_s = (
			getattr(app_state, "sim_elapsed_real_s", 0.0) + (now - last_tick_at)
		)
	app_state.sim_last_tick_at = now

	speed = getattr(app_state, "sim_speed", 1.0)
	elapsed_real_s = getattr(app_state, "sim_elapsed_real_s", 0.0)

	if paused:
		with driver.session() as session:
			trains = _load_trains(session)
			events = event_service.load_events(session)
		return {
			"trains": [_train_node_from_dict(t, now) for t in trains],
			"events": events,
			"scenario": scenario_service.active_info(app_state),
			"paused": True,
			"speed": speed,
			"elapsedRealS": elapsed_real_s,
			"timestamp": now,
		}

	# Mnożnik tempa (0.5x–2x) skaluje wyłącznie postęp pociągów — timery liczone
	# w realnych sekundach (przerwy, zdarzenia) celowo biegną niezależnie.
	dt_sim_s = config.SIM_TICK_INTERVAL_S * config.SIM_TIME_SCALE * speed

	with driver.session() as session:
		event_service.resolve_due_events(session, now)
		scenario_service.apply_due_spawns(session, app_state, now)

		edge_lookup = _load_directed_edge_lookup(session)
		trains = _load_trains(session)
		trains = [
			_advance_or_dispatch_one(train, session, now, dt_sim_s, edge_lookup)
			for train in trains
		]

		new_event = None
		if now >= app_state.next_event_at:
			new_event = event_service.maybe_create_random_event(session, now)
			app_state.next_event_at = now + random.expovariate(
				1.0 / config.SIM_EVENT_MEAN_INTERVAL_REAL_S
			)

		if new_event is not None and new_event.segmentId:
			trains = reroute_affected_trains(trains, session, new_event.segmentId)

		_write_back_trains(session, trains, now)
		events = event_service.load_events(session)

	return {
		"trains": [_train_node_from_dict(t, now) for t in trains],
		"events": events,
		"scenario": scenario_service.active_info(app_state),
		"paused": False,
		"speed": speed,
		"elapsedRealS": elapsed_real_s,
		"timestamp": now,
	}
