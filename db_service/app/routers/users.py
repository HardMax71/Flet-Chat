# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app import schemas
from app.database import get_uow
from app.dependencies import get_current_active_user
from app.uow import UnitOfWork
from typing import List, Optional

router = APIRouter()

@router.get("/users/", response_model=List[schemas.User])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    username: Optional[str] = Query(None, description="Filter users by username"),
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        users = await uow.users.get_all(skip=skip, limit=limit, username=username)
        return users

@router.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_active_user)):
    return current_user

@router.put("/users/me", response_model=schemas.User)
async def update_user(
    user_update: schemas.UserUpdate,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        updated_user = await uow.users.update(current_user.id, user_update)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user

@router.delete("/users/me", status_code=204)
async def delete_user(
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        deleted = await uow.users.delete(current_user.id)
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@router.get("/users/search", response_model=List[schemas.UserBasic])
async def search_users(
    query: str,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        users = await uow.users.search_users(query, current_user.id)
        return users