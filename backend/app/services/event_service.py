import random
import uuid

from neo4j import Session

from app.core import config
from app.schemas.event import RailEventNode

_MESSAGES = {
	"line_failure": "Awaria sieci trakcyjnej na odcinku {a} – {b}.",
	"derailment": "Wykolejenie pociągu {train} na odcinku {a} – {b}.",
	"speed_restriction": "Ograniczenie prędkości do {vmax} km/h na odcinku {a} – {b}.",
	"signal_failure": "Awaria sterowania ruchem na stacji {station}.",
}


def _new_event_id() -> str:
	return uuid.uuid4().hex[:12]


def _station_name(session: Session, station_id: str) -> str:
	record = session.run(
		"MATCH (s:Station {id: $id}) RETURN s.name AS name", id=station_id
	).single()
	return record["name"] if record else station_id


def _pick_active_directed_edge(session: Session) -> dict | None:
	"""Losuje jedną, jeszcze nie 'zajętą' przez inne zdarzenie, aktywną skierowaną relację TRACK."""
	records = [
		dict(r)
		for r in session.run(
			"""
			MATCH (u:Station)-[r:TRACK {status: 'active'}]->(v:Station)
			WHERE r.active_event_id IS NULL
			RETURN r.segment_id AS segmentId, u.id AS fromId, v.id AS toId,
			       r.rail_tracks AS railTracks, r.vmax AS vmax
			"""
		)
	]
	return random.choice(records) if records else None


def pick_derailment_target(session: Session) -> dict | None:
	"""Losuje pociąg w drodze (status='running'), którego bieżący odcinek nie jest już zajęty."""
	records = [
		dict(r)
		for r in session.run(
			"""
			MATCH (t:Train {status: 'running'})
			WHERE t.delayed_by_event_id IS NULL AND t.current_segment_id IS NOT NULL
			MATCH (:Station {id: t.current_station_id})
			      -[r:TRACK {segment_id: t.current_segment_id}]->
			      (:Station {id: t.next_station_id})
			WHERE r.active_event_id IS NULL
			RETURN t.id AS trainId, t.current_segment_id AS segmentId,
			       t.current_station_id AS fromId, t.next_station_id AS toId,
			       r.rail_tracks AS railTracks, r.vmax AS vmax
			"""
		)
	]
	return random.choice(records) if records else None


def pick_signal_failure_target(session: Session) -> dict | None:
	"""Losuje stację bez już aktywnej awarii sterowania ruchem."""
	excluded = {
		r["stationId"]
		for r in session.run(
			"MATCH (e:RailEvent {status: 'active', type: 'signal_failure'}) "
			"RETURN e.station_id AS stationId"
		)
	}
	candidates = [
		dict(r)
		for r in session.run("MATCH (s:Station) RETURN s.id AS stationId, s.name AS name")
		if r["stationId"] not in excluded
	]
	return random.choice(candidates) if candidates else None


def _incident_active_edges(session: Session, station_id: str) -> list[dict]:
	records = session.run(
		"""
		MATCH (u:Station)-[r:TRACK {status: 'active'}]->(v:Station)
		WHERE r.active_event_id IS NULL AND (u.id = $stationId OR v.id = $stationId)
		RETURN r.segment_id AS segmentId, u.id AS fromId, v.id AS toId, r.vmax AS vmax
		""",
		stationId=station_id,
	)
	return [dict(r) for r in records]


def _expand_for_track_count(target: dict) -> list[dict]:
	"""Jednotorowy odcinek (rail_tracks<=1) dzieli fizyczny tor w obu kierunkach — awaria
	blokuje wtedy obie skierowane relacje. Dwutorowy — tylko wylosowany kierunek."""
	edges = [target]
	if target.get("railTracks", 2) <= 1:
		edges.append({**target, "fromId": target["toId"], "toId": target["fromId"]})
	return edges


