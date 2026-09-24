from pydantic import BaseModel, EmailStr, Field


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = Field(
        default=None,
        min_length=12,
    )
    temporary_password: bool = True


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool | None = None