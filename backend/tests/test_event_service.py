from app.services.event_service import (
	_expand_for_track_count,
	_pick_active_directed_edge,
	create_event,
)


class FakeResult(list):
	"""Prawdziwy neo4j Result obsługuje zarówno iterację, jak i .single() --
	zwykła lista dostaje tu .single() doniesione, żeby zachowanie się zgadzało."""

	def single(self):
		return self[0] if self else None


class FakeSession:
	"""Minimalna, celowo prosta 'sesja' na potrzeby testów event_service: dopasowuje
	zapytania po charakterystycznym fragmencie tekstu i zwraca przygotowane dane.
	Zapisuje wszystkie wywołania, żeby można było sprawdzić, co dokładnie zostało
	wysłane do bazy (np. ile krawędzi trafiło do UNWIND przy blokadzie).

	Uwaga na kolejność dopasowań: kilka prawdziwych zapytań w event_service.py
	dzieli ten sam prefiks tekstu (np. _pick_active_directed_edge i
	_incident_active_edges obie zaczynają się od tego samego MATCH na TRACK), więc
	bardziej szczegółowe markery muszą być sprawdzane przed bardziej ogólnymi."""

	def __init__(
		self,
		station_names=None,
		edge_rows=None,
		derailment_rows=None,
		signal_targets=None,
		incident_edges=None,
	):
		self.station_names = station_names or {}
		self.edge_rows = edge_rows or []
		self.derailment_rows = derailment_rows or []
		self.signal_targets = signal_targets or []
		self.incident_edges = incident_edges or []
		self.calls: list[tuple[str, dict]] = []

	def run(self, query, **params):
		self.calls.append((query, params))

		if "MATCH (s:Station {id: $id}) RETURN s.name" in query:
			name = self.station_names.get(params["id"], params["id"])
			return FakeResult([{"name": name}])

		if "(u.id = $stationId OR v.id = $stationId)" in query:
			return FakeResult(self.incident_edges)

		if "MATCH (u:Station)-[r:TRACK {status: 'active'}]->(v:Station)" in query:
			return FakeResult(self.edge_rows)

		if "MATCH (t:Train {status: 'running'})" in query:
			return FakeResult(self.derailment_rows)

		if "MATCH (e:RailEvent {status: 'active', type: 'signal_failure'})" in query:
			return FakeResult([])

		if "MATCH (s:Station) RETURN s.id AS stationId" in query:
			return FakeResult(self.signal_targets)

		# CREATE / SET / UNWIND -- zapisy, których wynik nigdy nie jest odczytywany
		return []


def test_expand_for_track_count_single_track_blocks_both_directions():
	target = {"segmentId": "SEG1", "fromId": "A", "toId": "B", "railTracks": 1, "vmax": 100}
	edges = _expand_for_track_count(target)
	assert len(edges) == 2
	assert {(e["fromId"], e["toId"]) for e in edges} == {("A", "B"), ("B", "A")}


def test_expand_for_track_count_double_track_blocks_one_direction_only():
	target = {"segmentId": "SEG1", "fromId": "A", "toId": "B", "railTracks": 2, "vmax": 100}
	edges = _expand_for_track_count(target)
	assert len(edges) == 1
	assert edges[0]["fromId"] == "A" and edges[0]["toId"] == "B"


def test_line_failure_on_single_track_segment_blocks_both_directions():
	session = FakeSession(
		station_names={"A": "Stacja A", "B": "Stacja B"},
		edge_rows=[
			{"segmentId": "SEG1", "fromId": "A", "toId": "B", "railTracks": 1, "vmax": 90},
		],
	)
	event = create_event(session, "line_failure", now=1000.0)

	assert event is not None
	assert event.type == "line_failure"

	block_calls = [c for c in session.calls if "SET r.status = 'blocked'" in c[0]]
	assert len(block_calls) == 1
	assert len(block_calls[0][1]["edges"]) == 2


def test_line_failure_on_double_track_segment_blocks_one_direction():
	session = FakeSession(
		station_names={"A": "Stacja A", "B": "Stacja B"},
		edge_rows=[
			{"segmentId": "SEG1", "fromId": "A", "toId": "B", "railTracks": 2, "vmax": 120},
		],
	)
	event = create_event(session, "line_failure", now=1000.0)

	assert event is not None
	block_calls = [c for c in session.calls if "SET r.status = 'blocked'" in c[0]]
	assert len(block_calls) == 1
	assert len(block_calls[0][1]["edges"]) == 1


def test_create_event_returns_none_gracefully_when_no_target_available():
	session = FakeSession(edge_rows=[])
	event = create_event(session, "line_failure", now=1000.0)
	assert event is None


def test_pick_active_directed_edge_query_excludes_already_claimed_segments():
	session = FakeSession(
		edge_rows=[{"segmentId": "SEG1", "fromId": "A", "toId": "B", "railTracks": 2, "vmax": 100}]
	)
	target = _pick_active_directed_edge(session)

	assert target is not None
	edge_query = session.calls[0][0]
	assert "r.active_event_id IS NULL" in edge_query


def test_derailment_sets_train_status_and_links_event():
	session = FakeSession(
		station_names={"A": "Stacja A", "B": "Stacja B"},
		derailment_rows=[
			{"trainId": "T1", "segmentId": "SEG1", "fromId": "A", "toId": "B",
			 "railTracks": 2, "vmax": 100},
		],
	)
	event = create_event(session, "derailment", now=1000.0)

	assert event is not None
	assert event.type == "derailment"
	assert event.trainId == "T1"

	derail_calls = [c for c in session.calls if "SET t.status = 'derailed'" in c[0]]
	assert len(derail_calls) == 1
	assert derail_calls[0][1]["trainId"] == "T1"
	assert derail_calls[0][1]["eventId"] == event.id


def test_signal_failure_restricts_all_edges_incident_to_the_station():
	session = FakeSession(
		signal_targets=[{"stationId": "KAT", "name": "Katowice"}],
		incident_edges=[
			{"segmentId": "SEG1", "fromId": "KAT", "toId": "SOS", "vmax": 160},
			{"segmentId": "SEG2", "fromId": "CHO", "toId": "KAT", "vmax": 120},
		],
	)
	event = create_event(session, "signal_failure", now=1000.0)

	assert event is not None
	assert event.type == "signal_failure"
	assert event.stationId == "KAT"

	restrict_calls = [c for c in session.calls if "SET r.status = 'restricted'" in c[0]]
	assert len(restrict_calls) == 1
	assert len(restrict_calls[0][1]["edges"]) == 2
