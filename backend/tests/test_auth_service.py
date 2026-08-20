import pytest

from app.services import auth_service


# --- Token z rolą ----------------------------------------------------------


def test_token_round_trip_carries_role():
	token = auth_service.issue_token({"id": "USR_1", "email": "a@b.pl", "role": "admin"})
	payload = auth_service.verify_token(token)
	assert payload is not None
	assert payload["sub"] == "USR_1"
	assert payload["email"] == "a@b.pl"
	assert payload["role"] == "admin"


def test_token_rejects_tampering():
	token = auth_service.issue_token({"id": "USR_1", "email": "a@b.pl", "role": "user"})
	assert auth_service.verify_token(token + "x") is None


def test_password_hash_and_verify():
	encoded = auth_service._hash_password("tajne-haslo-123")
	assert auth_service._verify_password("tajne-haslo-123", encoded)
	assert not auth_service._verify_password("inne-haslo", encoded)


# --- Katalog uprawnień i domyślne role -------------------------------------


def test_default_roles_cover_the_permission_catalog():
	# Admin ma wszystkie uprawnienia; gość tylko podgląd; user coś pomiędzy.
	assert set(auth_service.DEFAULT_ROLES["admin"]["permissions"]) == set(auth_service.PERMISSIONS)
	assert auth_service.DEFAULT_ROLES["guest"]["permissions"] == ["simulation.view"]
	user_perms = auth_service.DEFAULT_ROLES["user"]["permissions"]
	assert "simulation.control" in user_perms
	assert "timetable.manage" in user_perms
	assert "users.manage" not in user_perms


def test_admin_locked_permissions_are_admin_only_and_present():
	for locked in auth_service.ADMIN_LOCKED_PERMISSIONS:
		assert locked in auth_service.DEFAULT_ROLES["admin"]["permissions"]
		assert locked not in auth_service.DEFAULT_ROLES["guest"]["permissions"]
		assert locked not in auth_service.DEFAULT_ROLES["user"]["permissions"]


def test_clean_permissions_filters_unknown_and_dedupes():
	cleaned = auth_service._clean_permissions(
		["simulation.view", "nie.istnieje", "simulation.view", "users.manage"]
	)
	assert cleaned == ["simulation.view", "users.manage"]


# --- Role: minimalna atrapa sesji (bez Memgraph) ---------------------------


class _FakeResult:
	def __init__(self, row):
		self._row = row

	def single(self):
		return self._row


class _FakeSession:
	"""Obsługuje tylko zapytania, których używa update_role/get_role."""

	def __init__(self, roles: dict):
		self.roles = roles

	def run(self, query: str, **params):
		if "SET r += $props" in query:
			self.roles[params["name"]].update(params["props"])
			return _FakeResult({"r": self.roles[params["name"]]})
		if "SET r.permissions" in query:
			self.roles[params["name"]]["permissions"] = params["permissions"]
			return _FakeResult({"r": self.roles[params["name"]]})
		if "MATCH (r:Role {name: $name}) RETURN r" in query:
			node = self.roles.get(params.get("name"))
			return _FakeResult({"r": node} if node is not None else None)
		return _FakeResult(None)


def test_update_role_rejects_edits_to_system_roles():
	roles = {
		"admin": {
			"name": "admin",
			"label": "Administrator",
			"permissions": ["users.manage", "roles.manage", "simulation.view"],
			"is_system": True,
		}
	}
	session = _FakeSession(roles)

	with pytest.raises(ValueError):
		auth_service.update_role(session, "admin", permissions=["simulation.view"])


def test_update_role_drops_unknown_permissions_for_custom_role():
	roles = {
		"dyspozytor": {
			"name": "dyspozytor",
			"label": "Dyspozytor",
			"permissions": ["simulation.view"],
			"is_system": False,
		}
	}
	session = _FakeSession(roles)

	result = auth_service.update_role(
		session, "dyspozytor", permissions=["simulation.control", "coś.wymyślonego"]
	)

	assert result["permissions"] == ["simulation.control"]


def test_permissions_for_role_falls_back_to_defaults_when_missing_in_db():
	session = _FakeSession({})  # baza nie zna tej roli
	assert auth_service.permissions_for_role(session, "guest") == ["simulation.view"]
	assert auth_service.permissions_for_role(session, "nie-ma-takiej") == []
