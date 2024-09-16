# app/infrastructure/event_dispatcher.py
from typing import Callable, Dict, List
from app.domain.events import Event
from app.infrastructure.event_handlers import (
    publish_message_created,
    publish_message_updated,
    publish_message_deleted,
    publish_message_status_updated,
    publish_unread_count_updated
)
class EventDispatcher:
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}

    def register(self, event_type: str, handler: Callable):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def dispatch(self, event: Event):
        event_type = event.__class__.__name__
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                await handler(event)


# Initialize the event dispatcher
event_dispatcher = EventDispatcher()

# Register event handlers
event_dispatcher.register("MessageCreated", publish_message_created)
event_dispatcher.register("MessageUpdated", publish_message_updated)
event_dispatcher.register("MessageDeleted", publish_message_deleted)
event_dispatcher.register("MessageStatusUpdated", publish_message_status_updated)
event_dispatcher.register("UnreadCountUpdated", publish_unread_count_updated)

