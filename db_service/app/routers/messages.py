# app/routers/messages.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app import schemas
from app.database import get_uow
from app.dependencies import get_current_active_user
from app.uow import UnitOfWork
from typing import List, Optional

router = APIRouter()

@router.post("/messages/", response_model=schemas.Message)
async def create_message(
    message: schemas.MessageCreate,
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        return await uow.messages.create(message, current_user.id)

@router.get("/messages/{chat_id}", response_model=List[schemas.Message])
async def read_messages(
    chat_id: int,
    skip: int = 0,
    limit: int = 100,
    content: Optional[str] = Query(None, description="Filter messages by content"),
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        messages = await uow.messages.get_all(chat_id, current_user.id, skip=skip, limit=limit, content=content)
        return messages

@router.put("/messages/{message_id}", response_model=schemas.Message)
async def update_message(
    message_id: int,
    message_update: schemas.MessageUpdate,
    uow: UnitOfWork = Depends(get_uow),
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
    uow: UnitOfWork = Depends(get_uow),
    current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        deleted = await uow.messages.delete(message_id, current_user.id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Message not found or not authorized")
    return {"message": "Message deleted successfully"}