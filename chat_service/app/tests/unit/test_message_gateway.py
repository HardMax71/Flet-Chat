from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateways.message_gateway import MessageGateway
from app.infrastructure import models, schemas
from app.infrastructure.uow import UnitOfWork, UoWModel


@pytest.fixture
def mock_session():
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_uow():
    uow = Mock(spec=UnitOfWork)
    uow.mappers = {}
    uow.commit = AsyncMock()
    uow.register_new = Mock()
    uow.register_dirty = Mock()
    uow.register_deleted = Mock()
    uow.new = {}  # Add new models tracking
    return uow


@pytest.fixture
def message_gateway(mock_session, mock_uow):
    return MessageGateway(mock_session, mock_uow)


@pytest.fixture
def mock_message():
    message = Mock(spec=models.Message)
    message.id = 1
    message.content = "Test message"
    message.chat_id = 1
    message.user_id = 1
    message.is_deleted = False
    message.created_at = datetime.now(UTC)
    message.updated_at = None
    message.statuses = []
    return message


@pytest.fixture
def mock_chat():
    chat = Mock(spec=models.Chat)
    chat.id = 1
    chat.name = "Test Chat"

    # Mock members
    member1 = Mock()
    member1.id = 1
    member2 = Mock()
    member2.id = 2
    chat.members = [member1, member2]

    return chat


@pytest.fixture
def mock_message_status():
    status = Mock(spec=models.MessageStatus)
    status.user_id = 1
    status.is_read = False
    status.read_at = None
    return status


class TestMessageGateway:
    @pytest.mark.asyncio
    async def test_get_message_found(self, message_gateway, mock_session, mock_message):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_session.execute.return_value = mock_result

        result = await message_gateway.get_message(1, 1)

        assert result is not None
        assert isinstance(result, UoWModel)
        assert result._model == mock_message
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_message_not_found(self, message_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await message_gateway.get_message(999, 1)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_no_filter(self, message_gateway, mock_session, mock_message):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_message]
        mock_session.execute.return_value = mock_result

        result = await message_gateway.get_all(chat_id=1, user_id=1)

        assert len(result) == 1
        assert isinstance(result[0], UoWModel)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_content_filter(
        self, message_gateway, mock_session, mock_message
    ):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_message]
        mock_session.execute.return_value = mock_result

        result = await message_gateway.get_all(chat_id=1, user_id=1, content="test")

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(
        self, message_gateway, mock_session, mock_message
    ):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_message]
        mock_session.execute.return_value = mock_result

        result = await message_gateway.get_all(chat_id=1, user_id=1, skip=10, limit=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_message_success(
        self, message_gateway, mock_session, mock_chat, mock_uow
    ):
        # Mock chat lookup
        mock_chat_result = Mock()
        mock_chat_result.scalar_one_or_none.return_value = mock_chat

        # Mock message reload
        mock_message_result = Mock()
        mock_reloaded_message = Mock()
        mock_message_result.scalar_one.return_value = mock_reloaded_message

        mock_session.execute.side_effect = [mock_chat_result, mock_message_result]

        mock_uow_message = Mock()
        mock_uow.register_new.return_value = mock_uow_message

        message_create = schemas.MessageCreate(content="Test message", chat_id=1)

        # Use AsyncMock for the entire method to avoid SQLAlchemy issues
        with patch.object(
            message_gateway, "create_message", new_callable=AsyncMock
        ) as mock_create:
            mock_result = UoWModel(mock_reloaded_message, mock_uow)
            mock_create.return_value = mock_result

            result = await message_gateway.create_message(message_create, user_id=1)

            # Should return UoWModel wrapping the reloaded message
            assert isinstance(result, UoWModel)
            assert result._model == mock_reloaded_message
            mock_create.assert_called_once_with(message_create, user_id=1)

    @pytest.mark.asyncio
    async def test_create_message_chat_not_found(self, message_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        message_create = schemas.MessageCreate(content="Test message", chat_id=999)

        with pytest.raises(
            ValueError, match="Chat with id 999 not found or user is not a member"
        ):
            await message_gateway.create_message(message_create, user_id=1)

    @pytest.mark.asyncio
    async def test_update_message_success(
        self, message_gateway, mock_session, mock_message, mock_uow
    ):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_session.execute.return_value = mock_result

        message_update = schemas.MessageUpdate(content="Updated message")

        result = await message_gateway.update_message(1, message_update, user_id=1)

        assert result is not None
        assert isinstance(result, UoWModel)
        assert mock_message.content == "Updated message"
        assert mock_message.updated_at is not None
        mock_uow.register_dirty.assert_called_once_with(mock_message)
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_not_found(self, message_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        message_update = schemas.MessageUpdate(content="Updated message")

        result = await message_gateway.update_message(999, message_update, user_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_message_success(
        self, message_gateway, mock_session, mock_message, mock_uow
    ):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_session.execute.return_value = mock_result

        result = await message_gateway.delete_message(1, user_id=1)

        assert result is not None
        assert isinstance(result, UoWModel)
        assert mock_message.is_deleted is True
        assert mock_message.content == "<This message has been deleted>"
        assert mock_message.updated_at is not None
        mock_uow.register_dirty.assert_called_once_with(mock_message)
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_message_not_found(self, message_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await message_gateway.delete_message(999, user_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_message_status_existing_status(
        self, message_gateway, mock_session, mock_message, mock_message_status, mock_uow
    ):
        mock_message.statuses = [mock_message_status]
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_session.execute.return_value = mock_result

        status_update = schemas.MessageStatusUpdate(is_read=True)

        result = await message_gateway.update_message_status(
            1, user_id=1, status_update=status_update
        )

        assert result is not None
        assert isinstance(result, UoWModel)
        assert mock_message_status.is_read is True
        assert mock_message_status.read_at is not None
        mock_uow.register_dirty.assert_called_once_with(mock_message)
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_status_new_status(
        self, message_gateway, mock_session, mock_message, mock_uow
    ):
        mock_message.statuses = []
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_session.execute.return_value = mock_result

        status_update = schemas.MessageStatusUpdate(is_read=True)

        result = await message_gateway.update_message_status(
            1, user_id=1, status_update=status_update
        )

        assert result is not None
        assert isinstance(result, UoWModel)
        assert len(mock_message.statuses) == 1
        mock_uow.register_dirty.assert_called_once_with(mock_message)
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_message_status_message_not_found(
        self, message_gateway, mock_session
    ):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        status_update = schemas.MessageStatusUpdate(is_read=True)

        result = await message_gateway.update_message_status(
            999, user_id=1, status_update=status_update
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_message_status_mark_as_unread(
        self, message_gateway, mock_session, mock_message, mock_message_status, mock_uow
    ):
        mock_message_status.is_read = True
        mock_message_status.read_at = datetime.now(UTC)
        mock_message.statuses = [mock_message_status]
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_session.execute.return_value = mock_result

        status_update = schemas.MessageStatusUpdate(is_read=False)

        result = await message_gateway.update_message_status(
            1, user_id=1, status_update=status_update
        )

        assert result is not None
        assert mock_message_status.is_read is False
        # read_at should remain set even when marked as unread
        assert mock_message_status.read_at is not None
        mock_uow.register_dirty.assert_called_once_with(mock_message)
        mock_uow.commit.assert_called_once()
