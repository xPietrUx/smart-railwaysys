import time
from unittest.mock import MagicMock

import app.services.train_service as train_service
from app.schemas.network import StationNode
from app.schemas.routing import FastestRouteResult
from app.services.train_service import reroute_affected_trains, run_tick_sync


def _station(id_):
	return StationNode(
		id=id_, code=id_, name=id_, type="przelotowa", lat=0.0, lon=0.0,
		platforms=2, tracks=4, dailyTrains=50,
	)


def _base_train(**overrides):
	train = {
		"id": "T1", "name": "Test", "type": "IC",
		"origin_station_id": "A", "destination_station_id": "D", "direction": "outbound",
		"current_station_id": "A", "next_station_id": "B", "current_segment_id": "SEG1",
		"progress": 0.0, "status": "running",
		"route_station_ids": ["A", "B"], "route_segment_ids": ["SEG1"], "route_index": 0,
		"vmax": 160, "priority": 3, "mass_tonnes": 400.0, "length_m": 200,
		"accel": 0.6, "decel": 0.9,
		"dwell_until": None, "delayed_by_event_id": None, "updated_at": 0.0,
	}
	train.update(overrides)
	return train


def test_reroute_scan_halts_train_whose_current_segment_just_blocked():
	train = _base_train(current_segment_id="SEG1", route_segment_ids=["SEG1", "SEG2"], route_index=0)

	updated = reroute_affected_trains([train], session=MagicMock(), segment_id="SEG1")

	assert updated[0]["status"] == "waiting"
	assert updated[0]["current_segment_id"] is None
	assert updated[0]["next_station_id"] is None


def test_reroute_scan_replans_future_segment_without_interrupting_current_hop(monkeypatch):
	route = FastestRouteResult(
		found=True, fromStation="B", toStation="D", trainType="IC",
		path=[_station("B"), _station("C"), _station("D")], segmentIds=["SEG9", "SEG10"],
		totalTravelMin=20.0, totalDistKm=40.0, exploredNodesCount=3,
	)
	monkeypatch.setattr(train_service, "find_fastest_route_astar", MagicMock(return_value=route))

	train = _base_train(
		current_station_id="A", next_station_id="B", current_segment_id="SEG1",
		route_segment_ids=["SEG1", "SEG2"], route_index=0, progress=0.4,
	)

	updated = reroute_affected_trains([train], session=MagicMock(), segment_id="SEG2")

	# bieżący (wciąż aktywny) odcinek zostaje dokończony bez przerywania
	assert updated[0]["status"] == "running"
	assert updated[0]["current_segment_id"] == "SEG1"
	assert updated[0]["progress"] == 0.4
	# ale dalsza część trasy jest przeliczona i doklejona za bieżącym odcinkiem
	assert updated[0]["route_segment_ids"] == ["SEG1", "SEG9", "SEG10"]


def test_reroute_scan_ignores_trains_not_using_the_blocked_segment():
	train = _base_train(current_segment_id="SEG1", route_segment_ids=["SEG1", "SEG2"], route_index=0)

	updated = reroute_affected_trains([train], session=MagicMock(), segment_id="SEG99")

	assert updated[0]["status"] == "running"
	assert updated[0]["current_segment_id"] == "SEG1"


class _FakeAppState:
	def __init__(self):
		# Wystarczająco daleko w przyszłości, żeby run_tick_sync nie próbował w tym
		# teście losować nowego zdarzenia (testujemy tu tylko fizykę ruchu pociągu).
		self.next_event_at = time.time() + 10_000.0


class _FakeSimSession:
	def __init__(self, train_row):
		self.train_row = train_row
		self.written_rows = None

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def run(self, query, **params):
		if "MATCH (e:RailEvent {status: 'active'})" in query:
			return []
		if "RETURN u.id AS fromId" in query:
			return [
				{"fromId": "A", "toId": "B", "distKm": 100.0, "vmax": 100,
				 "status": "active", "restrictedVmax": None},
			]
		if query.strip().startswith("MATCH (t:Train) RETURN t"):
			return [{"t": dict(self.train_row)}]
		if "UNWIND $rows AS row" in query:
			self.written_rows = params["rows"]
			return []
		if query.strip().startswith("MATCH (e:RailEvent) RETURN e"):
			return []
		raise AssertionError(f"Nieobsłużone zapytanie w teście: {query}")


class _FakeDriver:
	def __init__(self, session):
		self._session = session

	def session(self):
		return self._session


def test_run_tick_sync_advances_train_using_real_segment_distance():
	train_row = _base_train(next_station_id="B", current_segment_id="SEG1", progress=0.0)
	session = _FakeSimSession(train_row)
	driver = _FakeDriver(session)

	result = run_tick_sync(driver, _FakeAppState())

	assert len(result["trains"]) == 1
	train_out = result["trains"][0]
	# 100 km/h efektywnie na odcinku 100km, tick = 1.0s * SIM_TIME_SCALE(60) = 60s
	# symulowanych => 100/3600*60 ~= 1.667km => progress ~= 0.01667 (a NIE np. 3.0,
	# co dałby stary zahardkodowany dist_km=20.0)
	assert train_out.status == "running"
	assert 0.0 < train_out.progress < 0.02

	assert session.written_rows is not None
	assert session.written_rows[0]["progress"] == train_out.progress


def test_run_tick_sync_scales_train_progress_with_sim_speed():
	train_row = _base_train(next_station_id="B", current_segment_id="SEG1", progress=0.0)
	session = _FakeSimSession(train_row)
	driver = _FakeDriver(session)
	app_state = _FakeAppState()
	app_state.sim_speed = 2.0

	result = run_tick_sync(driver, app_state)

	# Mnożnik 2x podwaja bazowy przyrost (~0.01667 => ~0.0333).
	assert 0.03 < result["trains"][0].progress < 0.04
	assert result["speed"] == 2.0


def test_run_tick_sync_accumulates_real_elapsed_time_between_ticks():
	train_row = _base_train(next_station_id="B", current_segment_id="SEG1", progress=0.0)
	session = _FakeSimSession(train_row)
	driver = _FakeDriver(session)
	app_state = _FakeAppState()

	first = run_tick_sync(driver, app_state)
	assert first["elapsedRealS"] == 0.0  # pierwszy tick — brak punktu odniesienia

	app_state.sim_last_tick_at = time.time() - 5.0
	second = run_tick_sync(driver, app_state)
	assert 4.5 < second["elapsedRealS"] < 6.0


def test_run_tick_sync_freezes_elapsed_time_while_paused():
	train_row = _base_train()
	session = _FakeSimSession(train_row)
	driver = _FakeDriver(session)
	app_state = _FakeAppState()
	app_state.sim_paused = True
	app_state.sim_elapsed_real_s = 42.0
	app_state.sim_last_tick_at = time.time() - 100.0

	result = run_tick_sync(driver, app_state)

	assert result["paused"] is True
	assert result["elapsedRealS"] == 42.0
