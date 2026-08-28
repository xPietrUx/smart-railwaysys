from pydantic import BaseModel, Field


class AuthCredentials(BaseModel):
	email: str = Field(min_length=3, max_length=254)
	password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
	id: str
	email: str
	role: str
	permissions: list[str] = []


class TokenResponse(BaseModel):
	access_token: str
	token_type: str = "bearer"
	user: UserResponse


class GuestContext(BaseModel):
	role: str = "guest"
	permissions: list[str] = []


# --- Panel administratora ---------------------------------------------------


class AdminUser(BaseModel):
	id: str
	email: str
	role: str
	active: bool
	created_at: float | None = None


class UserCreateRequest(BaseModel):
	email: str = Field(min_length=3, max_length=254)
	password: str = Field(min_length=8, max_length=128)
	role: str = "user"


class UserUpdateRequest(BaseModel):
	email: str | None = Field(default=None, max_length=254)
	role: str | None = None
	active: bool | None = None


class PasswordResetRequest(BaseModel):
	password: str = Field(min_length=8, max_length=128)


class RoleModel(BaseModel):
	name: str
	label: str
	permissions: list[str]
	is_system: bool


class RoleCreateRequest(BaseModel):
	name: str = Field(min_length=2, max_length=31)
	label: str = Field(default="", max_length=60)
	permissions: list[str] = []


class RoleUpdateRequest(BaseModel):
	label: str | None = Field(default=None, max_length=60)
	permissions: list[str] | None = None


class PermissionInfo(BaseModel):
	key: str
	label: str
