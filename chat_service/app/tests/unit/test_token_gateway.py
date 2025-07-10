from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

import pytest
from app.gateways.token_gateway import TokenGateway
from app.infrastructure import models, schemas
from app.infrastructure.uow import UnitOfWork, UoWModel
from sqlalchemy.ext.asyncio import AsyncSession


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
def token_gateway(mock_session, mock_uow):
    return TokenGateway(mock_session, mock_uow)


@pytest.fixture
def mock_token():
    token = Mock(spec=models.Token)
    token.id = 1
    token.access_token = "access_token_123"
    token.refresh_token = "refresh_token_123"
    token.user_id = 1
    token.expires_at = datetime.now(timezone.utc)
    token.token_type = "bearer"
    return token


@pytest.fixture
def mock_uow_token(mock_token, mock_uow):
    return UoWModel(mock_token, mock_uow)


class TestTokenGateway:
    @pytest.mark.asyncio
    async def test_create_token_new(self, token_gateway, mock_uow):
        token_gateway.get_by_user_id = AsyncMock(return_value=None)

        mock_uow_token = Mock()
        mock_uow.register_new.return_value = mock_uow_token

        token_create = schemas.TokenCreate(
            access_token="new_access_token",
            refresh_token="new_refresh_token",
            user_id=1,
            expires_at=datetime.now(timezone.utc),
            token_type="bearer"
        )

        with patch('app.infrastructure.models.Token') as mock_token_class:
            mock_token_instance = Mock()
            mock_token_class.return_value = mock_token_instance

            result = await token_gateway.create_token(token_create)

            assert result == mock_uow_token
            mock_uow.register_new.assert_called_once()
            mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_token_update_existing(self, token_gateway, mock_uow_token, mock_uow):
        token_gateway.get_by_user_id = AsyncMock(return_value=mock_uow_token)

        token_create = schemas.TokenCreate(
            access_token="updated_access_token",
            refresh_token="updated_refresh_token",
            user_id=1,
            expires_at=datetime.now(timezone.utc),
            token_type="bearer"
        )

        result = await token_gateway.create_token(token_create)

        assert result == mock_uow_token
        assert mock_uow_token._model.access_token == "updated_access_token"
        assert mock_uow_token._model.refresh_token == "updated_refresh_token"
        mock_uow.register_dirty.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_id_found(self, token_gateway, mock_session, mock_token):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_session.execute.return_value = mock_result

        result = await token_gateway.get_by_user_id(1)

        assert result is not None
        assert isinstance(result, UoWModel)
        assert result._model == mock_token
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user_id_not_found(self, token_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await token_gateway.get_by_user_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_access_token_found(self, token_gateway, mock_session, mock_token):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_session.execute.return_value = mock_result

        result = await token_gateway.get_by_access_token("access_token_123")

        assert result is not None
        assert isinstance(result, UoWModel)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_access_token_not_found(self, token_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await token_gateway.get_by_access_token("invalid_token")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_refresh_token_found(self, token_gateway, mock_session, mock_token):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_session.execute.return_value = mock_result

        result = await token_gateway.get_by_refresh_token("refresh_token_123")

        assert result is not None
        assert isinstance(result, UoWModel)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_refresh_token_not_found(self, token_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await token_gateway.get_by_refresh_token("invalid_token")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_refresh_token_success(self, token_gateway, mock_uow_token, mock_uow):
        token_gateway.get_by_refresh_token = AsyncMock(return_value=mock_uow_token)

        result = await token_gateway.invalidate_refresh_token("refresh_token_123")

        assert result is True
        # register_deleted is called when invalidating the token
        mock_uow.register_deleted.assert_called_once_with(mock_uow_token)
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_refresh_token_not_found(self, token_gateway):
        token_gateway.get_by_refresh_token = AsyncMock(return_value=None)

        result = await token_gateway.invalidate_refresh_token("invalid_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_token_by_access_token_success(self, token_gateway, mock_uow_token, mock_uow):
        token_gateway.get_by_access_token = AsyncMock(return_value=mock_uow_token)

        result = await token_gateway.delete_token_by_access_token("access_token_123")

        assert result is True
        mock_uow.register_deleted.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_token_by_access_token_not_found(self, token_gateway):
        token_gateway.get_by_access_token = AsyncMock(return_value=None)

        result = await token_gateway.delete_token_by_access_token("invalid_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_token_by_refresh_token_success(self, token_gateway, mock_uow_token, mock_uow):
        token_gateway.get_by_refresh_token = AsyncMock(return_value=mock_uow_token)

        result = await token_gateway.delete_token_by_refresh_token("refresh_token_123")

        assert result is True
        mock_uow.register_deleted.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_token_by_refresh_token_not_found(self, token_gateway):
        token_gateway.get_by_refresh_token = AsyncMock(return_value=None)

        result = await token_gateway.delete_token_by_refresh_token("invalid_token")

        assert result is False
