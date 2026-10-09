from typing import Callable

from fastapi import Cookie, Depends, Header, HTTPException, Request
from neo4j import Driver

from app.services import auth_service


def get_driver(request: Request) -> Driver:
	driver = getattr(request.app.state, "driver", None)
	if driver is None:
		raise HTTPException(status_code=503, detail="Memgraph driver not ready")
	return driver


def get_current_user(
	request: Request,
	authorization: str | None = Header(default=None),
	srs_session: str | None = Cookie(default=None),
) -> dict:
	"""Rozwiązuje token Bearer (lub ciasteczko srs_session) do świeżego stanu użytkownika
	(z bieżącą rolą i uprawnieniami czytanymi z bazy), unieważniając tokeny wydane przed
	ostatnią zmianą hasła."""
	raw_token = None
	if authorization and authorization.lower().startswith("bearer "):
		raw_token = authorization.split(" ", 1)[1]
	elif srs_session:
		raw_token = srs_session

	if not raw_token:
		raise HTTPException(status_code=401, detail="Brak autoryzacji.")

	payload = auth_service.verify_token(raw_token)
	if not payload:
		raise HTTPException(status_code=401, detail="Sesja wygasła.")

	driver = get_driver(request)
	with driver.session() as session:
		user = auth_service.get_user_by_id(session, payload["sub"])
		if not user or not bool(user.get("active", True)):
			raise HTTPException(status_code=401, detail="Konto nie istnieje lub jest nieaktywne.")

		# Weryfikacja unieważnienia sesji po zmianie hasła
		token_iat = payload.get("iat")
		pwd_updated = user.get("password_updated_at")
		if token_iat is not None and pwd_updated is not None:
			if int(token_iat) < int(pwd_updated) - 1:
				raise HTTPException(
					status_code=401, detail="Hasło zostało zmienione. Zaloguj się ponownie."
				)

		user["permissions"] = auth_service.permissions_for_role(
			session, user.get("role") or auth_service.DEFAULT_ROLE_NAME
		)
	return user


from functools import lru_cache

@lru_cache
def require_permission(permission: str) -> Callable[..., dict]:
	def dependency(user: dict = Depends(get_current_user)) -> dict:
		if permission not in user.get("permissions", []):
			raise HTTPException(status_code=403, detail="Brak uprawnień do tej operacji.")
		return user

	return dependency
