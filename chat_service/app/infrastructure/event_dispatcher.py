# app/infrastructure/event_dispatcher.py
from typing import Callable, Dict, List
from app.domain.events import Event

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