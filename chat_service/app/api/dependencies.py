from app.config import AppConfig
from app.domain import schemas
from app.infrastructure.security import SecurityService
from app.infrastructure.unit_of_work import UnitOfWork
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_security_service(request: Request) -> SecurityService:
    return request.app.state.security_service


async def get_session(request: Request) -> AsyncSession:
    async for session in request.app.state.database.get_session():
        yield session


async def get_uow(
        session: AsyncSession = Depends(get_session),
        config: AppConfig = Depends(get_config),
) -> UnitOfWork:
    return UnitOfWork(session, config)


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        uow: UnitOfWork = Depends(get_uow),
        security_service: SecurityService = Depends(get_security_service),
):
    username = security_service.decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    async with uow:
        user = await uow.users.get_by_username(username)
        valid_token = await uow.tokens.get_by_access_token(token)
        if user is None or valid_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return user


async def get_current_active_user(
        current_user: schemas.User = Depends(get_current_user)
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
