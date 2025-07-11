# app/infrastructure/event_handlers.py
import json
from typing import Any

from app.domain.events import (
    MessageCreated,
    MessageDeleted,
    MessageEvent,
    MessageStatusUpdated,
    MessageUpdated,
    UnreadCountUpdated,
)


class EventHandlers:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def publish_message_event(
        self, event: MessageEvent, additional_data: dict[str, Any] | None = None
    ):
        channel_name = f"chat:{event.chat_id}"

        message_data = event.model_dump()
        message_data["id"] = message_data.pop("message_id")

        if additional_data:
            message_data.update(additional_data)

        message_json = json.dumps(message_data, default=str)
        await self.redis_client.publish(channel_name, message_json)

    async def publish_message_created(self, event: MessageCreated):
        await self.publish_message_event(event)

    async def publish_message_updated(self, event: MessageUpdated):
        await self.publish_message_event(event, {"updated_at": event.updated_at})

    async def publish_message_deleted(self, event: MessageDeleted):
        await self.publish_message_event(
            event,
            {
                "content": "<This message has been deleted>",
                "updated_at": event.updated_at,
            },
        )

    async def publish_message_status_updated(self, event: MessageStatusUpdated):
        channel_name = f"chat:{event.chat_id}:status"
        status_data = json.dumps(
            {
                "message_id": event.message_id,
                "user_id": event.user_id,
                "is_read": event.is_read,
                "read_at": event.read_at,
            },
            default=str,
        )
        await self.redis_client.publish(channel_name, status_data)

    async def publish_unread_count_updated(self, event: UnreadCountUpdated):
        channel_name = f"chat:{event.chat_id}:unread_count:{event.user_id}"
        unread_count_data = json.dumps(
            {
                "chat_id": event.chat_id,
                "unread_count": event.unread_count,
                "user_id": event.user_id,
            }
        )
        await self.redis_client.publish(channel_name, unread_count_data)
