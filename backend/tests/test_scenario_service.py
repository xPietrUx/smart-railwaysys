import pytest

from app.schemas.scenario import Scenario, TrainPlan
from app.services.scenario_service import (
	ALLOWED_TRAIN_TYPES,
	ScenarioValidationError,
	active_info,
	apply_due_spawns,
	clear_all_trains,
	pause_simulation,
	resume_simulation,
	run_scenario,
	starter_scenarios,
	update_scenario,
	validate_trains,
)


class FakeResult(list):
	def single(self):
		return self[0] if self else None


class FakeSession:
	"""Minimalna sesja pod rozkłady: znane stacje + zapis wywołań (dopasowanie
	zapytań po charakterystycznych fragmentach)."""

	def __init__(self, known_stations=None, exists_scenario=False):
		self.known_stations = known_stations if known_stations is not None else set()
		self.exists_scenario = exists_scenario
		self.calls: list[tuple[str, dict]] = []

	def run(self, query, **params):
		self.calls.append((query, params))

		if "MATCH (s:Station) RETURN s.id AS id" in query:
			return FakeResult([{"id": station_id} for station_id in self.known_stations])

		if "MATCH (sc:Scenario {id: $id}) RETURN count(sc) AS c" in query:
			return FakeResult([{"c": 1 if self.exists_scenario else 0}])

		# CREATE / SET / DELETE — zapisy bez odczytu wyniku
		return FakeResult([])


class FakeAppState:
	def __init__(self):
		self.next_event_at = 0.0
		self.scenario = None
		self.sim_paused = False
		self.pause_started_at = None


def _scenario(trains):
	return Scenario(id="ROZKLAD_TEST", name="Test", trains=trains)


def test_starter_scenarios_are_five_and_well_formed():
	starters = starter_scenarios()
	assert len(starters) == 5
	assert starters[0].id == "ROZKLAD_BAZOWY"
	assert len(starters[0].trains) == 52  # pełna flota z seed.py
	for scenario in starters:
		assert len(scenario.trains) >= 6
		for train in scenario.trains:
			assert train.type in ALLOWED_TRAIN_TYPES
			assert train.fromStationId != train.toStationId


def test_validate_trains_rejects_bad_definitions():
	session = FakeSession(known_stations={"KAT", "GLI"})

	validate_trains(session, [TrainPlan(
		name="OK", type="IC", fromStationId="KAT", toStationId="GLI",
	)])  # poprawny — nie rzuca

	with pytest.raises(ScenarioValidationError):
		validate_trains(session, [TrainPlan(
			name="X", type="REGIONAL", fromStationId="KAT", toStationId="KAT",
		)])
	with pytest.raises(ScenarioValidationError):
		validate_trains(session, [TrainPlan(
			name="X", type="REGIONAL", fromStationId="KAT", toStationId="XXX",
		)])
	with pytest.raises(ScenarioValidationError):
		validate_trains(session, [TrainPlan(
			name="X", type="MAGLEV", fromStationId="KAT", toStationId="GLI",
		)])


def test_run_scenario_replaces_fleet_and_schedules_spawns():
	scenario = _scenario([
		TrainPlan(name="A", type="REGIONAL", fromStationId="KAT", toStationId="GLI", departS=0),
		TrainPlan(name="B", type="IC", fromStationId="GLI", toStationId="KAT", departS=100),
	])
	app_state = FakeAppState()
	session = FakeSession()

	info = run_scenario(session, app_state, scenario, now=1000.0)

	assert info.totalTrains == 2 and info.spawnedTrains == 0
	# stara flota usunięta, aktywne zdarzenia wygaszone
	assert any("MATCH (t:Train) DETACH DELETE t" in c[0] for c in session.calls)
	assert any("SET e.resolves_at = $now" in c[0] for c in session.calls)


def test_apply_due_spawns_creates_only_due_trains():
	scenario = _scenario([
		TrainPlan(name="A", type="REGIONAL", fromStationId="KAT", toStationId="GLI", departS=0),
		TrainPlan(name="B", type="FREIGHT", fromStationId="GLI", toStationId="KAT", departS=100),
	])
	app_state = FakeAppState()
	session = FakeSession()
	run_scenario(session, app_state, scenario, now=1000.0)

	assert apply_due_spawns(session, app_state, now=1000.5) == 1
	spawn_calls = [c for c in session.calls if "CREATE (:Train {" in c[0]]
	assert len(spawn_calls) == 1
	assert spawn_calls[0][1]["name"] == "A"
	assert active_info(app_state).spawnedTrains == 1

	assert apply_due_spawns(session, app_state, now=1101.0) == 1
	spawn_calls = [c for c in session.calls if "CREATE (:Train {" in c[0]]
	assert spawn_calls[1][1]["name"] == "B"
	assert spawn_calls[1][1]["vmax"] == 80  # parametry towarowego
	assert active_info(app_state).spawnedTrains == 2


def test_clear_all_trains_wipes_fleet_and_active_scenario():
	app_state = FakeAppState()
	session = FakeSession()
	run_scenario(session, app_state, _scenario([
		TrainPlan(name="A", type="REGIONAL", fromStationId="KAT", toStationId="GLI", departS=300),
	]), now=1000.0)

	clear_all_trains(session, app_state)

	assert app_state.scenario is None
	assert active_info(app_state) is None


def test_pause_and_resume_shift_all_timers_by_pause_duration():
	app_state = FakeAppState()
	app_state.next_event_at = 1050.0
	session = FakeSession()
	run_scenario(session, app_state, _scenario([
		TrainPlan(name="A", type="REGIONAL", fromStationId="KAT", toStationId="GLI", departS=200),
	]), now=1000.0)

	assert pause_simulation(app_state, now=1010.0) is True
	assert pause_simulation(app_state, now=1011.0) is False  # już wstrzymana

	# pauza trwała 90 s — wszystkie zegary przesunięte o 90
	assert resume_simulation(session, app_state, now=1100.0) is True
	assert app_state.sim_paused is False
	assert app_state.next_event_at == 1050.0 + 90.0
	assert app_state.scenario["pending"][0]["due_at"] == 1000.0 + 200 + 90.0

	shift_calls = [c for c in session.calls if "t.dwell_until + $delta" in c[0]]
	assert len(shift_calls) == 1 and shift_calls[0][1]["delta"] == 90.0

	assert resume_simulation(session, app_state, now=1200.0) is False  # nie wstrzymana


def test_run_while_paused_anchors_departures_at_pause_moment():
	app_state = FakeAppState()
	session = FakeSession()
	pause_simulation(app_state, now=1000.0)

	run_scenario(session, app_state, _scenario([
		TrainPlan(name="A", type="REGIONAL", fromStationId="KAT", toStationId="GLI", departS=50),
	]), now=1030.0)

	# odjazd zakotwiczony w momencie pauzy...
	assert app_state.scenario["pending"][0]["due_at"] == 1000.0 + 50
	# ...więc po wznowieniu wypada dokładnie 50 s po wznowieniu
	resume_simulation(session, app_state, now=1100.0)
	assert app_state.scenario["pending"][0]["due_at"] == 1100.0 + 50


def test_update_missing_scenario_returns_none():
	session = FakeSession(known_stations={"KAT", "GLI"}, exists_scenario=False)
	assert update_scenario(session, "ROZKLAD_zzz", "X", "", [
		TrainPlan(name="A", type="REGIONAL", fromStationId="KAT", toStationId="GLI"),
	]) is None
