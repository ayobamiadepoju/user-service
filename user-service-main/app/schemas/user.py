from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
import uuid

class UserPreferenceBase(BaseModel):
    email: bool = True
    push: bool = True

class UserPreferenceCreate(UserPreferenceBase):
    pass

class UserPreference(UserPreferenceBase):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: uuid.UUID

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    preferences: UserPreferenceCreate

class UserUpdatePushToken(BaseModel):
    push_token: str

class UserUpdatePreferences(BaseModel):
    preferences: UserPreferenceBase

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    email: EmailStr
    push_token: Optional[str] = None
    preferences: UserPreference