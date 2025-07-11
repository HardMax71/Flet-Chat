# app/infrastructure/event_dispatcher.py
from collections import defaultdict
from collections.abc import Callable

from app.domain.events import Event


class EventDispatcher:
    def __init__(self) -> None:
        self.handlers: dict[str, list[Callable]] = defaultdict(list)

    def register(self, event_type: str, handler: Callable) -> None:
        self.handlers[event_type].append(handler)

    async def dispatch(self, event: Event) -> None:
        event_type = event.__class__.__name__
        for handler in self.handlers[event_type]:
            await handler(event)
