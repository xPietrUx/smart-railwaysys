from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.live import router as live_router
from app.core.ws_manager import ConnectionManager


def _build_test_app(driver):
	# Celowo NIE używamy prawdziwego lifespan() z main.py -- ten łączy się z
	# Memgraph z nieskończonym retry, więc zbudowalibyśmy tu appkę, która wisi bez
	# żywej bazy. Zamiast tego montujemy tylko router /ws/live na gołej FastAPI
	# z podstawionym driverem i managerem połączeń.
	app = FastAPI()
	app.state.driver = driver
	app.state.ws_manager = ConnectionManager()
	app.include_router(live_router)
	return app


def _fake_driver_with_empty_state():
	session = MagicMock()
	session.__enter__.return_value = session
	session.__exit__.return_value = False
	session.run.return_value = []

	driver = MagicMock()
	driver.session.return_value = session
	return driver


def test_ws_live_sends_initial_snapshot_on_connect():
	app = _build_test_app(_fake_driver_with_empty_state())
	client = TestClient(app)

	with client.websocket_connect("/ws/live") as websocket:
		message = websocket.receive_json()

	assert message["type"] == "snapshot"
	assert message["trains"] == []
	assert message["events"] == []


def test_ws_live_rejects_disallowed_origin():
	app = _build_test_app(_fake_driver_with_empty_state())
	client = TestClient(app)

	rejected = False
	try:
		with client.websocket_connect("/ws/live", headers={"origin": "http://evil.example"}) as websocket:
			websocket.receive_json()
	except Exception:
		rejected = True

	assert rejected, "połączenie z niedozwolonego Origin powinno zostać odrzucone"
