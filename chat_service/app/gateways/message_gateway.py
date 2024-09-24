# app/gateways/message_gateway.py
from datetime import datetime
from typing import List, Optional, Dict

from app.domain import models, schemas
from app.infrastructure.uow import UnitOfWork, UoWModel


class MessageGateway:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_message(self, message_id: int, user_id: int) -> Optional[UoWModel]:
        message = await self.uow.mappers[models.Message].get_message(message_id, user_id)
        return UoWModel(message, self.uow) if message else None

    async def get_all(self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100,
                      content: Optional[str] = None) -> List[UoWModel]:
        messages = await self.uow.mappers[models.Message].get_all(chat_id, user_id, skip, limit, content)
        return [UoWModel(message, self.uow) for message in messages]

    async def create_message(self, message: schemas.MessageCreate, user_id: int) -> UoWModel:
        chat = await self.uow.mappers[models.Chat].get_chat(message.chat_id, user_id)
        if not chat:
            raise ValueError(f"Chat with id {message.chat_id} not found or user is not a member")

        db_message = models.Message(content=message.content,
                                    chat_id=message.chat_id,
                                    user_id=user_id)

        created_message = await self.uow.mappers[models.Message].create_message_with_statuses(db_message, chat.members)
        return UoWModel(created_message, self.uow)

    async def update_message(self, message_id: int, message_update: schemas.MessageUpdate, user_id: int) -> Optional[
        UoWModel]:
        message = await self.uow.mappers[models.Message].update_message(message_id, message_update, user_id)
        if message:
            return UoWModel(message, self.uow)
        return None

    async def delete_message(self, message_id: int, user_id: int) -> Optional[UoWModel]:
        message = await self.uow.mappers[models.Message].delete_message(message_id, user_id)
        if message:
            return UoWModel(message, self.uow)
        return None

    async def update_message_status(self, message_id: int, user_id: int, status_update: schemas.MessageStatusUpdate) -> Optional[UoWModel]:
        updated_message = await self.uow.mappers[models.Message].update_message_status(message_id, user_id, status_update)
        if updated_message:
            return UoWModel(updated_message, self.uow)
        return None

    async def get_unread_counts_for_chat_members(self, chat_id: int, current_user_id: int) -> Dict[int, int]:
        return await self.uow.mappers[models.Message].get_unread_counts_for_chat_members(chat_id, current_user_id)

    async def get_unread_messages_count(self, chat_id: int, user_id: int) -> int:
        return await self.uow.mappers[models.Message].get_unread_messages_count(chat_id, user_id)
