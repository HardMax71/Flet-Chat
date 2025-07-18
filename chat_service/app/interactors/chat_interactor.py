# app/interactors/chat_interactor.py


from app.gateways.interfaces import IChatGateway, IUserGateway
from app.infrastructure import schemas


class ChatInteractor:
    def __init__(self, chat_gateway: IChatGateway, user_gateway: IUserGateway):
        self.chat_gateway = chat_gateway
        self.user_gateway = user_gateway

    async def get_chat(self, chat_id: int, user_id: int) -> schemas.Chat | None:
        chat = await self.chat_gateway.get_chat(chat_id, user_id)
        return schemas.Chat.model_validate(chat) if chat else None

    async def get_chats(
        self, user_id: int, skip: int = 0, limit: int = 100, name: str | None = None
    ) -> list[schemas.Chat]:
        chats = await self.chat_gateway.get_all(user_id, skip, limit, name)
        return [schemas.Chat.model_validate(chat) for chat in chats]

    async def create_chat(
        self, chat: schemas.ChatCreate, user_id: int
    ) -> schemas.Chat | None:
        # Verify all members exist
        for member_id in chat.member_ids:
            user = await self.user_gateway.get_user(member_id)
            if not user:
                return None  # Invalid member

        new_chat = await self.chat_gateway.create_chat(chat, user_id)
        return schemas.Chat.model_validate(new_chat) if new_chat else None

    async def update_chat(
        self, chat_id: int, chat_update: schemas.ChatUpdate, user_id: int
    ) -> schemas.Chat | None:
        chat = await self.chat_gateway.get_chat(chat_id, user_id)
        if not chat:
            return None
        for key, value in chat_update.model_dump(exclude_unset=True).items():
            setattr(chat, key, value)
        return schemas.Chat.model_validate(chat)

    async def delete_chat(self, chat_id: int, user_id: int) -> bool:
        chat = await self.chat_gateway.get_chat(chat_id, user_id)
        if chat:
            await self.chat_gateway.delete_chat(chat_id, user_id)
            return True
        return False

    async def add_member(
        self, chat_id: int, user_id: int, current_user_id: int
    ) -> schemas.Chat | None:
        # Verify that the current user is authorized to add members
        chat = await self.get_chat(chat_id, current_user_id)
        if not chat:
            return None

        # Add the new member via the gateway
        updated_chat = await self.chat_gateway.add_member(
            chat_id, user_id, current_user_id
        )
        if not updated_chat:
            return None

        return schemas.Chat.model_validate(updated_chat)

    async def remove_member(
        self, chat_id: int, user_id: int, current_user_id: int
    ) -> schemas.Chat | None:
        # Verify that the current user is authorized to remove members
        chat = await self.get_chat(chat_id, current_user_id)
        if not chat:
            return None

        success = await self.chat_gateway.remove_member(
            chat_id, user_id, current_user_id
        )
        return chat if success else None

    async def start_chat(
        self, current_user_id: int, other_user_id: int
    ) -> schemas.Chat | None:
        new_chat = await self.chat_gateway.start_chat(current_user_id, other_user_id)
        return schemas.Chat.model_validate(new_chat) if new_chat else None

    async def get_unread_counts_for_chat_members(
        self, chat_id: int, current_user_id: int
    ) -> dict[int, int]:
        return await self.chat_gateway.get_unread_counts_for_chat_members(
            chat_id, current_user_id
        )

    async def get_unread_messages_count(self, chat_id: int, user_id: int) -> int | None:
        chat = await self.chat_gateway.get_chat(chat_id, user_id)
        if not chat:
            return None
        return await self.chat_gateway.get_unread_messages_count(chat_id, user_id)