def _set_edges_blocked(session: Session, edges: list[dict], event_id: str) -> None:
	session.run(
		"""
		UNWIND $edges AS e
		MATCH (:Station {id: e.fromId})-[r:TRACK {segment_id: e.segmentId}]->(:Station {id: e.toId})
		SET r.status = 'blocked', r.active_event_id = $eventId, r.restricted_vmax = NULL
		""",
		edges=[{"fromId": e["fromId"], "toId": e["toId"], "segmentId": e["segmentId"]} for e in edges],
		eventId=event_id,
	)


def _set_edges_restricted(
	session: Session, edges: list[dict], event_id: str, factor: float
) -> list[dict]:
	rows = [
		{
			"fromId": e["fromId"],
			"toId": e["toId"],
			"segmentId": e["segmentId"],
			"restrictedVmax": max(20, round(e["vmax"] * factor)),
		}
		for e in edges
	]
	session.run(
		"""
		UNWIND $edges AS e
		MATCH (:Station {id: e.fromId})-[r:TRACK {segment_id: e.segmentId}]->(:Station {id: e.toId})
		SET r.status = 'restricted', r.active_event_id = $eventId, r.restricted_vmax = e.restrictedVmax
		""",
		edges=rows,
		eventId=event_id,
	)
	return rows


def _build_event(
	event_id: str, event_type: str, severity: str, now: float, resolves_at: float, message: str, **context
) -> RailEventNode:
	return RailEventNode(
		id=event_id,
		type=event_type,
		severity=severity,
		status="active",
		startedAt=now,
		resolvesAt=resolves_at,
		resolvedAt=None,
		segmentId=context.get("segmentId"),
		fromStationId=context.get("fromStationId"),
		toStationId=context.get("toStationId"),
		stationId=context.get("stationId"),
		trainId=context.get("trainId"),
		restrictedVmax=context.get("restrictedVmax"),
		message=message,
	)


def _persist_event(session: Session, event: RailEventNode) -> None:
	session.run(
		"""
		CREATE (e:RailEvent {
			id: $id, type: $type, severity: $severity, status: $status,
			segment_id: $segmentId, from_station_id: $fromStationId, to_station_id: $toStationId,
			station_id: $stationId, train_id: $trainId, restricted_vmax: $restrictedVmax,
			message: $message, started_at: $startedAt, resolves_at: $resolvesAt, resolved_at: $resolvedAt
		})
		""",
		**event.model_dump(),
	)
	if event.trainId:
		session.run(
			"""
			MATCH (e:RailEvent {id: $eventId}), (t:Train {id: $trainId})
			CREATE (e)-[:AFFECTS]->(t)
			""",
			eventId=event.id,
			trainId=event.trainId,
		)


def create_event(session: Session, event_type: str, now: float) -> RailEventNode | None:
	duration = random.uniform(
		config.SIM_EVENT_DURATION_REAL_S_MIN, config.SIM_EVENT_DURATION_REAL_S_MAX
	)
	resolves_at = now + duration
	event_id = _new_event_id()

	if event_type == "line_failure":
		target = _pick_active_directed_edge(session)
		if not target:
			return None
		from_name = _station_name(session, target["fromId"])
		to_name = _station_name(session, target["toId"])
		event = _build_event(
			event_id, "line_failure", "major", now, resolves_at,
			message=_MESSAGES["line_failure"].format(a=from_name, b=to_name),
			segmentId=target["segmentId"], fromStationId=target["fromId"], toStationId=target["toId"],
		)
		_persist_event(session, event)
		_set_edges_blocked(session, _expand_for_track_count(target), event_id)
		return event

	if event_type == "derailment":
		target = pick_derailment_target(session)
		if not target:
			return None
		from_name = _station_name(session, target["fromId"])
		to_name = _station_name(session, target["toId"])
		event = _build_event(
			event_id, "derailment", "major", now, resolves_at,
			message=_MESSAGES["derailment"].format(train=target["trainId"], a=from_name, b=to_name),
			segmentId=target["segmentId"], fromStationId=target["fromId"], toStationId=target["toId"],
			trainId=target["trainId"],
		)
		_persist_event(session, event)
		_set_edges_blocked(session, _expand_for_track_count(target), event_id)
		session.run(
			"MATCH (t:Train {id: $trainId}) SET t.status = 'derailed', t.delayed_by_event_id = $eventId",
			trainId=target["trainId"],
			eventId=event_id,
		)
		return event

	if event_type == "speed_restriction":
		target = _pick_active_directed_edge(session)
		if not target:
			return None
		rows = _set_edges_restricted(
			session, _expand_for_track_count(target), event_id, config.SIM_SPEED_RESTRICTION_FACTOR
		)
		restricted_vmax = rows[0]["restrictedVmax"]
		from_name = _station_name(session, target["fromId"])
		to_name = _station_name(session, target["toId"])
		event = _build_event(
			event_id, "speed_restriction", "minor", now, resolves_at,
			message=_MESSAGES["speed_restriction"].format(vmax=restricted_vmax, a=from_name, b=to_name),
			segmentId=target["segmentId"], fromStationId=target["fromId"], toStationId=target["toId"],
			restrictedVmax=restricted_vmax,
		)
		_persist_event(session, event)
		return event

	if event_type == "signal_failure":
		target = pick_signal_failure_target(session)
		if not target:
			return None
		edges = _incident_active_edges(session, target["stationId"])
		if not edges:
			return None
		event = _build_event(
			event_id, "signal_failure", "minor", now, resolves_at,
			message=_MESSAGES["signal_failure"].format(station=target["name"]),
			stationId=target["stationId"],
		)
		_persist_event(session, event)
		_set_edges_restricted(session, edges, event_id, config.SIM_SPEED_RESTRICTION_FACTOR)
		return event

	return None


