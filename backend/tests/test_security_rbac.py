import time
from fastapi.testclient import TestClient

from app.api.dependencies import get_driver
from app.main import app
from app.services import auth_service
from app.schemas.event import IncidentCreateRequest
from pydantic import ValidationError
import pytest


class _FakeResult:
	def __init__(self, rows=None):
		self._rows = rows or []

	def single(self):
		return self._rows[0] if self._rows else None

	def __iter__(self):
		return iter(self._rows)


class _FakeSession:
	def __init__(self, user_record=None):
		self.user_record = user_record
		self.runs = []

	def __enter__(self):
		return self

	def __exit__(self, *args):
		pass

	def run(self, query, **params):
		self.runs.append((query, params))
		if "MATCH (u:User {id: $id})" in query:
			if self.user_record:
				return _FakeResult([{"u": self.user_record}])
			return _FakeResult([])
		if "MATCH (r:Role {name: $name})" in query:
			return _FakeResult([{"r": {"name": params.get("name"), "permissions": ["simulation.view"]}}])
		return _FakeResult([])


class _FakeDriver:
	def __init__(self, user_record=None):
		self.user_record = user_record

	def session(self):
		return _FakeSession(self.user_record)


def test_simulation_endpoints_require_auth():
	client = TestClient(app)

	# Bez autoryzacji wszystkie akcje sterujące muszą zwrócić 401
	resp_speed = client.post("/api/simulation/speed", json={"speed": 1.5})
	assert resp_speed.status_code == 401

	resp_pause = client.post("/api/simulation/pause")
	assert resp_pause.status_code == 401

	resp_resume = client.post("/api/simulation/resume")
	assert resp_resume.status_code == 401

	resp_clear = client.post("/api/simulation/trains/clear")
	assert resp_clear.status_code == 401


def test_scenario_endpoints_require_auth():
	client = TestClient(app)

	resp_create = client.post("/api/scenarios", json={"name": "test", "trains": []})
	assert resp_create.status_code == 401

	resp_update = client.put("/api/scenarios/123", json={"name": "test", "trains": []})
	assert resp_update.status_code == 401

	resp_delete = client.delete("/api/scenarios/123")
	assert resp_delete.status_code == 401

	resp_run = client.post("/api/scenarios/123/run")
	assert resp_run.status_code == 401


def test_trigger_event_requires_auth():
	client = TestClient(app)
	resp = client.post("/api/simulation/events/trigger")
	assert resp.status_code == 401


def test_incident_duration_validation():
	# durationS <= 0 nie może przejść walidacji
	with pytest.raises(ValidationError):
		IncidentCreateRequest(type="line_failure", targetId="SEG_1", durationS=-10.0)

	with pytest.raises(ValidationError):
		IncidentCreateRequest(type="line_failure", targetId="SEG_1", durationS=0.0)

	# durationS > 86400 (doba) nie może przejść walidacji
	with pytest.raises(ValidationError):
		IncidentCreateRequest(type="line_failure", targetId="SEG_1", durationS=999999.0)

	# Prawidłowa wartość przechodzi
	req = IncidentCreateRequest(type="line_failure", targetId="SEG_1", durationS=60.0)
	assert req.durationS == 60.0


def test_security_headers_present():
	client = TestClient(app)
	resp = client.get("/api/hello")
	assert resp.status_code == 200
	assert resp.headers.get("X-Content-Type-Options") == "nosniff"
	assert resp.headers.get("X-Frame-Options") == "DENY"
	assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_token_revocation_after_password_reset():
	user_id = "USR_test_pwd"
	t0 = time.time()
	user = {
		"id": user_id,
		"email": "test@smartrailway.pl",
		"role": "admin",
		"active": True,
		"created_at": t0,
		"password_updated_at": t0,
	}

	# Wystawiamy token w chwili t0
	token = auth_service.issue_token(user)

	# Symulujemy, że hasło zostało zmienione w chwili t0 + 10 sekund
	user_after_pwd_change = dict(user)
	user_after_pwd_change["password_updated_at"] = t0 + 10.0

	fake_driver = _FakeDriver(user_after_pwd_change)
	app.state.driver = fake_driver
	app.dependency_overrides[get_driver] = lambda: fake_driver

	client = TestClient(app)
	# Próba autoryzacji starym tokenem po zmianie hasła
	resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
	assert resp.status_code == 401
	assert "Hasło zostało zmienione" in resp.json()["detail"]

	app.state.driver = None
	app.dependency_overrides.pop(get_driver, None)


def test_cookie_authentication_supported():
	user_id = "USR_cookie_test"
	now = time.time()
	user = {
		"id": user_id,
		"email": "cookie@smartrailway.pl",
		"role": "admin",
		"active": True,
		"created_at": now,
		"password_updated_at": now,
	}
	token = auth_service.issue_token(user)

	fake_driver = _FakeDriver(user)
	app.state.driver = fake_driver
	app.dependency_overrides[get_driver] = lambda: fake_driver

	client = TestClient(app)
	# Wysyłamy token w ciasteczku srs_session bez nagłówka Authorization
	client.cookies.set("srs_session", token)
	resp = client.get("/api/auth/me")
	assert resp.status_code == 200
	assert resp.json()["email"] == "cookie@smartrailway.pl"

	app.state.driver = None
	app.dependency_overrides.pop(get_driver, None)
