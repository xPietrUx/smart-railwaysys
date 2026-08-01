"""Scenariusze rozkładu pociągów.

Scenariusz = nazwana lista pociągów (relacja from->to, typ, odjazd po X s od
startu). Uruchomienie zastępuje WSZYSTKIE pociągi na sieci pociągami rozkładu;
wjeżdżają one o swoich czasach (apply_due_spawns w pętli symulacji) i dalej
kursują cyklicznie jak flota bazowa — prowadzi je ten sam silnik (A*, obsługa
blokad i zdarzeń losowych).

Wszystkie scenariusze żyją w Memgraph i są w pełni edytowalne. Przy pustej
bazie scenariuszy tworzony jest komplet 5 startowych (ensure_starter_scenarios).
"""

import json
import uuid

from neo4j import Session

from app.schemas.scenario import ActiveScenarioInfo, Scenario, TrainPlan

ALLOWED_TRAIN_TYPES = ("REGIONAL", "IC", "FREIGHT")

# Parametry fizyczne pociągów per typ — wartości jak w db/seed.py.
_TRAIN_DEFAULTS = {
	"REGIONAL": {"vmax": 120, "priority": 2, "mass": 120.0, "length": 60, "accel": 0.6, "decel": 0.9},
	"IC": {"vmax": 160, "priority": 3, "mass": 420.0, "length": 200, "accel": 0.5, "decel": 0.8},
	"FREIGHT": {"vmax": 80, "priority": 1, "mass": 1800.0, "length": 550, "accel": 0.25, "decel": 0.4},
}


class ScenarioValidationError(ValueError):
	"""Nieprawidłowa definicja scenariusza (np. nieistniejąca stacja)."""


def _plan(name: str, train_type: str, from_id: str, to_id: str, depart_s: float) -> TrainPlan:
	return TrainPlan(
		name=name, type=train_type, fromStationId=from_id, toStationId=to_id, departS=depart_s
	)


def _full_base_timetable() -> list[TrainPlan]:
	"""Pełna flota bazowa z db/seed.py jako rozkład — odjazdy rozłożone falami,
	żeby sieć zapełniała się stopniowo, a nie jednym wystrzałem."""
	from db.seed import TRAINS

	plans = []
	for index, row in enumerate(TRAINS):
		_, name, train_type, origin, destination = row[:5]
		plans.append(_plan(name, train_type, origin, destination, float((index % 24) * 5)))
	return plans


