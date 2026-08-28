from fastapi import APIRouter, Depends, HTTPException
from neo4j import Driver, Session

from app.api.dependencies import get_current_user, get_driver
from app.schemas.auth import AuthCredentials, GuestContext, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(session: Session, user: dict) -> TokenResponse:
	role = user.get("role") or auth_service.DEFAULT_ROLE_NAME
	permissions = auth_service.permissions_for_role(session, role)
	public_user = UserResponse(id=user["id"], email=user["email"], role=role, permissions=permissions)
	return TokenResponse(access_token=auth_service.issue_token(user), user=public_user)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: AuthCredentials, driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		try:
			user = auth_service.create_user(session, payload.email, payload.password)
		except ValueError as exc:
			raise HTTPException(status_code=422, detail=str(exc)) from exc
		if not user:
			raise HTTPException(status_code=409, detail="Konto z tym adresem e-mail już istnieje.")
		return _token_response(session, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: AuthCredentials, driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		user = auth_service.authenticate(session, payload.email, payload.password)
		if not user:
			raise HTTPException(status_code=401, detail="Nieprawidłowy e-mail lub hasło.")
		return _token_response(session, user)


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)):
	return UserResponse(
		id=user["id"],
		email=user["email"],
		role=user.get("role") or auth_service.DEFAULT_ROLE_NAME,
		permissions=user.get("permissions", []),
	)


@router.get("/guest", response_model=GuestContext)
def guest(driver: Driver = Depends(get_driver)):
	"""Uprawnienia sesji gościa — pobierane z bazy, więc edycja roli „gość” w
	panelu administratora od razu wpływa na to, co gość może zrobić."""
	with driver.session() as session:
		permissions = auth_service.permissions_for_role(session, auth_service.GUEST_ROLE_NAME)
	return GuestContext(role=auth_service.GUEST_ROLE_NAME, permissions=permissions)
