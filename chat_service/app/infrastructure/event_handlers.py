# app/infrastructure/event_handlers.py
import json
from typing import Any, Dict

from app.domain.events import MessageCreated, MessageUpdated, MessageDeleted, MessageStatusUpdated, UnreadCountUpdated, \
    MessageEvent
from app.infrastructure.redis_config import get_redis_client


async def publish_message_event(event: MessageEvent, additional_data: Dict[str, Any] = None):
    redis_client = await get_redis_client()
    channel_name = f"chat:{event.chat_id}"
    message_data = {
        "id": event.message_id,
        "chat_id": event.chat_id,
        "user_id": event.user_id,
        "content": event.content,
        "created_at": event.created_at,
        "user": event.user,
        "is_deleted": event.is_deleted
    }
    if additional_data:
        message_data.update(additional_data)

    message_json = json.dumps(message_data, default=str)
    await redis_client.publish(channel_name, message_json)


async def publish_message_created(event: MessageCreated):
    await publish_message_event(event)


async def publish_message_updated(event: MessageUpdated):
    await publish_message_event(event, {"updated_at": event.updated_at})


async def publish_message_deleted(event: MessageDeleted):
    await publish_message_event(event, {
        "content": "<This message has been deleted>",
        "updated_at": event.updated_at
    })


async def publish_message_status_updated(event: MessageStatusUpdated):
    redis_client = await get_redis_client()
    channel_name = f"chat:{event.chat_id}:status"
    status_data = json.dumps({
        "message_id": event.message_id,
        "user_id": event.user_id,
        "is_read": event.is_read,
        "read_at": event.read_at
    }, default=str)
    await redis_client.publish(channel_name, status_data)


async def publish_unread_count_updated(event: UnreadCountUpdated):
    redis_client = await get_redis_client()
    channel_name = f"chat:{event.chat_id}:unread_count:{event.user_id}"
    unread_count_data = json.dumps({
        "chat_id": event.chat_id,
        "unread_count": event.unread_count,
        "user_id": event.user_id
    })
    await redis_client.publish(channel_name, unread_count_data)
