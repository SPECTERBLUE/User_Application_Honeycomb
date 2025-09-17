from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    secret: str

class UserLogin(BaseModel):
    email: EmailStr
    secret: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class SecretUpdate(BaseModel):
    old_secret: str
    new_secret: str

class IdentityUpdate(BaseModel):
    new_email: EmailStr
