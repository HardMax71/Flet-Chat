# app/tests/unit/test_unit_of_work.py

from unittest.mock import AsyncMock

import pytest
from app.infrastructure import models
from app.infrastructure.data_mappers import UserMapper
from app.infrastructure.uow import UoWModel, UnitOfWork


@pytest.fixture
def mock_session():
    """
    Provides a mocked AsyncSession for testing.
    """
    return AsyncMock()


@pytest.fixture
def uow(mock_session):
    """
    Initializes the UnitOfWork with a mocked UserMapper.
    """
    uow = UnitOfWork()
    user_mapper = UserMapper(mock_session)
    user_mapper.insert = AsyncMock()
    user_mapper.update = AsyncMock()
    user_mapper.delete = AsyncMock()
    uow.mappers[models.User] = user_mapper
    return uow


@pytest.mark.asyncio
async def test_register_new_model(uow):
    """
    Test registering a new model and ensuring it's tracked correctly.
    """
    user = models.User(username="testuser", email="test@example.com")
    uow_model = uow.register_new(user)

    assert len(uow.new) == 1, "New models should be tracked in 'new'"
    assert id(user) in uow.new, "Registered model should exist in 'new'"
    assert isinstance(uow_model, UoWModel), "Returned object should be an instance of UoWModel"


@pytest.mark.asyncio
async def test_modify_new_model_does_not_register_dirty(uow):
    """
    Test that modifying a newly registered model does not add it to 'dirty'.
    """
    user = models.User(username="testuser", email="test@example.com")
    uow_model = uow.register_new(user)

    # Modify the model
    uow_model.username = "updateduser"

    # Since the model is in 'new', it should not appear in 'dirty'
    assert len(uow.dirty) == 0, "'dirty' should remain empty for new models"
    assert id(user) in uow.new, "Modified new model should remain in 'new'"


@pytest.mark.asyncio
async def test_register_existing_model_as_dirty(uow):
    """
    Test registering an existing model as dirty and ensuring it's tracked correctly.
    """
    user = models.User(username="existinguser", email="existing@example.com")

    # Simulate that the model is already existing (not new)
    uow_model = UoWModel(user, uow)
    uow_model.email = "updated@example.com"

    # Now, 'dirty' should include the model
    assert len(uow.dirty) == 1, "Existing models should be tracked in 'dirty' when modified"
    assert id(user) in uow.dirty, "Modified existing model should exist in 'dirty'"


@pytest.mark.asyncio
async def test_register_deleted_model(uow):
    """
    Test registering a model for deletion and ensuring it's tracked correctly.
    """
    user = models.User(username="existinguser", email="existing@example.com")

    # Register the model as deleted
    uow.register_deleted(user)

    assert len(uow.deleted) == 1, "Deleted models should be tracked in 'deleted'"
    assert id(user) in uow.deleted, "Deleted model should exist in 'deleted'"


@pytest.mark.asyncio
async def test_register_deleted_model_removes_from_new_and_dirty(uow):
    new_user = models.User(username="newuser", email="new@example.com")
    uow_model = uow.register_new(new_user)

    dirty_user = models.User(username="dirtyuser", email="dirty@example.com")
    uow.register_dirty(dirty_user)

    uow.register_deleted(uow_model)
    uow.register_deleted(dirty_user)

    assert id(new_user) not in uow.new, "Deleted new model shouldn't remain in 'new'"
    assert id(dirty_user) not in uow.dirty, "Deleted dirty model should be removed from 'dirty'"
    assert id(dirty_user) in uow.deleted, "Deleted dirty model should be added to 'deleted'"
    # New models are not added to deleted when removed
    assert id(new_user) not in uow.deleted, "Deleted new model should not be in 'deleted'"


@pytest.mark.asyncio
async def test_commit_inserts_new_models(uow):
    """
    Test that committing the UoW calls insert on new models.
    """
    user = models.User(username="testuser", email="test@example.com")
    uow.register_new(user)
    await uow.commit()

    # Verify that insert was called once with the correct model
    uow.mappers[models.User].insert.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_commit_updates_dirty_models(uow):
    """
    Test that committing the UoW calls update on dirty models.
    """
    user = models.User(username="existinguser", email="existing@example.com")
    uow.register_dirty(user)
    await uow.commit()

    # Verify that update was called once with the correct model
    uow.mappers[models.User].update.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_commit_deletes_deleted_models(uow):
    """
    Test that committing the UoW calls delete on deleted models.
    """
    user = models.User(username="existinguser", email="existing@example.com")
    uow.register_deleted(user)
    await uow.commit()

    # Verify that delete was called once with the correct model
    uow.mappers[models.User].delete.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_commit_handles_multiple_operations(uow):
    """
    Test that committing the UoW handles multiple operations correctly.
    """
    new_user = models.User(username="newuser", email="new@example.com")
    uow.register_new(new_user)

    existing_user = models.User(username="existinguser", email="existing@example.com")
    uow.register_dirty(existing_user)

    to_delete_user = models.User(username="deleteuser", email="delete@example.com")
    uow.register_deleted(to_delete_user)

    await uow.commit()

    uow.mappers[models.User].insert.assert_awaited_once_with(new_user)
    uow.mappers[models.User].update.assert_awaited_once_with(existing_user)
    uow.mappers[models.User].delete.assert_awaited_once_with(to_delete_user)


@pytest.mark.asyncio
async def test_register_uowmodel(uow):
    user = models.User(username="testuser", email="test@example.com")
    uow_model = uow.register_new(user)

    assert id(user) in uow.new, "Model should be registered in 'new'"
    assert id(user) not in uow.dirty, "New model should not be in 'dirty'"

    # Changing a property of a new model should not mark it as dirty
    uow_model.email = "updated@example.com"
    assert id(user) in uow.new, "Model should still be in 'new' after property change"
    assert id(user) not in uow.dirty, "New model should not be marked as dirty when changed"

    # Simulate commit (clear the new dictionary)
    uow.new.clear()
    uow.dirty.clear()

    # Now changing a property should mark it as dirty
    uow_model.username = "updateduser"
    assert id(user) in uow.dirty, "Model should be marked as dirty after property change post-commit"


@pytest.mark.asyncio
async def test_delete_new_model(uow):
    user = models.User(username="testuser", email="test@example.com")
    uow_model = uow.register_new(user)

    uow.register_deleted(uow_model)

    assert id(user) not in uow.new, "Deleted new model shouldn't remain in 'new'"
    assert id(user) not in uow.deleted, "Deleted new model should not be in 'deleted'"
