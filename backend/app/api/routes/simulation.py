import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from neo4j import Driver

from app.api.dependencies import get_driver
from app.core import config
from app.schemas.simulation import SimulationSpeedRequest
from app.services import scenario_service

router = APIRouter(tags=["simulation"])


@router.post("/api/simulation/speed", status_code=204)
async def set_simulation_speed(payload: SimulationSpeedRequest, request: Request):
	if payload.speed not in config.SIM_SPEED_OPTIONS:
		allowed = ", ".join(f"{option:g}" for option in config.SIM_SPEED_OPTIONS)
		raise HTTPException(
			status_code=422, detail=f"Dozwolone prędkości symulacji: {allowed}"
		)
	app_state = request.app.state
	async with app_state.sim_lock:
		app_state.sim_speed = payload.speed


@router.post("/api/simulation/pause", status_code=204)
async def pause_simulation(request: Request):
	app_state = request.app.state
	async with app_state.sim_lock:
		if not scenario_service.pause_simulation(app_state, time.time()):
			raise HTTPException(status_code=409, detail="Symulacja jest już wstrzymana")


@router.post("/api/simulation/resume", status_code=204)
async def resume_simulation(request: Request, driver: Driver = Depends(get_driver)):
	app_state = request.app.state

	def _resume_sync() -> bool:
		with driver.session() as session:
			return scenario_service.resume_simulation(session, app_state, time.time())

	async with app_state.sim_lock:
		resumed = await asyncio.to_thread(_resume_sync)
	if not resumed:
		raise HTTPException(status_code=409, detail="Symulacja nie jest wstrzymana")


@router.post("/api/simulation/trains/clear", status_code=204)
async def clear_trains(request: Request, driver: Driver = Depends(get_driver)):
	app_state = request.app.state

	def _clear_sync() -> None:
		with driver.session() as session:
			scenario_service.clear_all_trains(session, app_state)

	async with app_state.sim_lock:
		await asyncio.to_thread(_clear_sync)
