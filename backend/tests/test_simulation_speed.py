import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.simulation import router as simulation_router


def _build_test_app():
	# Bez lifespan() z main.py (łączy się z Memgraph z nieskończonym retry) —
	# endpoint prędkości nie dotyka bazy, wystarczy goły router i sim_lock.
	app = FastAPI()
	app.state.sim_lock = asyncio.Lock()
	app.state.sim_speed = 1.0
	app.include_router(simulation_router)
	return app


def test_set_speed_accepts_allowed_multiplier():
	app = _build_test_app()
	client = TestClient(app)

	response = client.post("/api/simulation/speed", json={"speed": 1.5})

	assert response.status_code == 204
	assert app.state.sim_speed == 1.5


def test_set_speed_rejects_unknown_multiplier():
	app = _build_test_app()
	client = TestClient(app)

	response = client.post("/api/simulation/speed", json={"speed": 3.0})

	assert response.status_code == 422
	assert app.state.sim_speed == 1.0