def starter_scenarios() -> list[Scenario]:
	return [
		Scenario(
			id="ROZKLAD_BAZOWY",
			name="Rozkład bazowy Kolei Śląskich",
			description=(
				"Pełna flota z danych GTFS + PKP PLK: 52 pociągi (regionalne, "
				"dalekobieżne i towarowe) wyjeżdżające falami na całą sieć."
			),
			trains=_full_base_timetable(),
		),
		Scenario(
			id="ROZKLAD_SZCZYT_GOP",
			name="Szczyt poranny GOP",
			description=(
				"Gęsty ruch regionalny wokół Katowic: krótkie relacje aglomeracyjne "
				"co kilkadziesiąt sekund, głównie przez węzeł katowicki."
			),
			trains=[
				_plan("S1 Katowice – Gliwice", "REGIONAL", "KAT", "GLI", 0),
				_plan("S1 Gliwice – Katowice", "REGIONAL", "GLI", "KAT", 10),
				_plan("S9 Katowice – Częstochowa", "REGIONAL", "KAT", "CZE", 20),
				_plan("S9 Częstochowa – Katowice", "REGIONAL", "CZE", "KAT", 30),
				_plan("S4 Katowice – Tychy Lodowisko", "REGIONAL", "KAT", "TYL", 40),
				_plan("S4 Tychy Lodowisko – Katowice", "REGIONAL", "TYL", "KAT", 50),
				_plan("S3 Katowice – Jaworzno Szczakowa", "REGIONAL", "KAT", "JA2", 60),
				_plan("S31 Katowice – Oświęcim", "REGIONAL", "KAT", "OSW", 70),
				_plan("S18 Gliwice – Bytom", "REGIONAL", "GLI", "BYT", 80),
				_plan("S8 Katowice – Lubliniec", "REGIONAL", "KAT", "LUB", 90),
				_plan("S1 Katowice – Dąbrowa G. Ząbkowice", "REGIONAL", "KAT", "DAG", 100),
				_plan("S7 Katowice – Rybnik", "REGIONAL", "KAT", "RYB", 110),
			],
		),
		Scenario(
			id="ROZKLAD_EKSPRESY",
			name="Ekspresy dalekobieżne",
			description=(
				"Tylko szybkie składy PKP Intercity — sieć niemal pusta, za to "
				"pociągi pędzą 160 km/h między głównymi węzłami."
			),
			trains=[
				_plan("IC Ślązak", "IC", "BIG", "KAT", 0),
				_plan("IC Ondraszek", "IC", "BIG", "SOG", 15),
				_plan("EC Silesia", "IC", "KAT", "CHY", 30),
				_plan("EC Sobieski", "IC", "KAT", "GLI", 45),
				_plan("TLK Jasna Góra", "IC", "KAT", "CZE", 60),
				_plan("IC Odra", "IC", "KAT", "GLI", 75),
			],
		),
		Scenario(
			id="ROZKLAD_TOWAROWY",
			name="Korytarz towarowy",
			description=(
				"Ciężkie składy towarowe na korytarzach węglowych i tranzytowych — "
				"wolne (80 km/h), długie i trudne do wyprzedzenia."
			),
			trains=[
				_plan("Towarowy węglowy północ", "FREIGHT", "RYT", "GLI", 0),
				_plan("Towarowy tranzytowy CZ", "FREIGHT", "CHA", "RYT", 20),
				_plan("Towarowy hutniczy", "FREIGHT", "DAG", "SOG", 40),
				_plan("Towarowy magistralny", "FREIGHT", "TAG", "LUB", 60),
				_plan("Towarowy graniczny", "FREIGHT", "OSW", "MYS", 80),
				_plan("Towarowy raciborski", "FREIGHT", "GLI", "RAC", 100),
			],
		),
		Scenario(
			id="ROZKLAD_BESKIDY",
			name="Beskidy i południe",
			description=(
				"Ruch turystyczny na południe: Żywiec, Wisła, Zwardoń i Cieszyn, "
				"z jednym wzmocnionym IC do Bielska."
			),
			trains=[
				_plan("S5 Katowice – Żywiec", "REGIONAL", "KAT", "ZYW", 0),
				_plan("S6 Katowice – Wisła Głębce", "REGIONAL", "KAT", "WIG", 15),
				_plan("S61 Cieszyn – Czechowice-Dziedzice", "REGIONAL", "CIE", "CZ2", 30),
				_plan("KSL Czechowice-Dziedzice – Żywiec", "REGIONAL", "CZ2", "ZYW", 45),
				_plan("S5 Katowice – Zwardoń", "REGIONAL", "KAT", "ZWA", 60),
				_plan("S62 Goleszów – Wisła Głębce", "REGIONAL", "GOL", "WIG", 75),
				_plan("IC Beskidy", "IC", "KAT", "BIG", 90),
			],
		),
	]


def ensure_starter_scenarios(session: Session, now: float) -> int:
	"""Przy pustej bazie scenariuszy zapisuje komplet startowych. Zwraca liczbę
	utworzonych (0, gdy scenariusze już istnieją). Węzły w starym formacie
	(sprzed modelu rozkładów, bez trains_json) są przy okazji usuwane."""
	session.run("MATCH (sc:Scenario) WHERE sc.trains_json IS NULL DETACH DELETE sc")
	count = session.run("MATCH (sc:Scenario) RETURN count(sc) AS c").single()["c"]
	if count > 0:
		return 0
	for offset, scenario in enumerate(starter_scenarios()):
		_persist_scenario(session, scenario, now + offset)
	return len(starter_scenarios())


def _persist_scenario(session: Session, scenario: Scenario, created_at: float) -> None:
	session.run(
		"""
		CREATE (sc:Scenario {
			id: $id, name: $name, description: $description,
			trains_json: $trainsJson, created_at: $createdAt
		})
		""",
		id=scenario.id,
		name=scenario.name,
		description=scenario.description,
		trainsJson=json.dumps([t.model_dump() for t in scenario.trains]),
		createdAt=created_at,
	)


