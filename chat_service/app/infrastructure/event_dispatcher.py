# app/infrastructure/event_dispatcher.py
from collections import defaultdict
from typing import Callable, Dict, List

from app.domain.events import Event


class EventDispatcher:
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = defaultdict(list)

    def register(self, event_type: str, handler: Callable):
        self.handlers[event_type].append(handler)

    async def dispatch(self, event: Event):
        event_type = event.__class__.__name__
        for handler in self.handlers[event_type]:
            await handler(event)