def maybe_create_random_event(session: Session, now: float) -> RailEventNode | None:
	types = list(config.SIM_EVENT_TYPE_WEIGHTS.keys())
	weights = list(config.SIM_EVENT_TYPE_WEIGHTS.values())
	event_type = random.choices(types, weights=weights, k=1)[0]
	return create_event(session, event_type, now)


def resolve_due_events(session: Session, now: float) -> list[dict]:
	due = [
		dict(r)
		for r in session.run(
			"""
			MATCH (e:RailEvent {status: 'active'})
			WHERE e.resolves_at <= $now
			RETURN e.id AS id, e.type AS type, e.train_id AS trainId
			""",
			now=now,
		)
	]
	for item in due:
		session.run(
			"""
			MATCH ()-[r:TRACK {active_event_id: $eventId}]->()
			SET r.status = 'active', r.active_event_id = NULL, r.restricted_vmax = NULL
			""",
			eventId=item["id"],
		)
		session.run(
			"MATCH (e:RailEvent {id: $eventId}) SET e.status = 'resolved', e.resolved_at = $now",
			eventId=item["id"],
			now=now,
		)
		if item["type"] == "derailment" and item["trainId"]:
			session.run(
				"""
				MATCH (t:Train {id: $trainId})
				SET t.status = 'waiting', t.progress = 0.0, t.current_segment_id = NULL,
				    t.next_station_id = NULL, t.route_station_ids = [], t.route_segment_ids = [],
				    t.route_index = 0, t.delayed_by_event_id = NULL
				""",
				trainId=item["trainId"],
			)
	return due


def _event_from_node(node) -> RailEventNode:
	return RailEventNode(
		id=node["id"],
		type=node["type"],
		severity=node["severity"],
		status=node["status"],
		segmentId=node.get("segment_id"),
		fromStationId=node.get("from_station_id"),
		toStationId=node.get("to_station_id"),
		stationId=node.get("station_id"),
		trainId=node.get("train_id"),
		restrictedVmax=node.get("restricted_vmax"),
		message=node["message"],
		startedAt=node["started_at"],
		resolvesAt=node["resolves_at"],
		resolvedAt=node.get("resolved_at"),
	)


def load_events(session: Session, status: str | None = None) -> list[RailEventNode]:
	if status:
		records = session.run(
			"MATCH (e:RailEvent {status: $status}) RETURN e ORDER BY e.started_at DESC LIMIT 50",
			status=status,
		)
	else:
		records = session.run("MATCH (e:RailEvent) RETURN e ORDER BY e.started_at DESC LIMIT 50")
	return [_event_from_node(r["e"]) for r in records]
