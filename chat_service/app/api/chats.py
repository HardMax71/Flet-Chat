from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from app.domain import schemas
from app.infrastructure.unit_of_work import AbstractUnitOfWork
from app.api.dependencies import get_uow, get_current_active_user

def create_router():
    router = APIRouter()

    @router.post("/", response_model=schemas.Chat)
    async def create_chat(
            chat: schemas.ChatCreate,
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            return await uow.chats.create(chat, current_user.id)

    @router.get("/", response_model=List[schemas.Chat])
    async def read_chats(
            skip: int = 0,
            limit: int = 100,
            name: Optional[str] = Query(None, description="Filter chats by name"),
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            return await uow.chats.get_all(current_user.id, skip=skip, limit=limit, name=name)

    @router.post("/start", response_model=schemas.Chat)
    async def start_chat(
            other_user_id: int = Body(..., embed=True, description="ID of the user to start a chat with"),
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            chat = await uow.chats.start_chat(current_user.id, other_user_id)
            if not chat:
                raise HTTPException(status_code=404, detail="User not found")
            return chat

    @router.get("/{chat_id}", response_model=schemas.Chat)
    async def read_chat(
            chat_id: int,
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            db_chat = await uow.chats.get_by_id(chat_id, current_user.id)
            if db_chat is None:
                raise HTTPException(status_code=404, detail="Chat not found")
            return db_chat

    @router.put("/{chat_id}", response_model=schemas.Chat)
    async def update_chat(
            chat_id: int,
            chat_update: schemas.ChatUpdate,
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            db_chat = await uow.chats.get_by_id(chat_id, current_user.id)
            if db_chat is None:
                raise HTTPException(status_code=404, detail="Chat not found")
            updated_chat = await uow.chats.update(chat_id, chat_update, current_user.id)
            if not updated_chat:
                raise HTTPException(status_code=404, detail="Chat not found")
            return updated_chat

    @router.delete("/{chat_id}", status_code=204)
    async def delete_chat(
            chat_id: int,
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            db_chat = await uow.chats.get_by_id(chat_id, current_user.id)
            if db_chat is None:
                raise HTTPException(status_code=404, detail="Chat not found")
            deleted = await uow.chats.delete(chat_id, current_user.id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Chat not found")
        return {"message": "Chat deleted successfully"}

    @router.get("/{chat_id}/members", response_model=List[schemas.User])
    async def get_chat_members(
            chat_id: int,
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            chat = await uow.chats.get_by_id(chat_id, current_user.id)
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found or you're not a member")
            members = await uow.chats.get_chat_members(chat_id)
            return members

    @router.post("/{chat_id}/members", response_model=schemas.Chat)
    async def add_chat_member(
            chat_id: int,
            user_id: int = Body(..., embed=True),
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            updated_chat = await uow.chats.add_member(chat_id, user_id, current_user.id)
            if not updated_chat:
                raise HTTPException(status_code=404, detail="Chat or user not found")
            return updated_chat

    @router.delete("/{chat_id}/members/{user_id}", status_code=204)
    async def remove_chat_member(
            chat_id: int,
            user_id: int,
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            removed = await uow.chats.remove_member(chat_id, user_id, current_user.id)
            if not removed:
                raise HTTPException(status_code=404, detail="Chat or user not found")
        return {"message": "Member removed from chat successfully"}

    @router.get("/{chat_id}/unread_count", response_model=int)
    async def get_unread_messages_count(
            chat_id: int,
            uow: AbstractUnitOfWork = Depends(get_uow),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        async with uow:
            return await uow.chats.get_unread_messages_count(chat_id, current_user.id)

    return router