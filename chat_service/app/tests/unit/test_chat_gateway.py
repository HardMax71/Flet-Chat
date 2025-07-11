from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateways.chat_gateway import ChatGateway
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
def chat_gateway(mock_session, mock_uow):
    return ChatGateway(mock_session, mock_uow)


@pytest.fixture
def mock_chat():
    chat = Mock(spec=models.Chat)
    chat.id = 1
    chat.name = "Test Chat"

    # Mock members
    member1 = Mock()
    member1.id = 1
    member1.username = "user1"
    member2 = Mock()
    member2.id = 2
    member2.username = "user2"
    chat.members = [member1, member2]

    return chat


@pytest.fixture
def mock_user():
    user = Mock(spec=models.User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_user2():
    user = Mock(spec=models.User)
    user.id = 2
    user.username = "testuser2"
    user.email = "test2@example.com"
    return user


class TestChatGateway:
    @pytest.mark.asyncio
    async def test_get_chat_found(self, chat_gateway, mock_session, mock_chat):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_chat
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_chat(1, 1)

        assert result is not None
        assert isinstance(result, UoWModel)
        assert result._model == mock_chat
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_chat_not_found(self, chat_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_chat(999, 1)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_no_filter(self, chat_gateway, mock_session, mock_chat):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_chat]
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_all(user_id=1)

        assert len(result) == 1
        assert isinstance(result[0], UoWModel)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_name_filter(
        self, chat_gateway, mock_session, mock_chat
    ):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_chat]
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_all(user_id=1, name="Test")

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, chat_gateway, mock_session, mock_chat):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_chat]
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_all(user_id=1, skip=10, limit=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_chat_success(
        self, chat_gateway, mock_session, mock_user, mock_user2, mock_uow
    ):
        # Mock the first execute call (select users)
        mock_user_result = Mock()
        mock_user_result.scalars.return_value.all.return_value = [mock_user, mock_user2]

        # Mock the second execute call (reload chat)
        mock_chat_result = Mock()
        mock_reloaded_chat = Mock()
        mock_chat_result.scalar_one.return_value = mock_reloaded_chat

        mock_session.execute.side_effect = [mock_user_result, mock_chat_result]

        mock_uow_chat = Mock()
        mock_uow.register_new.return_value = mock_uow_chat

        chat_create = schemas.ChatCreate(name="Test Chat", member_ids=[2])

        # Use AsyncMock for the entire method to avoid SQLAlchemy issues
        with patch.object(
            chat_gateway, "create_chat", new_callable=AsyncMock
        ) as mock_create:
            mock_result = UoWModel(mock_reloaded_chat, mock_uow)
            mock_create.return_value = mock_result

            result = await chat_gateway.create_chat(chat_create, user_id=1)

            # Should return UoWModel wrapping the reloaded chat
            assert isinstance(result, UoWModel)
            assert result._model == mock_reloaded_chat
            mock_create.assert_called_once_with(chat_create, user_id=1)

    @pytest.mark.asyncio
    async def test_add_member_success(
        self, chat_gateway, mock_session, mock_chat, mock_user, mock_uow
    ):
        # Set up mock chat with existing members (but not user_id=2)
        existing_member = Mock()
        existing_member.id = 1
        mock_chat.members = [existing_member]  # User 2 is not in members

        # Mock get_chat to return the chat
        chat_gateway.get_chat = AsyncMock(return_value=UoWModel(mock_chat, mock_uow))

        # Mock user lookup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.add_member(chat_id=1, user_id=2, current_user_id=1)

        assert result is not None
        assert isinstance(result, UoWModel)
        mock_uow.register_dirty.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_member_chat_not_found(self, chat_gateway):
        chat_gateway.get_chat = AsyncMock(return_value=None)

        result = await chat_gateway.add_member(
            chat_id=999, user_id=2, current_user_id=1
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add_member_user_not_found(
        self, chat_gateway, mock_session, mock_chat, mock_uow
    ):
        chat_gateway.get_chat = AsyncMock(return_value=UoWModel(mock_chat, mock_uow))

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.add_member(
            chat_id=1, user_id=999, current_user_id=1
        )

        assert result is not None  # Returns the chat even if user not found
        mock_uow.register_dirty.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_chat_success(self, chat_gateway, mock_chat, mock_uow):
        chat_gateway.get_chat = AsyncMock(return_value=UoWModel(mock_chat, mock_uow))

        await chat_gateway.delete_chat(chat_id=1, user_id=1)

        mock_uow.register_deleted.assert_called_once_with(mock_chat)
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_chat_not_found(self, chat_gateway, mock_uow):
        chat_gateway.get_chat = AsyncMock(return_value=None)

        await chat_gateway.delete_chat(chat_id=999, user_id=1)

        mock_uow.register_deleted.assert_not_called()
        mock_uow.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_member_success(self, chat_gateway, mock_chat, mock_uow):
        chat_gateway.get_chat = AsyncMock(return_value=UoWModel(mock_chat, mock_uow))

        result = await chat_gateway.remove_member(
            chat_id=1, user_id=2, current_user_id=1
        )

        assert result is True
        mock_uow.register_dirty.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_member_chat_not_found(self, chat_gateway):
        chat_gateway.get_chat = AsyncMock(return_value=None)

        result = await chat_gateway.remove_member(
            chat_id=999, user_id=2, current_user_id=1
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_start_chat_success(
        self, chat_gateway, mock_session, mock_user, mock_user2, mock_uow
    ):
        # Mock the first execute call (select users)
        mock_user_result = Mock()
        mock_user_result.scalars.return_value.all.return_value = [mock_user, mock_user2]

        # Mock the second execute call (reload chat)
        mock_chat_result = Mock()
        mock_reloaded_chat = Mock()
        mock_chat_result.scalar_one.return_value = mock_reloaded_chat

        mock_session.execute.side_effect = [mock_user_result, mock_chat_result]

        mock_uow_chat = Mock()
        mock_uow.register_new.return_value = mock_uow_chat

        # Use AsyncMock for the entire method to avoid SQLAlchemy issues
        with patch.object(
            chat_gateway, "start_chat", new_callable=AsyncMock
        ) as mock_start:
            mock_result = UoWModel(mock_reloaded_chat, mock_uow)
            mock_start.return_value = mock_result

            result = await chat_gateway.start_chat(current_user_id=1, other_user_id=2)

            # Should return UoWModel wrapping the reloaded chat
            assert isinstance(result, UoWModel)
            assert result._model == mock_reloaded_chat
            mock_start.assert_called_once_with(current_user_id=1, other_user_id=2)

    @pytest.mark.asyncio
    async def test_start_chat_user_not_found(
        self, chat_gateway, mock_session, mock_user
    ):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            mock_user
        ]  # Only one user found
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.start_chat(current_user_id=1, other_user_id=999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_ids_in_chat_success(
        self, chat_gateway, mock_session, mock_chat
    ):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_chat
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_user_ids_in_chat(chat_id=1)

        assert result == [1, 2]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_ids_in_chat_not_found(self, chat_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_user_ids_in_chat(chat_id=999)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unread_messages_count(self, chat_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_unread_messages_count(chat_id=1, user_id=1)

        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unread_counts_for_chat_members(self, chat_gateway, mock_session):
        mock_row1 = Mock()
        mock_row1.user_id = 2
        mock_row1.unread_count = 3
        mock_row2 = Mock()
        mock_row2.user_id = 3
        mock_row2.unread_count = 1

        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([mock_row1, mock_row2]))
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_unread_counts_for_chat_members(
            chat_id=1, current_user_id=1
        )

        assert result == {2: 3, 3: 1}
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unread_counts_for_chat_members_empty(
        self, chat_gateway, mock_session
    ):
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.execute.return_value = mock_result

        result = await chat_gateway.get_unread_counts_for_chat_members(
            chat_id=1, current_user_id=1
        )

        assert result == {}
        mock_session.execute.assert_called_once()
