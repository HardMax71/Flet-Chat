# app/api/auth.py
import datetime
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import (
    get_config,
    get_security_service,
    get_token_interactor,
    get_user_interactor,
    oauth2_scheme,
)
from app.config import AppConfig
from app.infrastructure import schemas
from app.infrastructure.security import SecurityService
from app.interactors.token_interactor import TokenInteractor
from app.interactors.user_interactor import UserInteractor

router = APIRouter()


@router.post("/login", response_model=schemas.TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_interactor: UserInteractor = Depends(get_user_interactor),
    token_interactor: TokenInteractor = Depends(get_token_interactor),
    config: AppConfig = Depends(get_config),
    security_service: SecurityService = Depends(get_security_service),
):
    user = await user_interactor.verify_user_password(
        form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = datetime.timedelta(
        minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token, access_expire = security_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token, _ = security_service.create_refresh_token(
        data={"sub": user.username}
    )

    token_create = schemas.TokenCreate(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_at=access_expire,
        user_id=user.id,
    )
    token = await token_interactor.create_token(token_create)

    return token


@router.post("/register", response_model=schemas.User)
async def register_user(
    user: schemas.UserCreate,
    user_interactor: UserInteractor = Depends(get_user_interactor),
):
    existing_user = await user_interactor.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    existing_email = await user_interactor.get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await user_interactor.create_user(user)
    if not new_user:
        raise HTTPException(status_code=400, detail="User creation failed")
    return new_user


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_token(
    refresh_token_request: schemas.RefreshTokenRequest,
    token_interactor: TokenInteractor = Depends(get_token_interactor),
    user_interactor: UserInteractor = Depends(get_user_interactor),
    security_service: SecurityService = Depends(get_security_service),
    config: AppConfig = Depends(get_config),
):
    token = await token_interactor.get_token_by_refresh_token(
        refresh_token_request.refresh_token
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = security_service.decode_refresh_token(token.refresh_token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_interactor.get_user_by_username(username)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Delete the old refresh token
    await token_interactor.delete_token_by_refresh_token(
        refresh_token_request.refresh_token
    )

    # Create new tokens
    new_access_token, new_access_token_expires = security_service.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token, _ = security_service.create_refresh_token(
        data={"sub": user.username}
    )

    token_create = schemas.TokenCreate(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_at=new_access_token_expires,
        user_id=user.id,
    )
    new_token = await token_interactor.create_token(token_create)

    return new_token


@router.post("/logout", status_code=204)
async def logout(
    token: str = Depends(oauth2_scheme),
    token_interactor: TokenInteractor = Depends(get_token_interactor),
):
    deleted = await token_interactor.delete_token_by_access_token(token)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
