from pydantic import BaseModel, Field


class AuthCredentials(BaseModel):
	email: str = Field(min_length=3, max_length=254)
	password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
	id: str
	email: str


class TokenResponse(BaseModel):
	access_token: str
	token_type: str = "bearer"
	user: UserResponse
