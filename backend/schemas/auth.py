from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    id: str
    username: str
    email: str
    company_name: str | None = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    company_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    remember: bool = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class MeResponse(BaseModel):
    user: AuthUser