def _scenario_from_node(node) -> Scenario:
	return Scenario(
		id=node["id"],
		name=node["name"],
		description=node.get("description") or "",
		trains=[TrainPlan(**raw) for raw in json.loads(node["trains_json"])],
	)


def list_scenarios(session: Session) -> list[Scenario]:
	records = session.run("MATCH (sc:Scenario) RETURN sc ORDER BY sc.created_at ASC")
	return [_scenario_from_node(r["sc"]) for r in records]


def get_scenario(session: Session, scenario_id: str) -> Scenario | None:
	record = session.run(
		"MATCH (sc:Scenario {id: $id}) RETURN sc", id=scenario_id
	).single()
	return _scenario_from_node(record["sc"]) if record else None


def validate_trains(session: Session, trains: list[TrainPlan]) -> None:
	known_stations = {
		r["id"] for r in session.run("MATCH (s:Station) RETURN s.id AS id")
	}
	for index, train in enumerate(trains, start=1):
		if train.type not in ALLOWED_TRAIN_TYPES:
			raise ScenarioValidationError(f"Pociąg {index}: nieznany typ '{train.type}'")
		if train.fromStationId == train.toStationId:
			raise ScenarioValidationError(
				f"Pociąg {index}: stacja początkowa i docelowa muszą być różne"
			)
		for station_id in (train.fromStationId, train.toStationId):
			if station_id not in known_stations:
				raise ScenarioValidationError(f"Pociąg {index}: nieznana stacja '{station_id}'")


def create_scenario(
	session: Session, name: str, description: str, trains: list[TrainPlan], now: float
) -> Scenario:
	validate_trains(session, trains)
	scenario = Scenario(
		id=f"ROZKLAD_{uuid.uuid4().hex[:10]}",
		name=name.strip(),
		description=description.strip(),
		trains=trains,
	)
	_persist_scenario(session, scenario, now)
	return scenario


def update_scenario(
	session: Session, scenario_id: str, name: str, description: str,
	trains: list[TrainPlan],
) -> Scenario | None:
	record = session.run(
		"MATCH (sc:Scenario {id: $id}) RETURN count(sc) AS c", id=scenario_id
	).single()
	if not record or record["c"] == 0:
		return None
	validate_trains(session, trains)
	scenario = Scenario(
		id=scenario_id, name=name.strip(), description=description.strip(), trains=trains
	)
	session.run(
		"""
		MATCH (sc:Scenario {id: $id})
		SET sc.name = $name, sc.description = $description, sc.trains_json = $trainsJson
		""",
		id=scenario.id,
		name=scenario.name,
		description=scenario.description,
		trainsJson=json.dumps([t.model_dump() for t in scenario.trains]),
	)
	return scenario


def delete_scenario(session: Session, scenario_id: str) -> bool:
	record = session.run(
		"MATCH (sc:Scenario {id: $id}) RETURN count(sc) AS c", id=scenario_id
	).single()
	if not record or record["c"] == 0:
		return False
	session.run("MATCH (sc:Scenario {id: $id}) DETACH DELETE sc", id=scenario_id)
	return True


# --- Uruchamianie rozkładu i sterowanie flotą (stan w app.state) ---


def run_scenario(session: Session, app_state, scenario: Scenario, now: float) -> ActiveScenarioInfo:
	"""Zastępuje flotę: usuwa wszystkie pociągi z sieci, wygasza aktywne zdarzenia
	(czysty start) i planuje wjazdy pociągów rozkładu. Same wjazdy wykonuje pętla
	symulacji (apply_due_spawns) — jedna ścieżka mutacji floty.

	Przy wstrzymanej symulacji odjazdy liczą się od momentu pauzy — wznowienie
	przesuwa je o czas pauzy (shift_timers_after_pause), więc rozkład ruszy
	dokładnie od wznowienia."""
	session.run("MATCH (t:Train) DETACH DELETE t")
	session.run("MATCH (e:RailEvent {status: 'active'}) SET e.resolves_at = $now", now=now)
	base = (
		app_state.pause_started_at
		if getattr(app_state, "sim_paused", False) and getattr(app_state, "pause_started_at", None)
		else now
	)
	pending = [
		{"plan": plan, "due_at": base + plan.departS} for plan in scenario.trains
	]
	pending.sort(key=lambda item: item["due_at"])
	app_state.scenario = {
		"id": scenario.id,
		"name": scenario.name,
		"started_at": base,
		"pending": pending,
		"total": len(scenario.trains),
	}
	return active_info(app_state)


