import asyncio
import logging
import time

from fastapi import FastAPI

from app.core import config
from app.services.train_service import run_tick_sync

logger = logging.getLogger("sim")


def _build_broadcast_payload(tick_result: dict) -> dict:
	scenario = tick_result.get("scenario")
	return {
		"type": "tick",
		"trains": [train.model_dump() for train in tick_result["trains"]],
		"events": [event.model_dump() for event in tick_result["events"]],
		"scenario": scenario.model_dump() if scenario is not None else None,
		"paused": tick_result.get("paused", False),
		"timestamp": tick_result["timestamp"],
	}


async def run_simulation_loop(app: FastAPI) -> None:
	while True:
		tick_start = time.monotonic()
		try:
			async with app.state.sim_lock:
				result = await asyncio.to_thread(run_tick_sync, app.state.driver, app.state)
			await app.state.ws_manager.broadcast(_build_broadcast_payload(result))
		except asyncio.CancelledError:
			raise
		except Exception:
			# Nie wywala reszty aplikacji — jeden nieudany tick nie może ubić
			# "autonomicznej" pętli. Loguje i próbuje ponownie za SIM_TICK_INTERVAL_S.
			logger.exception("Krok symulacji nie powiódł się — pętla kontynuuje działanie")
		elapsed = time.monotonic() - tick_start
		await asyncio.sleep(max(0.0, config.SIM_TICK_INTERVAL_S - elapsed))


def start_simulation(app: FastAPI) -> None:
	app.state.sim_task = asyncio.create_task(run_simulation_loop(app))


async def stop_simulation(app: FastAPI) -> None:
	task = getattr(app.state, "sim_task", None)
	if task is None:
		return
	task.cancel()
	try:
		await task
	except asyncio.CancelledError:
		pass
