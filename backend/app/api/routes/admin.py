from fastapi import APIRouter, Depends, HTTPException
from neo4j import Driver

from app.api.dependencies import get_driver, require_permission
from app.schemas.auth import (
	AdminUser,
	PasswordResetRequest,
	PermissionInfo,
	RoleCreateRequest,
	RoleModel,
	RoleUpdateRequest,
	UserCreateRequest,
	UserUpdateRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/permissions", response_model=list[PermissionInfo])
def list_permissions(_: dict = Depends(require_permission("users.manage"))):
	return [PermissionInfo(key=key, label=label) for key, label in auth_service.PERMISSIONS.items()]


# --- Użytkownicy ------------------------------------------------------------


@router.get("/users", response_model=list[AdminUser])
def list_users(
	driver: Driver = Depends(get_driver),
	_: dict = Depends(require_permission("users.manage")),
):
	with driver.session() as session:
		return auth_service.list_users(session)


@router.post("/users", response_model=AdminUser, status_code=201)
def create_user(
	payload: UserCreateRequest,
	driver: Driver = Depends(get_driver),
	_: dict = Depends(require_permission("users.manage")),
):
	with driver.session() as session:
		if not auth_service.role_exists(session, payload.role):
			raise HTTPException(status_code=422, detail="Wybrana rola nie istnieje.")
		try:
			user = auth_service.create_user(session, payload.email, payload.password, payload.role)
		except ValueError as exc:
			raise HTTPException(status_code=422, detail=str(exc)) from exc
		if not user:
			raise HTTPException(status_code=409, detail="Konto z tym adresem e-mail już istnieje.")
		return auth_service.public_user(user)


@router.patch("/users/{user_id}", response_model=AdminUser)
def update_user(
	user_id: str,
	payload: UserUpdateRequest,
	driver: Driver = Depends(get_driver),
	_: dict = Depends(require_permission("users.manage")),
):
	with driver.session() as session:
		try:
			user = auth_service.update_user(
				session,
				user_id,
				email=payload.email,
				role=payload.role,
				active=payload.active,
			)
		except ValueError as exc:
			raise HTTPException(status_code=422, detail=str(exc)) from exc
	if not user:
		raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika.")
	return user


@router.post("/users/{user_id}/password", status_code=204)
def reset_password(
	user_id: str,
	payload: PasswordResetRequest,
	driver: Driver = Depends(get_driver),
	_: dict = Depends(require_permission("users.manage")),
):
	with driver.session() as session:
		try:
			user = auth_service.set_user_password(session, user_id, payload.password)
		except ValueError as exc:
			raise HTTPException(status_code=422, detail=str(exc)) from exc
	if not user:
		raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika.")


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
	user_id: str,
	driver: Driver = Depends(get_driver),
	current: dict = Depends(require_permission("users.manage")),
):
	if user_id == current["id"]:
		raise HTTPException(status_code=400, detail="Nie możesz usunąć własnego konta.")
	with driver.session() as session:
		try:
			deleted = auth_service.delete_user(session, user_id)
		except ValueError as exc:
			raise HTTPException(status_code=422, detail=str(exc)) from exc
	if not deleted:
		raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika.")


# --- Role -------------------------------------------------------------------


@router.get("/roles", response_model=list[RoleModel])
def list_roles(
	driver: Driver = Depends(get_driver),
	_: dict = Depends(require_permission("users.manage")),
):
	with driver.session() as session:
		return auth_service.list_roles(session)


@router.post("/roles", response_model=RoleModel, status_code=201)
def create_role(
	payload: RoleCreateRequest,
	driver: Driver = Depends(get_driver),
	_: dict = Depends(require_permission("roles.manage")),
):
	with driver.session() as session:
		try:
			return auth_service.create_role(session, payload.name, payload.label, payload.permissions)
		except ValueError as exc:
			raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/roles/{name}", response_model=RoleModel)
def update_role(
	name: str,
	payload: RoleUpdateRequest,
	driver: Driver = Depends(get_driver),
	_: dict = Depends(require_permission("roles.manage")),
):
	with driver.session() as session:
		try:
			role = auth_service.update_role(
				session, name, label=payload.label, permissions=payload.permissions
			)
		except ValueError as exc:
			raise HTTPException(status_code=422, detail=str(exc)) from exc
	if not role:
		raise HTTPException(status_code=404, detail="Nie znaleziono roli.")
	return role


@router.delete("/roles/{name}", status_code=204)
def delete_role(
	name: str,
	driver: Driver = Depends(get_driver),
	_: dict = Depends(require_permission("roles.manage")),
):
	with driver.session() as session:
		try:
			deleted = auth_service.delete_role(session, name)
		except ValueError as exc:
			raise HTTPException(status_code=422, detail=str(exc)) from exc
	if not deleted:
		raise HTTPException(status_code=404, detail="Nie znaleziono roli.")
