from fastapi import APIRouter, Depends, Header, HTTPException
from neo4j import Driver

from app.api.dependencies import get_driver
from app.schemas.auth import AuthCredentials, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _response(user: dict) -> TokenResponse:
	public_user = UserResponse(id=user["id"], email=user["email"])
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
	return _response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: AuthCredentials, driver: Driver = Depends(get_driver)):
	with driver.session() as session:
		user = auth_service.authenticate(session, payload.email, payload.password)
	if not user:
		raise HTTPException(status_code=401, detail="Nieprawidłowy e-mail lub hasło.")
	return _response(user)


@router.get("/me", response_model=UserResponse)
def me(authorization: str | None = Header(default=None)):
	if not authorization or not authorization.lower().startswith("bearer "):
		raise HTTPException(status_code=401, detail="Brak autoryzacji.")
	payload = auth_service.verify_token(authorization.split(" ", 1)[1])
	if not payload:
		raise HTTPException(status_code=401, detail="Sesja wygasła.")
	return UserResponse(id=payload["sub"], email=payload["email"])
