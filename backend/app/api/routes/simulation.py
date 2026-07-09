import time
from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Driver

from app.api.dependencies import get_driver
from app.schemas.simulation import TrainCreateRequest, TrainState, SimulationStateResponse
from app.services.simulation_service import (
	add_train,
	clear_all_trains,
	get_all_trains,
	spawn_demo_trains,
	tick_simulation,
)

router = APIRouter(tags=["simulation"])


@router.get("/api/simulation/trains", response_model=SimulationStateResponse)
def get_trains():
	return SimulationStateResponse(trains=get_all_trains(), timestamp=time.time())


@router.post("/api/simulation/trains", response_model=TrainState)
def create_train(payload: TrainCreateRequest, driver: Driver = Depends(get_driver)):
	try:
		return add_train(driver, payload)
	except ValueError as err:
		raise HTTPException(status_code=400, detail=str(err))


@router.post("/api/simulation/trains/demo", response_model=SimulationStateResponse)
def create_demo_trains(driver: Driver = Depends(get_driver)):
	trains = spawn_demo_trains(driver)
	return SimulationStateResponse(trains=trains, timestamp=time.time())


@router.post("/api/simulation/tick", response_model=SimulationStateResponse)
def tick(
	deltaSec: float = Query(1.0, gt=0.0),
	timeScale: float = Query(60.0, gt=0.0),
	driver: Driver = Depends(get_driver),
):
	return tick_simulation(driver, delta_sec=deltaSec, time_scale=timeScale)


@router.delete("/api/simulation/trains")
def delete_all_trains():
	count = clear_all_trains()
	return {"success": True, "clearedCount": count}
