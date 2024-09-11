from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import schemas
from app.infrastructure.database import get_session
from app.infrastructure.security import decode_access_token
from app.infrastructure.unit_of_work import UnitOfWork

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_uow(session: AsyncSession = Depends(get_session)):
    return UnitOfWork(session)

async def get_current_user(token: str = Depends(oauth2_scheme), uow: UnitOfWork = Depends(get_uow)):
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    async with uow:
        user = await uow.users.get_by_username(username)
        # Check if the token is still valid (not logged out)
        valid_token = await uow.tokens.get_by_access_token(token)
        if user is None or valid_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return user

async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user