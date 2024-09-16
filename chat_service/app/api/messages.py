# app/api/messages.py
from typing import List, Optional

from app.api.dependencies import get_uow, get_current_active_user
from app.domain import schemas
from app.domain.events import MessageCreated, MessageDeleted, MessageUpdated, MessageStatusUpdated, UnreadCountUpdated
from app.infrastructure.event_dispatcher import event_dispatcher
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
        chat_exists = await uow.messages.check_chat_exists_and_user_is_member(message.chat_id, current_user.id)
        if not chat_exists:
            raise HTTPException(status_code=404, detail="Chat not found or user is not a member")

        db_message = await uow.messages.create(message, current_user.id)

        # Dispatch MessageCreated event
        await event_dispatcher.dispatch(MessageCreated(
            message_id=db_message.id,
            chat_id=db_message.chat_id,
            user_id=db_message.user_id,
            content=db_message.content,
            created_at=db_message.created_at,
            user={
                "id": current_user.id,
                "username": current_user.username
            },
            is_deleted=db_message.is_deleted
        ))

        # Update unread count for other chat members
        chat_members = await uow.chats.get_chat_members(message.chat_id)
        for member in chat_members:
            if member.id != current_user.id:
                unread_count = await uow.chats.get_unread_messages_count(message.chat_id, member.id)
                # Dispatch UnreadCountUpdated event
                await event_dispatcher.dispatch(UnreadCountUpdated(
                    chat_id=message.chat_id,
                    user_id=member.id,
                    unread_count=unread_count
                ))
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

        # Dispatch MessageUpdated event
        await event_dispatcher.dispatch(MessageUpdated(
            message_id=updated_message.id,
            chat_id=updated_message.chat_id,
            user_id=updated_message.user_id,
            content=updated_message.content,
            created_at=updated_message.created_at,
            updated_at=updated_message.updated_at,
            user={
                "id": current_user.id,
                "username": current_user.username
            },
            is_deleted=updated_message.is_deleted
        ))

        return updated_message


@router.delete("/messages/{message_id}", status_code=200, response_model=schemas.Message)
async def delete_message(
        message_id: int,
        uow: AbstractUnitOfWork = Depends(get_uow),
        current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        deleted_message = await uow.messages.delete(message_id, current_user.id)
        if not deleted_message:
            raise HTTPException(status_code=404, detail="Message not found or not authorized")

        # Dispatch MessageDeleted event
        await event_dispatcher.dispatch(MessageDeleted(
            message_id=deleted_message.id,
            chat_id=deleted_message.chat_id,
            user_id=deleted_message.user_id,
            created_at=deleted_message.created_at,
            updated_at=deleted_message.updated_at,
            user={
                "id": current_user.id,
                "username": current_user.username
            },
            is_deleted=deleted_message.is_deleted
        ))

    return deleted_message


@router.put("/messages/{message_id}/status", response_model=schemas.Message)
async def update_message_status(
        message_id: int,
        status_update: schemas.MessageStatusUpdate,
        uow: AbstractUnitOfWork = Depends(get_uow),
        current_user: schemas.User = Depends(get_current_active_user)
):
    async with uow:
        # Update the message status in the database
        updated_message = await uow.messages.update_message_status(
            message_id, current_user.id, status_update
        )
        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Extract the MessageStatus instance for the current user
        message_status = next(
            (status for status in updated_message.statuses if status.user_id == current_user.id),
            None
        )
        if not message_status:
            raise HTTPException(status_code=404, detail="MessageStatus not found")

        # Dispatch MessageStatusUpdated event
        await event_dispatcher.dispatch(MessageStatusUpdated(
            message_id=updated_message.id,
            chat_id=updated_message.chat_id,
            user_id=current_user.id,
            is_read=message_status.is_read,
            read_at=message_status.read_at
        ))

        # Update unread count for the current user
        unread_count = await uow.chats.get_unread_messages_count(updated_message.chat_id, current_user.id)

        # Dispatch UnreadCountUpdated event
        await event_dispatcher.dispatch(UnreadCountUpdated(
            chat_id=updated_message.chat_id,
            user_id=current_user.id,
            unread_count=unread_count
        ))

        return updated_message
