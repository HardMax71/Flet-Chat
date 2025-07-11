from unittest.mock import Mock, AsyncMock

import pytest
from app.gateways.user_gateway import UserGateway
from app.infrastructure import models, schemas
from app.infrastructure.security import SecurityService
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
def mock_security_service():
    service = Mock(spec=SecurityService)
    service.get_password_hash = Mock(return_value="hashed_password")
    service.verify_password = Mock(return_value=True)
    return service


@pytest.fixture
def user_gateway(mock_session, mock_uow):
    return UserGateway(mock_session, mock_uow)


@pytest.fixture
def mock_user():
    user = Mock(spec=models.User)
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.hashed_password = "hashed_password"
    user.is_active = True
    return user


@pytest.fixture
def mock_uow_user(mock_user, mock_uow):
    return UoWModel(mock_user, mock_uow)


class TestUserGateway:
    @pytest.mark.asyncio
    async def test_get_user_found(self, user_gateway, mock_session, mock_user, mock_uow):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_user(1)

        assert result is not None
        assert isinstance(result, UoWModel)
        assert result._model == mock_user
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_gateway, mock_session):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_user(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_found(self, user_gateway, mock_session, mock_user):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_by_email("test@example.com")

        assert result is not None
        assert isinstance(result, UoWModel)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_case_insensitive(self, user_gateway, mock_session, mock_user):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_by_email("TEST@EXAMPLE.COM")

        assert result is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_username_found(self, user_gateway, mock_session, mock_user):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_by_username("testuser")

        assert result is not None
        assert isinstance(result, UoWModel)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_username_case_insensitive(self, user_gateway, mock_session, mock_user):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_by_username("TESTUSER")

        assert result is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_no_filter(self, user_gateway, mock_session, mock_user):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_all()

        assert len(result) == 1
        assert isinstance(result[0], UoWModel)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_username_filter(self, user_gateway, mock_session, mock_user):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_all(username="test")

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, user_gateway, mock_session, mock_user):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.execute.return_value = mock_result

        result = await user_gateway.get_all(skip=10, limit=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_gateway, mock_security_service, mock_uow):
        user_gateway.get_by_email = AsyncMock(return_value=None)
        user_gateway.get_by_username = AsyncMock(return_value=None)

        mock_uow_user = Mock()
        mock_uow.register_new.return_value = mock_uow_user

        user_create = schemas.UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123"
        )

        result = await user_gateway.create_user(user_create, mock_security_service)

        assert result == mock_uow_user
        mock_security_service.get_password_hash.assert_called_once_with("password123")
        mock_uow.register_new.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_gateway, mock_security_service, mock_uow_user):
        user_gateway.get_by_email = AsyncMock(return_value=mock_uow_user)
        user_gateway.get_by_username = AsyncMock(return_value=None)

        user_create = schemas.UserCreate(
            username="newuser",
            email="existing@example.com",
            password="password123"
        )

        result = await user_gateway.create_user(user_create, mock_security_service)

        assert result is None
        mock_security_service.get_password_hash.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_username_exists(self, user_gateway, mock_security_service, mock_uow_user):
        user_gateway.get_by_email = AsyncMock(return_value=None)
        user_gateway.get_by_username = AsyncMock(return_value=mock_uow_user)

        user_create = schemas.UserCreate(
            username="existinguser",
            email="new@example.com",
            password="password123"
        )

        result = await user_gateway.create_user(user_create, mock_security_service)

        assert result is None
        mock_security_service.get_password_hash.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_with_password(self, user_gateway, mock_uow_user, mock_security_service, mock_uow):
        user_update = schemas.UserUpdate(password="newpassword")

        result = await user_gateway.update_user(mock_uow_user, user_update, mock_security_service)

        assert result == mock_uow_user
        mock_security_service.get_password_hash.assert_called_once_with("newpassword")
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_without_password(self, user_gateway, mock_uow_user, mock_security_service, mock_uow):
        user_update = schemas.UserUpdate(username="newusername")

        result = await user_gateway.update_user(mock_uow_user, user_update, mock_security_service)

        assert result == mock_uow_user
        mock_security_service.get_password_hash.assert_not_called()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_users(self, user_gateway, mock_session, mock_user):
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.execute.return_value = mock_result

        result = await user_gateway.search_users("test", 2)

        assert len(result) == 1
        assert isinstance(result[0], UoWModel)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_password_success(self, user_gateway, mock_uow_user, mock_security_service):
        mock_security_service.verify_password.return_value = True

        result = await user_gateway.verify_password(mock_uow_user, "correct_password", mock_security_service)

        assert result is True
        mock_security_service.verify_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_password_failure(self, user_gateway, mock_uow_user, mock_security_service):
        mock_security_service.verify_password.return_value = False

        result = await user_gateway.verify_password(mock_uow_user, "wrong_password", mock_security_service)

        assert result is False
        mock_security_service.verify_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_password(self, user_gateway, mock_uow_user, mock_security_service, mock_uow):
        await user_gateway.update_password(mock_uow_user, "newpassword", mock_security_service)

        mock_security_service.get_password_hash.assert_called_once_with("newpassword")
        mock_uow.register_dirty.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_found(self, user_gateway, mock_session, mock_user, mock_uow):
        # Mock the user lookup result
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        
        # Mock the token lookup result
        mock_token_result = Mock()
        mock_token_result.scalars.return_value.all.return_value = []  # No tokens
        
        mock_session.execute.side_effect = [mock_user_result, mock_token_result]

        result = await user_gateway.delete_user(1)

        assert result is not None
        assert isinstance(result, UoWModel)
        assert result._model == mock_user
        mock_uow.register_deleted.assert_called_once_with(mock_user)
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_gateway, mock_session, mock_uow):
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await user_gateway.delete_user(999)

        assert result is None
        mock_uow.register_deleted.assert_not_called()
        mock_uow.commit.assert_not_called()
