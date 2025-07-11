# app/tests/unit/test_event_dispatcher.py
from datetime import UTC, datetime

import pytest

from app.domain.events import MessageCreated, UserInfo
from app.infrastructure.event_dispatcher import EventDispatcher


@pytest.mark.asyncio
async def test_event_dispatcher():
    dispatcher = EventDispatcher()

    events_received = []

    async def test_handler(event):
        events_received.append(event)

    dispatcher.register("MessageCreated", test_handler)

    event = MessageCreated(
        message_id=1,
        chat_id=1,
        user_id=1,
        content="Test",
        created_at=datetime.now(UTC),
        user=UserInfo(id=1, username="testuser"),
        is_deleted=False,
    )
    await dispatcher.dispatch(event)

    assert len(events_received) == 1
    assert isinstance(events_received[0], MessageCreated)
