# app/api/messages.py
from typing import List, Optional

from app.api.dependencies import get_message_interactor, get_current_active_user, get_event_dispatcher, \
    get_chat_interactor
from app.domain import schemas
from app.domain.events import MessageCreated, MessageDeleted, MessageUpdated, MessageStatusUpdated, UnreadCountUpdated
from app.infrastructure.event_dispatcher import EventDispatcher
from app.interactors.message_interactor import MessageInteractor
from fastapi import APIRouter, Depends, HTTPException, Query


def create_router():
    router = APIRouter()

    @router.post("/", response_model=schemas.Message)
    async def create_message(
            message: schemas.MessageCreate,
            message_interactor: MessageInteractor = Depends(get_message_interactor),
            chat_interactor: MessageInteractor = Depends(get_chat_interactor),
            current_user: schemas.User = Depends(get_current_active_user),
            event_dispatcher: EventDispatcher = Depends(get_event_dispatcher)
    ):
        try:
            db_message = await message_interactor.create_message(message, current_user.id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

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

        unread_counts = await chat_interactor.get_unread_counts_for_chat_members(db_message.chat_id, current_user.id)
        for user_id, unread_count in unread_counts.items():
            await event_dispatcher.dispatch(UnreadCountUpdated(
                chat_id=db_message.chat_id,
                user_id=user_id,
                unread_count=unread_count
            ))

        return db_message

    @router.get("/{chat_id}", response_model=List[schemas.Message])
    async def read_messages(
            chat_id: int,
            skip: int = 0,
            limit: int = 100,
            content: Optional[str] = Query(None, description="Filter messages by content"),
            message_interactor: MessageInteractor = Depends(get_message_interactor),
            current_user: schemas.User = Depends(get_current_active_user)
    ):
        messages = await message_interactor.get_messages(chat_id, current_user.id, skip, limit, content)
        return messages

    @router.put("/{message_id}", response_model=schemas.Message)
    async def update_message(
            message_id: int,
            message_update: schemas.MessageUpdate,
            message_interactor: MessageInteractor = Depends(get_message_interactor),
            current_user: schemas.User = Depends(get_current_active_user),
            event_dispatcher: EventDispatcher = Depends(get_event_dispatcher)
    ):
        updated_message = await message_interactor.update_message(message_id, message_update, current_user.id)
        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found or you're not authorized to update it")

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

    @router.delete("/{message_id}", status_code=200, response_model=schemas.Message)
    async def delete_message(
            message_id: int,
            message_interactor: MessageInteractor = Depends(get_message_interactor),
            current_user: schemas.User = Depends(get_current_active_user),
            event_dispatcher: EventDispatcher = Depends(get_event_dispatcher)
    ):
        deleted_message = await message_interactor.delete_message(message_id, current_user.id)
        if not deleted_message:
            raise HTTPException(status_code=404, detail="Message not found or you're not authorized to delete it")

        await event_dispatcher.dispatch(MessageDeleted(
            message_id=deleted_message.id,
            chat_id=deleted_message.chat_id,
            user_id=deleted_message.user_id,
            created_at=deleted_message.created_at,
            content=deleted_message.content,
            updated_at=deleted_message.updated_at,
            user={
                "id": current_user.id,
                "username": current_user.username
            },
            is_deleted=deleted_message.is_deleted
        ))

        return deleted_message

    @router.put("/{message_id}/status", response_model=schemas.Message)
    async def update_message_status(
            message_id: int,
            status_update: schemas.MessageStatusUpdate,
            message_interactor: MessageInteractor = Depends(get_message_interactor),
            chat_interactor: MessageInteractor = Depends(get_chat_interactor),
            current_user: schemas.User = Depends(get_current_active_user),
            event_dispatcher: EventDispatcher = Depends(get_event_dispatcher)
    ):
        updated_message = await message_interactor.update_message_status(message_id, current_user.id, status_update)
        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found")

        message_status = next(
            (status for status in updated_message.statuses if status.user_id == current_user.id),
            None
        )
        if not message_status:
            raise HTTPException(status_code=404, detail="MessageStatus not found")

        await event_dispatcher.dispatch(MessageStatusUpdated(
            message_id=updated_message.id,
            chat_id=updated_message.chat_id,
            user_id=current_user.id,
            is_read=message_status.is_read,
            read_at=message_status.read_at
        ))

        unread_count = await chat_interactor.get_unread_messages_count(updated_message.chat_id, current_user.id)

        await event_dispatcher.dispatch(UnreadCountUpdated(
            chat_id=updated_message.chat_id,
            user_id=current_user.id,
            unread_count=unread_count
        ))

        return updated_message

    return router
