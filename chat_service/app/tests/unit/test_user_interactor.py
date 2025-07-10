from unittest.mock import Mock

import pytest
from app.gateways.interfaces import IUserGateway
from app.infrastructure import schemas
from app.infrastructure.security import SecurityService
from app.infrastructure.uow import UoWModel
from app.interactors.user_interactor import UserInteractor


@pytest.fixture
def mock_security_service():
    return Mock(spec=SecurityService)


@pytest.fixture
def mock_user_gateway():
    return Mock(spec=IUserGateway)


@pytest.fixture
def user_interactor(mock_security_service, mock_user_gateway):
    return UserInteractor(mock_security_service, mock_user_gateway)


@pytest.fixture
def mock_user_model():
    user = Mock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.created_at = "2023-01-01T00:00:00Z"
    user.updated_at = "2023-01-01T00:00:00Z"
    return user


@pytest.fixture
def mock_uow_user(mock_user_model):
    return Mock(spec=UoWModel, _model=mock_user_model)


class TestUserInteractor:
    @pytest.mark.asyncio
    async def test_get_user_found(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.get_user.return_value = mock_uow_user

        result = await user_interactor.get_user(1)

        assert result is not None
        assert isinstance(result, schemas.User)
        mock_user_gateway.get_user.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_interactor, mock_user_gateway):
        mock_user_gateway.get_user.return_value = None

        result = await user_interactor.get_user(999)

        assert result is None
        mock_user_gateway.get_user.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_get_user_by_username_found(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.get_by_username.return_value = mock_uow_user

        result = await user_interactor.get_user_by_username("testuser")

        assert result is not None
        assert isinstance(result, schemas.User)
        mock_user_gateway.get_by_username.assert_called_once_with("testuser")

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, user_interactor, mock_user_gateway):
        mock_user_gateway.get_by_username.return_value = None

        result = await user_interactor.get_user_by_username("nonexistent")

        assert result is None
        mock_user_gateway.get_by_username.assert_called_once_with("nonexistent")

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.get_by_email.return_value = mock_uow_user

        result = await user_interactor.get_user_by_email("test@example.com")

        assert result is not None
        assert isinstance(result, schemas.User)
        mock_user_gateway.get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_interactor, mock_user_gateway):
        mock_user_gateway.get_by_email.return_value = None

        result = await user_interactor.get_user_by_email("nonexistent@example.com")

        assert result is None
        mock_user_gateway.get_by_email.assert_called_once_with("nonexistent@example.com")

    @pytest.mark.asyncio
    async def test_get_users(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.get_all.return_value = [mock_uow_user]

        result = await user_interactor.get_users()

        assert len(result) == 1
        assert isinstance(result[0], schemas.User)
        mock_user_gateway.get_all.assert_called_once_with(0, 100, None)

    @pytest.mark.asyncio
    async def test_get_users_with_params(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.get_all.return_value = [mock_uow_user]

        result = await user_interactor.get_users(skip=10, limit=5, username="test")

        assert len(result) == 1
        mock_user_gateway.get_all.assert_called_once_with(10, 5, "test")

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_interactor, mock_user_gateway, mock_user_model):
        mock_user_gateway.create_user.return_value = mock_user_model

        user_create = schemas.UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123"
        )

        result = await user_interactor.create_user(user_create)

        assert result is not None
        assert isinstance(result, schemas.User)
        mock_user_gateway.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_failure(self, user_interactor, mock_user_gateway):
        mock_user_gateway.create_user.return_value = None

        user_create = schemas.UserCreate(
            username="existinguser",
            email="existing@example.com",
            password="password123"
        )

        result = await user_interactor.create_user(user_create)

        assert result is None
        mock_user_gateway.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_success(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.get_user.return_value = mock_uow_user
        mock_user_gateway.update_user.return_value = mock_uow_user

        user_update = schemas.UserUpdate(username="updateduser")

        result = await user_interactor.update_user(1, user_update)

        assert result is not None
        assert isinstance(result, schemas.User)
        mock_user_gateway.get_user.assert_called_once_with(1)
        mock_user_gateway.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_interactor, mock_user_gateway):
        mock_user_gateway.get_user.return_value = None

        user_update = schemas.UserUpdate(username="updateduser")

        result = await user_interactor.update_user(999, user_update)

        assert result is None
        mock_user_gateway.get_user.assert_called_once_with(999)
        mock_user_gateway.update_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.delete_user.return_value = mock_uow_user

        result = await user_interactor.delete_user(1)

        assert result is True
        mock_user_gateway.delete_user.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_interactor, mock_user_gateway):
        mock_user_gateway.delete_user.return_value = None

        result = await user_interactor.delete_user(999)

        assert result is False
        mock_user_gateway.delete_user.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_search_users(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.search_users.return_value = [mock_uow_user]

        result = await user_interactor.search_users("test", 1)

        assert len(result) == 1
        assert isinstance(result[0], schemas.User)
        mock_user_gateway.search_users.assert_called_once_with("test", 1)

    @pytest.mark.asyncio
    async def test_verify_user_password_success(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.get_by_username.return_value = mock_uow_user
        mock_user_gateway.verify_password.return_value = True

        result = await user_interactor.verify_user_password("testuser", "password")

        assert result is not None
        assert isinstance(result, schemas.User)
        mock_user_gateway.get_by_username.assert_called_once_with("testuser")
        mock_user_gateway.verify_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_user_password_user_not_found(self, user_interactor, mock_user_gateway):
        mock_user_gateway.get_by_username.return_value = None

        result = await user_interactor.verify_user_password("nonexistent", "password")

        assert result is None
        mock_user_gateway.get_by_username.assert_called_once_with("nonexistent")
        mock_user_gateway.verify_password.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_user_password_wrong_password(self, user_interactor, mock_user_gateway, mock_uow_user):
        mock_user_gateway.get_by_username.return_value = mock_uow_user
        mock_user_gateway.verify_password.return_value = False

        result = await user_interactor.verify_user_password("testuser", "wrongpassword")

        assert result is None
        mock_user_gateway.get_by_username.assert_called_once_with("testuser")
        mock_user_gateway.verify_password.assert_called_once()
