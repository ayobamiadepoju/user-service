from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError
from app.db.database import get_db
from app.db.cache import get_redis
from app.db.models import User
from app.schemas.token import Token, AccessToken, RefreshTokenRequest, TokenData
from app.schemas.response import GenericResponse
from app.services.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.services.metrics import login_attempts_total, token_refresh_total

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    token_type: str = payload.get("type")
    
    if email is None or token_type != "access":
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_user_from_refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
    )
    
    payload = decode_token(refresh_data.refresh_token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    token_type: str = payload.get("type")
    
    if email is None or token_type != "refresh":
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

@router.post("/login", response_model=GenericResponse[Token])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        login_attempts_total.labels(status='failed').inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    login_attempts_total.labels(status='success').inc()
    
    return GenericResponse(
        success=True,
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        ),
        message="Login successful"
    )

@router.post("/refresh", response_model=GenericResponse[AccessToken])
async def refresh_token(
    user: User = Depends(get_user_from_refresh_token)
):
    try:
        access_token = create_access_token(data={"sub": user.email})
        token_refresh_total.labels(status='success').inc()
        
        return GenericResponse(
            success=True,
            data=AccessToken(
                access_token=access_token,
                token_type="bearer"
            ),
            message="Token refreshed successfully"
        )
    except Exception as e:
        token_refresh_total.labels(status='failed').inc()
        raise