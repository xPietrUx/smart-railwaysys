import math
from unittest.mock import MagicMock

import app.services.train_service as train_service
from app.schemas.network import StationNode
from app.schemas.routing import FastestRouteResult


def _station(id_):
	return StationNode(
		id=id_, code=id_, name=id_, type="przelotowa", lat=0.0, lon=0.0,
		platforms=2, tracks=4, dailyTrains=50,
	)


def _base_train(**overrides):
	train = {
		"id": "T1", "name": "Test", "type": "IC",
		"origin_station_id": "A", "destination_station_id": "B", "direction": "outbound",
		"current_station_id": "A", "next_station_id": "B", "current_segment_id": "SEG1",
		"progress": 0.0, "status": "running",
		"route_station_ids": ["A", "B"], "route_segment_ids": ["SEG1"], "route_index": 0,
		"vmax": 160, "priority": 3, "mass_tonnes": 400.0, "length_m": 200,
		"accel": 0.6, "decel": 0.9,
		"dwell_until": None, "delayed_by_event_id": None, "updated_at": 0.0,
	}
	train.update(overrides)
	return train


def test_advance_train_arrival_uses_real_segment_distance_not_hardcoded_20km():
	# Regresja na błąd z gałęzi A*: dist_km=20.0 było zahardkodowane i ignorowało
	# prawdziwy dystans odcinka. Tu odcinek ma 100km -- przy 100 km/h przez 3600s
	# symulowanych to dokładnie cały odcinek (dotarcie), a nie 5x za szybko.
	train = _base_train(progress=0.0)
	edge_lookup = {("A", "B"): {"distKm": 100.0, "effectiveVmax": 100.0}}

	updated = train_service.advance_train(train, dt_sim_s=3600.0, now=1000.0, edge_lookup=edge_lookup)

	assert updated["status"] == "dwelling"


def test_advance_train_partial_progress_matches_real_distance():
	train = _base_train(progress=0.0)
	edge_lookup = {("A", "B"): {"distKm": 100.0, "effectiveVmax": 100.0}}

	updated = train_service.advance_train(train, dt_sim_s=1800.0, now=1000.0, edge_lookup=edge_lookup)

	# 100km/h * 0.5h = 50km z odcinka 100km => progress = 0.5
	assert updated["status"] == "running"
	assert math.isclose(updated["progress"], 0.5, rel_tol=1e-6)


def test_dispatch_or_wait_sets_waiting_when_no_route_found(monkeypatch):
	no_route = FastestRouteResult(
		found=False, fromStation="A", toStation="B", trainType="IC",
		path=[], segmentIds=[], totalTravelMin=0.0, totalDistKm=0.0, exploredNodesCount=0,
	)
	monkeypatch.setattr(train_service, "find_fastest_route_astar", MagicMock(return_value=no_route))

	train = _base_train(
		status="waiting", current_station_id="A", next_station_id=None,
		current_segment_id=None, route_station_ids=[], route_segment_ids=[],
	)
	updated = train_service.dispatch_or_wait(train, session=MagicMock(), now=1000.0)

	assert updated["status"] == "waiting"
	assert updated["current_segment_id"] is None
	assert updated["next_station_id"] is None


def test_dispatch_or_wait_dispatches_when_route_found(monkeypatch):
	route = FastestRouteResult(
		found=True, fromStation="A", toStation="B", trainType="IC",
		path=[_station("A"), _station("B")], segmentIds=["SEG1"],
		totalTravelMin=10.0, totalDistKm=20.0, exploredNodesCount=2,
	)
	monkeypatch.setattr(train_service, "find_fastest_route_astar", MagicMock(return_value=route))

	train = _base_train(
		status="waiting", current_station_id="A", next_station_id=None,
		current_segment_id=None, route_station_ids=[], route_segment_ids=[],
	)
	updated = train_service.dispatch_or_wait(train, session=MagicMock(), now=1000.0)

	assert updated["status"] == "running"
	assert updated["current_segment_id"] == "SEG1"
	assert updated["next_station_id"] == "B"
	assert updated["progress"] == 0.0


def test_full_cycle_dwell_then_reverse_direction_and_depart(monkeypatch):
	"""Po dotarciu na miejsce pociąg dostaje przerwę (status='dwelling'), a po jej
	zakończeniu odwraca kierunek i rusza w drogę powrotną -- 'powtarza cykl'."""
	route_back = FastestRouteResult(
		found=True, fromStation="B", toStation="A", trainType="IC",
		path=[_station("B"), _station("A")], segmentIds=["SEG1"],
		totalTravelMin=10.0, totalDistKm=20.0, exploredNodesCount=2,
	)
	monkeypatch.setattr(train_service, "find_fastest_route_astar", MagicMock(return_value=route_back))

	# Pociąg właśnie dojechał do B (destination) i jego przerwa się właśnie skończyła.
	train = _base_train(
		status="dwelling", direction="outbound", current_station_id="B",
		next_station_id=None, current_segment_id=None, progress=0.0,
		route_station_ids=[], route_segment_ids=[], dwell_until=500.0,
	)

	updated = train_service._advance_or_dispatch_one(
		train, session=MagicMock(), now=1000.0, dt_sim_s=60.0, edge_lookup={}
	)

	assert updated["direction"] == "return"
	assert updated["status"] == "running"
	assert updated["dwell_until"] is None
	assert updated["current_segment_id"] == "SEG1"


def test_dwelling_train_before_dwell_expires_stays_put():
	train = _base_train(status="dwelling", dwell_until=2000.0)
	updated = train_service._advance_or_dispatch_one(
		train, session=MagicMock(), now=1000.0, dt_sim_s=60.0, edge_lookup={}
	)
	assert updated["status"] == "dwelling"
	assert updated["direction"] == "outbound"


def test_derailed_train_is_frozen_and_ignored_by_tick():
	train = _base_train(status="derailed", progress=0.4)
	updated = train_service._advance_or_dispatch_one(
		train, session=MagicMock(), now=1000.0, dt_sim_s=60.0, edge_lookup={}
	)
	assert updated["status"] == "derailed"
	assert updated["progress"] == 0.4
