# app/routers/chats.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app import schemas
from app.database import get_uow
from app.dependencies import get_current_active_user
from app.uow import UnitOfWork
from typing import List, Optional

router = APIRouter()

@router.post("/chats/", response_model=schemas.Chat)
async def create_chat(
    chat: schemas.ChatCreate,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        return await uow.chats.create(chat, current_user.id)

@router.get("/chats/", response_model=List[schemas.Chat])
async def read_chats(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = Query(None, description="Filter chats by name"),
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        return await uow.chats.get_all(current_user.id, skip=skip, limit=limit, name=name)

@router.post("/chats/start", response_model=schemas.Chat)
async def start_chat(
    other_user_id: int = Query(..., description="ID of the user to start a chat with"),
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        chat = await uow.chats.start_chat(current_user.id, other_user_id)
        if not chat:
            raise HTTPException(status_code=404, detail="User not found")
        return chat

@router.get("/chats/{chat_id}", response_model=schemas.Chat)
async def read_chat(
    chat_id: int,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        db_chat = await uow.chats.get_by_id(chat_id, current_user.id)
        if db_chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        return db_chat

@router.put("/chats/{chat_id}", response_model=schemas.Chat)
async def update_chat(
    chat_id: int,
    chat_update: schemas.ChatUpdate,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        db_chat = await uow.chats.get_by_id(chat_id, current_user.id)
        if db_chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        updated_chat = await uow.chats.update(chat_id, chat_update)
        if not updated_chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        return updated_chat

@router.delete("/chats/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: int,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        db_chat = await uow.chats.get_by_id(chat_id, current_user.id)
        if db_chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")
        deleted = await uow.chats.delete(chat_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Chat not found")
    return {"message": "Chat deleted successfully"}

@router.post("/chats/{chat_id}/members", response_model=schemas.Chat)
async def add_chat_member(
    chat_id: int,
    user_id: int,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        updated_chat = await uow.chats.add_member(chat_id, user_id)
        if not updated_chat:
            raise HTTPException(status_code=404, detail="Chat or user not found")
        return updated_chat

@router.delete("/chats/{chat_id}/members/{user_id}", status_code=204)
async def remove_chat_member(
    chat_id: int,
    user_id: int,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        removed = await uow.chats.remove_member(chat_id, user_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Chat or user not found")
    return {"message": "Member removed from chat successfully"}