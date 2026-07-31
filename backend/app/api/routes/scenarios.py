import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from neo4j import Driver

from app.api.dependencies import get_driver
from app.schemas.scenario import (
	ActiveScenarioInfo,
	Scenario,
	ScenarioCreateRequest,
	ScenariosResponse,
)
from app.services import scenario_service
from app.services.scenario_service import ScenarioValidationError

router = APIRouter(tags=["scenarios"])


@router.get("/api/scenarios", response_model=ScenariosResponse)
def get_scenarios(driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		return ScenariosResponse(scenarios=scenario_service.list_scenarios(session))


@router.post("/api/scenarios", response_model=Scenario, status_code=201)
def create_scenario(payload: ScenarioCreateRequest, driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		try:
			return scenario_service.create_scenario(
				session, payload.name, payload.description, payload.trains, time.time()
			)
		except ScenarioValidationError as exc:
			raise HTTPException(status_code=422, detail=str(exc))


@router.put("/api/scenarios/{scenario_id}", response_model=Scenario)
def update_scenario(
	scenario_id: str, payload: ScenarioCreateRequest, driver: Driver = Depends(get_driver)
):
	with driver.session() as session:
		try:
			updated = scenario_service.update_scenario(
				session, scenario_id, payload.name, payload.description, payload.trains
			)
		except ScenarioValidationError as exc:
			raise HTTPException(status_code=422, detail=str(exc))
	if updated is None:
		raise HTTPException(status_code=404, detail="Nie znaleziono scenariusza")
	return updated


@router.delete("/api/scenarios/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: str, driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		if not scenario_service.delete_scenario(session, scenario_id):
			raise HTTPException(status_code=404, detail="Nie znaleziono scenariusza")


def _run_scenario_sync(driver: Driver, app_state, scenario_id: str) -> ActiveScenarioInfo | None:
	with driver.session() as session:
		scenario = scenario_service.get_scenario(session, scenario_id)
		if scenario is None:
			return None
		return scenario_service.run_scenario(session, app_state, scenario, time.time())


@router.post("/api/scenarios/{scenario_id}/run", response_model=ActiveScenarioInfo)
async def run_scenario(
	scenario_id: str, request: Request, driver: Driver = Depends(get_driver)
):
	# Pod sim_lock, żeby podmiana floty nie przecinała się z tickiem symulacji.
	app_state = request.app.state
	async with app_state.sim_lock:
		info = await asyncio.to_thread(_run_scenario_sync, driver, app_state, scenario_id)
	if info is None:
		raise HTTPException(status_code=404, detail="Nie znaleziono scenariusza")
	return info


@router.get("/api/scenarios/active", response_model=ActiveScenarioInfo | None)
def get_active_scenario(request: Request):
	return scenario_service.active_info(request.app.state)
