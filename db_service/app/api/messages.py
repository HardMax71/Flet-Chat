# app/api/messages.py
import json
from typing import List, Optional

from app.api.dependencies import get_uow, get_current_active_user
from app.domain import schemas
from app.infrastructure.redis_config import get_redis_client
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

        # Publish an event to Redis
        channel_name = f"chat:{message.chat_id}"
        message_data = schemas.Message.from_orm(db_message).model_dump_json()
        redis_client = await get_redis_client()
        await redis_client.publish(channel_name, message_data)  # Async publish

        # Update unread count for other chat members
        chat_members = await uow.chats.get_chat_members(message.chat_id)
        for member in chat_members:
            if member.id != current_user.id:
                unread_count = await uow.chats.get_unread_messages_count(message.chat_id, member.id)
                unread_count_channel = f"chat:{message.chat_id}:unread_count:{member.id}"
                unread_count_data = json.dumps({
                    "chat_id": message.chat_id,
                    "unread_count": unread_count,
                    "user_id": member.id
                })
                await redis_client.publish(unread_count_channel, unread_count_data)

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

        # Publish an event to Redis asynchronously
        channel_name = f"chat:{updated_message.chat_id}:status"
        status_data = schemas.MessageStatus.from_orm(message_status).model_dump_json()
        try:
            redis_client = await get_redis_client()
            await redis_client.publish(channel_name, status_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to publish status update")

        # Update unread count for the current user asynchronously
        try:
            unread_count = await uow.chats.get_unread_messages_count(updated_message.chat_id, current_user.id)
            unread_count_channel = f"chat:{updated_message.chat_id}:unread_count:{current_user.id}"
            unread_count_data = json.dumps({
                "chat_id": updated_message.chat_id,
                "unread_count": unread_count,
                "user_id": current_user.id
            })
            await redis_client.publish(unread_count_channel, unread_count_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to publish unread count")

        return updated_message

