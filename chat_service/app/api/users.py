# app/api/users.py
from typing import List, Optional

from app.api.dependencies import get_user_interactor, get_current_active_user
from app.infrastructure import schemas
from app.interactors.user_interactor import UserInteractor
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    username: Optional[str] = Query(None, description="Filter users by username"),
    user_interactor: UserInteractor = Depends(get_user_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    users = await user_interactor.get_users(skip=skip, limit=limit, username=username)
    return users


@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=schemas.User)
async def update_user(
    user_update: schemas.UserUpdate,
    user_interactor: UserInteractor = Depends(get_user_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    updated_user = await user_interactor.update_user(current_user.id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


@router.delete("/me", status_code=204)
async def delete_user(
    user_interactor: UserInteractor = Depends(get_user_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    deleted = await user_interactor.delete_user(current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/search", response_model=List[schemas.UserBasic])
async def search_users(
    query: str,
    user_interactor: UserInteractor = Depends(get_user_interactor),
    current_user: schemas.User = Depends(get_current_active_user),
):
    users = await user_interactor.search_users(query, current_user.id)
    return users
