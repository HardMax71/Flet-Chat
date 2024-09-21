# app/tests/unit/test_models.py
from app.domain.models import User, Chat, Message, Token, MessageStatus


def test_user_model():
    user = User(username="testuser", email="test@example.com")
    assert user.username == "testuser"
    assert user.email == "test@example.com"


def test_chat_model():
    chat = Chat(name="Test Chat")
    assert chat.name == "Test Chat"


def test_message_model():
    message = Message(content="Hello, world!", chat_id=1, user_id=1)
    assert message.content == "Hello, world!"
    assert message.chat_id == 1
    assert message.user_id == 1


def test_token_model():
    token = Token(access_token="access", refresh_token="refresh", token_type="bearer", user_id=1)
    assert token.access_token == "access"
    assert token.refresh_token == "refresh"
    assert token.token_type == "bearer"
    assert token.user_id == 1


def test_message_status_model():
    status = MessageStatus(message_id=1, user_id=1, is_read=False)
    assert status.message_id == 1
    assert status.user_id == 1
    assert status.is_read == False
