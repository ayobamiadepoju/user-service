from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import json
from app.db.database import get_db
from app.db.cache import get_redis
from app.db.models import User, UserPreference
from app.schemas.user import UserCreate, User as UserSchema, UserUpdatePushToken, UserUpdatePreferences
from app.schemas.response import GenericResponse
from app.services.security import get_password_hash
from app.api.v1.routes.auth import get_current_user
from app.services.metrics import (
    user_registrations_total,
    cache_operations_total,
    cache_hit_rate,
    active_users_gauge
)

router = APIRouter()

@router.post("/", response_model=GenericResponse[UserSchema], status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(db_user)
    db.flush()
    
    db_preference = UserPreference(
        user_id=db_user.id,
        email=user_data.preferences.email,
        push=user_data.preferences.push
    )
    db.add(db_preference)
    db.commit()
    db.refresh(db_user)
    
    user_registrations_total.inc()
    active_users_gauge.set(db.query(User).count())
    
    return GenericResponse(
        success=True,
        data=UserSchema.model_validate(db_user),
        message="User created successfully"
    )

@router.get("/{user_id}", response_model=GenericResponse[UserSchema])
async def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    cache = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    cache_key = f"user:{user_id}"
    cached_user = cache.get(cache_key)
    
    if cached_user:
        cache_hit_rate.labels(result='hit').inc()
        cache_operations_total.labels(operation='get', status='hit').inc()
        user_data = json.loads(cached_user)
        return GenericResponse(
            success=True,
            data=user_data,
            message="User retrieved from cache"
        )
    
    cache_hit_rate.labels(result='miss').inc()
    cache_operations_total.labels(operation='get', status='miss').inc()
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_schema = UserSchema.model_validate(user)
    cache.setex(cache_key, 3600, user_schema.model_dump_json())
    cache_operations_total.labels(operation='set', status='success').inc()
    
    return GenericResponse(
        success=True,
        data=user_schema,
        message="User retrieved successfully"
    )

@router.get("/", response_model=GenericResponse[List[UserSchema]])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    users = db.query(User).offset(skip).limit(limit).all()
    
    return GenericResponse(
        success=True,
        data=[UserSchema.model_validate(user) for user in users],
        message="Users retrieved successfully"
    )

@router.put("/{user_id}/push-token", response_model=GenericResponse[UserSchema])
async def update_push_token(
    user_id: uuid.UUID,
    token_data: UserUpdatePushToken,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache = Depends(get_redis)
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.push_token = token_data.push_token
    db.commit()
    db.refresh(user)
    
    cache.delete(f"user:{user_id}")
    cache_operations_total.labels(operation='delete', status='success').inc()
    
    return GenericResponse(
        success=True,
        data=UserSchema.model_validate(user),
        message="Push token updated successfully"
    )

@router.put("/{user_id}/preferences", response_model=GenericResponse[UserSchema])
async def update_preferences(
    user_id: uuid.UUID,
    preferences_data: UserUpdatePreferences,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache = Depends(get_redis)
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.preferences.email = preferences_data.preferences.email
    user.preferences.push = preferences_data.preferences.push
    db.commit()
    db.refresh(user)
    
    cache.delete(f"user:{user_id}")
    cache_operations_total.labels(operation='delete', status='success').inc()
    
    return GenericResponse(
        success=True,
        data=UserSchema.model_validate(user),
        message="Preferences updated successfully"
    )