# app/interactors/message_interactor.py
from typing import List, Optional

from app.gateways.message_gateway import MessageGateway
from app.infrastructure import schemas
from app.infrastructure.uow import UnitOfWork


class MessageInteractor:
    def __init__(self, uow: UnitOfWork, message_gateway: MessageGateway):
        self.uow = uow
        self.message_gateway = message_gateway

    async def get_message(self, message_id: int, user_id: int) -> Optional[schemas.Message]:
        message = await self.message_gateway.get_message(message_id, user_id)
        return schemas.Message.model_validate(message) if message else None

    async def get_messages(self, chat_id: int, user_id: int, skip: int = 0, limit: int = 100,
                           content: Optional[str] = None) -> List[schemas.Message]:
        messages = await self.message_gateway.get_all(chat_id, user_id, skip, limit, content)
        return [schemas.Message.model_validate(message) for message in messages]

    async def update_message_status(self, message_id: int, user_id: int, status_update: schemas.MessageStatusUpdate) -> \
    Optional[schemas.Message]:
        updated_message = await self.message_gateway.update_message_status(message_id, user_id, status_update)
        if updated_message:
            await self.uow.commit()
            return schemas.Message.model_validate(updated_message)
        return None

    async def create_message(self, message: schemas.MessageCreate, user_id: int) -> schemas.Message:
        new_message = await self.message_gateway.create_message(message, user_id)
        await self.uow.commit()
        return schemas.Message.model_validate(new_message)

    async def update_message(self, message_id: int, message_update: schemas.MessageUpdate, user_id: int) -> Optional[
        schemas.Message]:
        updated_message = await self.message_gateway.update_message(message_id, message_update, user_id)
        if updated_message:
            await self.uow.commit()
            return schemas.Message.model_validate(updated_message)
        return None

    async def delete_message(self, message_id: int, user_id: int) -> Optional[schemas.Message]:
        deleted_message = await self.message_gateway.delete_message(message_id, user_id)
        if deleted_message:
            await self.uow.commit()
            return schemas.Message.model_validate(deleted_message)
        return None