def apply_due_spawns(session: Session, app_state, now: float) -> int:
	"""Wywoływane co tick: wprowadza na sieć pociągi rozkładu, którym minął czas
	odjazdu. Pociąg startuje jako 'waiting' — najbliższy tick silnika sam wyliczy
	mu trasę A* (jak przy seedzie). Zwraca liczbę wprowadzonych pociągów."""
	state = getattr(app_state, "scenario", None)
	if state is None or not state["pending"]:
		return 0

	spawned = 0
	still_pending = []
	for item in state["pending"]:
		if item["due_at"] > now:
			still_pending.append(item)
			continue
		_spawn_train(session, item["plan"], now)
		spawned += 1
	state["pending"] = still_pending
	return spawned


def _spawn_train(session: Session, plan: TrainPlan, now: float) -> str:
	defaults = _TRAIN_DEFAULTS[plan.type]
	train_id = f"ROZ_{uuid.uuid4().hex[:8]}"
	session.run(
		"""
		CREATE (:Train {
			id: $id, name: $name, type: $type,
			origin_station_id: $origin, destination_station_id: $destination,
			direction: 'outbound',
			current_station_id: $origin, next_station_id: null, current_segment_id: null,
			progress: 0.0, status: 'waiting',
			route_station_ids: [], route_segment_ids: [], route_index: 0,
			vmax: $vmax, priority: $priority, mass_tonnes: $mass, length_m: $length,
			accel: $accel, decel: $decel,
			dwell_until: null, delayed_by_event_id: null, updated_at: $now,
			operator: 'rozkład scenariusza', line_code: '',
			data_source: 'scenario', data_confidence: 'modeled'
		})
		""",
		id=train_id,
		name=plan.name,
		type=plan.type,
		origin=plan.fromStationId,
		destination=plan.toStationId,
		now=now,
		**defaults,
	)
	return train_id


def clear_all_trains(session: Session, app_state) -> None:
	"""Usuwa z sieci wszystkie pociągi (flotę bieżącego rozkładu) wraz z jeszcze
	niewprowadzonymi wjazdami."""
	session.run("MATCH (t:Train) DETACH DELETE t")
	app_state.scenario = None


def active_info(app_state) -> ActiveScenarioInfo | None:
	state = getattr(app_state, "scenario", None)
	if state is None:
		return None
	return ActiveScenarioInfo(
		id=state["id"],
		name=state["name"],
		startedAt=state["started_at"],
		totalTrains=state["total"],
		spawnedTrains=state["total"] - len(state["pending"]),
	)


# --- Pauza symulacji ---


def pause_simulation(app_state, now: float) -> bool:
	"""Zamraża symulację (pętla przestaje mutować stan). Zwraca False, gdy już
	wstrzymana."""
	if getattr(app_state, "sim_paused", False):
		return False
	app_state.sim_paused = True
	app_state.pause_started_at = now
	return True


def resume_simulation(session: Session, app_state, now: float) -> bool:
	"""Wznawia symulację, przesuwając wszystkie zegary (przerwy postojowe,
	wygasanie zdarzeń, timer losowań, zaplanowane wjazdy) o czas pauzy — po
	wznowieniu nic nie 'nadrabia' skokowo."""
	if not getattr(app_state, "sim_paused", False):
		return False
	delta = now - (app_state.pause_started_at or now)
	session.run(
		"MATCH (t:Train) WHERE t.dwell_until IS NOT NULL "
		"SET t.dwell_until = t.dwell_until + $delta",
		delta=delta,
	)
	session.run(
		"MATCH (e:RailEvent {status: 'active'}) SET e.resolves_at = e.resolves_at + $delta",
		delta=delta,
	)
	app_state.next_event_at += delta
	state = getattr(app_state, "scenario", None)
	if state is not None:
		state["started_at"] += delta
		for item in state["pending"]:
			item["due_at"] += delta
	app_state.sim_paused = False
	app_state.pause_started_at = None
	return True
