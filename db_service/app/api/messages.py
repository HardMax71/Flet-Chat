# app/api/messages.py
from typing import List, Optional

from app.api.dependencies import get_uow, get_current_active_user
from app.domain import schemas
from app.infrastructure.unit_of_work import AbstractUnitOfWork
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter()


@router.post("/messages/", response_model=schemas.Message)
async def create_message(
        message: schemas.MessageCreate,
        uow: AbstractUnitOfWork = Depends(get_uow),
        current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        # Check if the chat exists and the user is a member
        chat_exists = await uow.messages.check_chat_exists_and_user_is_member(message.chat_id, current_user.id)
        if not chat_exists:
            raise HTTPException(status_code=404, detail="Chat not found or user is not a member")

        db_message = await uow.messages.create(message, current_user.id)
        return db_message


@router.get("/messages/{chat_id}", response_model=List[schemas.Message])
async def read_messages(
        chat_id: int,
        skip: int = 0,
        limit: int = 100,
        content: Optional[str] = Query(None, description="Filter messages by content"),
        uow: AbstractUnitOfWork = Depends(get_uow),
        current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        messages = await uow.messages.get_all(chat_id, current_user.id, skip=skip, limit=limit, content=content)
        return messages


@router.put("/messages/{message_id}", response_model=schemas.Message)
async def update_message(
        message_id: int,
        message_update: schemas.MessageUpdate,
        uow: AbstractUnitOfWork = Depends(get_uow),
        current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        updated_message = await uow.messages.update(message_id, message_update, current_user.id)
        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found or not authorized")
        return updated_message


@router.delete("/messages/{message_id}", status_code=204)
async def delete_message(
        message_id: int,
        uow: AbstractUnitOfWork = Depends(get_uow),
        current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        deleted = await uow.messages.delete(message_id, current_user.id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Message not found or not authorized")
    return {"message": "Message deleted successfully"}


@router.put("/messages/{message_id}/status", response_model=schemas.Message)
async def update_message_status(
        message_id: int,
        status_update: schemas.MessageStatusUpdate,
        uow: AbstractUnitOfWork = Depends(get_uow),
        current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        updated_message = await uow.messages.update_message_status(message_id, current_user.id, status_update)
        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found")
        return updated_message
