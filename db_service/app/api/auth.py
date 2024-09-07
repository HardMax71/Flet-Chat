# app/api/auth.py
from datetime import timedelta

from app.api.dependencies import get_uow
from app.config import settings
from app.domain import schemas
from app.infrastructure.security import (verify_password, create_access_token,
                                         create_refresh_token, decode_refresh_token)
from app.infrastructure.unit_of_work import UnitOfWork
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/auth/login", response_model=schemas.TokenResponse)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        uow: UnitOfWork = Depends(get_uow)
):
    async with uow:
        user = await uow.users.get_by_username(form_data.username)
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token, access_expire = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        refresh_token, refresh_expire = create_refresh_token(data={"sub": user.username})

        # Save tokens to database
        token = schemas.TokenCreate(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_at=access_expire,
            user_id=user.id
        )
        await uow.tokens.create(token)

        return schemas.TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_at=access_expire,
            user_id=user.id
        )


@router.post("/auth/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, uow: UnitOfWork = Depends(get_uow)):
    async with uow:
        db_user = await uow.users.get_by_username(user.username)
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        return await uow.users.create(user)


@router.post("/auth/refresh", response_model=schemas.TokenResponse)
async def refresh_token(
        refresh_token_request: schemas.RefreshTokenRequest,
        uow: UnitOfWork = Depends(get_uow)
):
    async with uow:
        token = await uow.tokens.get_by_refresh_token(refresh_token_request.refresh_token)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username = decode_refresh_token(token.refresh_token)
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )


        user = await uow.users.get_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        new_access_token, new_access_token_expires = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        new_refresh_token, new_refresh_token_expires = create_refresh_token(
            data={"sub": user.username}
        )

        token.access_token = new_access_token
        token.refresh_token = new_refresh_token
        token.expires_at = new_access_token_expires
        await uow.tokens.update(token)

        return schemas.TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_at=new_access_token_expires,
            user_id=user.id
        )
