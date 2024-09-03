# app/routers/auth.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app import schemas
from app.database import get_uow
from app.security import verify_password, create_access_token
from app.config import settings
from app.uow import UnitOfWork

router = APIRouter()

@router.post("/auth/login", response_model=schemas.Token)
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
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, uow: UnitOfWork = Depends(get_uow)):
    async with uow:
        db_user = await uow.users.get_by_username(user.username)
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        return await uow.users.create(user)