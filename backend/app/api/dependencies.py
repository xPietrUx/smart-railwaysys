from typing import Callable

from fastapi import Depends, Header, HTTPException, Request
from neo4j import Driver

from app.services import auth_service


def get_driver(request: Request) -> Driver:
	driver = getattr(request.app.state, "driver", None)
	if driver is None:
		raise HTTPException(status_code=503, detail="Memgraph driver not ready")
	return driver


def get_current_user(
	authorization: str | None = Header(default=None),
	driver: Driver = Depends(get_driver),
) -> dict:
	"""Rozwiązuje token Bearer do świeżego stanu użytkownika (z bieżącą rolą i
	uprawnieniami czytanymi z bazy), więc zmiany ról działają natychmiast."""
	if not authorization or not authorization.lower().startswith("bearer "):
		raise HTTPException(status_code=401, detail="Brak autoryzacji.")
	payload = auth_service.verify_token(authorization.split(" ", 1)[1])
	if not payload:
		raise HTTPException(status_code=401, detail="Sesja wygasła.")
	with driver.session() as session:
		user = auth_service.get_user_by_id(session, payload["sub"])
		if not user or not bool(user.get("active", True)):
			raise HTTPException(status_code=401, detail="Konto nie istnieje lub jest nieaktywne.")
		user["permissions"] = auth_service.permissions_for_role(
			session, user.get("role") or auth_service.DEFAULT_ROLE_NAME
		)
	return user


def require_permission(permission: str) -> Callable[..., dict]:
	def dependency(user: dict = Depends(get_current_user)) -> dict:
		if permission not in user.get("permissions", []):
			raise HTTPException(status_code=403, detail="Brak uprawnień do tej operacji.")
		return user

	return dependency
