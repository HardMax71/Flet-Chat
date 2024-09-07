from app.domain import schemas
from app.infrastructure.database import SessionLocal
from app.infrastructure.security import decode_access_token
from app.infrastructure.unit_of_work import UnitOfWork
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_uow(db: Session = Depends(get_db)):
    return UnitOfWork(db)


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
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
