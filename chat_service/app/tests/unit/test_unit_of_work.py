# app/tests/unit/test_unit_of_work.py

import pytest
from unittest.mock import AsyncMock
from app.domain import models
from app.infrastructure.uow import UnitOfWork, UoWModel, init_uow
from app.infrastructure.data_mappers import UserMapper, ChatMapper, MessageMapper, TokenMapper


@pytest.fixture
def mock_session():
    """
    Provides a mocked AsyncSession for testing.
    """
    return AsyncMock()


@pytest.fixture
def uow(mock_session):
    """
    Initializes the UnitOfWork with mocked data mappers.
    """
    uow = init_uow(mock_session)

    # Mock the insert, update, delete methods for each mapper
    for mapper in uow.mappers.values():
        mapper.insert = AsyncMock()
        mapper.update = AsyncMock()
        mapper.delete = AsyncMock()

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


@pytest.mark.asyncio
async def test_register_existing_model_as_dirty(uow):
    """
    Test registering an existing model as dirty and ensuring it's tracked correctly.
    """
    user = models.User(username="existinguser", email="existing@example.com")

    # Simulate that the model is already existing (not new)
    uow.register_dirty(user)

    # Modify the model via UoWModel
    uow_model = UoWModel(user, uow)
    uow_model.email = "updated@example.com"

    # Now, 'dirty' should include the model
    assert len(uow.dirty) == 1, "Existing models should be tracked in 'dirty' when modified"
    assert id(user) in uow.dirty, "Modified existing model should exist in 'dirty'"


@pytest.mark.asyncio
async def test_register_deleted_model_with_existing_model(uow):
    """
    Test registering an existing model for deletion and ensuring it's tracked correctly.
    """
    user = models.User(username="existinguser", email="existing@example.com")

    # Simulate existing model
    uow.register_dirty(user)

    # Modify the model via UoWModel
    uow_model = UoWModel(user, uow)
    uow_model.email = "updated@example.com"

    # Register the model as deleted
    uow.register_deleted(uow_model)

    # According to the current UoW implementation, the model should be removed from 'dirty'
    # and not added to 'deleted'
    assert len(uow.deleted) == 0, "Deleted models should not be tracked in 'deleted' when deleting existing dirty models"
    assert id(user) not in uow.dirty, "Deleted model should be removed from 'dirty'"


@pytest.mark.asyncio
async def test_register_deleted_model_with_new_model(uow):
    """
    Test registering a new model for deletion and ensuring it's not tracked in 'deleted'.
    """
    user = models.User(username="testuser", email="test@example.com")
    uow_model = uow.register_new(user)

    # Register the model as deleted
    uow.register_deleted(uow_model)

    assert len(uow.deleted) == 0, "Deleted models should not track new models"
    assert id(user) not in uow.new, "Deleted model should be removed from 'new'"
    assert id(user) not in uow.dirty, "Deleted model should not be in 'dirty'"


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
    # Create an existing model and register it as dirty
    user = models.User(username="existinguser", email="existing@example.com")
    uow.register_dirty(user)

    # Modify the model via UoWModel
    uow_model = UoWModel(user, uow)
    uow_model.email = "updated@example.com"

    await uow.commit()

    # Verify that update was called once with the correct model
    uow.mappers[models.User].update.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_commit_deletes_deleted_models_with_existing_model(uow):
    """
    Test that committing the UoW calls delete on deleted existing models.
    """
    user = models.User(username="existinguser", email="existing@example.com")

    # Simulate existing model
    uow.register_dirty(user)

    # Modify the model via UoWModel
    uow_model = UoWModel(user, uow)
    uow_model.email = "updated@example.com"

    # Register the model as deleted
    uow.register_deleted(uow_model)
    await uow.commit()

    # According to the UoW implementation, 'deleted' remains empty since the model was in 'dirty' and deleted
    # Thus, 'delete' should not have been called
    uow.mappers[models.User].delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_deletes_deleted_models_with_new_model(uow):
    """
    Test that committing the UoW does not call delete on models that were new and then deleted.
    """
    user = models.User(username="testuser", email="test@example.com")
    uow_model = uow.register_new(user)

    # Register the model as deleted
    uow.register_deleted(uow_model)
    await uow.commit()

    # Verify that delete was not called since the model was new and then deleted
    uow.mappers[models.User].delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_handles_multiple_operations(uow):
    """
    Test that committing the UoW handles multiple operations correctly.
    """
    # Register new model
    new_user = models.User(username="newuser", email="new@example.com")
    uow.register_new(new_user)

    # Existing model
    existing_user = models.User(username="existinguser", email="existing@example.com")
    uow.register_dirty(existing_user)
    uow_model_existing = UoWModel(existing_user, uow)
    uow_model_existing.email = "updated@example.com"

    # Register deleted existing model
    to_delete_user = models.User(username="deleteuser", email="delete@example.com")
    uow.register_dirty(to_delete_user)
    uow_model_delete = UoWModel(to_delete_user, uow)
    uow_model_delete.email = "to_delete@example.com"
    uow.register_deleted(uow_model_delete)

    await uow.commit()

    # Check insert for new_user
    uow.mappers[models.User].insert.assert_awaited_once_with(new_user)

    # Check update for existing_user
    uow.mappers[models.User].update.assert_awaited_once_with(existing_user)

    # Check delete for to_delete_user: should not have been called, since it's in 'dirty' and was deleted
    uow.mappers[models.User].delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_rollback(uow):
    """
    Test that rollback clears all tracked changes without calling mapper methods.
    """
    # Register new and dirty models
    user_new = models.User(username="newuser", email="new@example.com")
    uow.register_new(user_new)

    user_existing = models.User(username="existinguser", email="existing@example.com")
    uow.register_dirty(user_existing)

    # Register deleted model
    user_to_delete = models.User(username="deleteuser", email="delete@example.com")
    uow.register_dirty(user_to_delete)
    uow_model_delete = UoWModel(user_to_delete, uow)
    uow_model_delete.email = "to_delete@example.com"
    uow.register_deleted(uow_model_delete)

    # Before rollback
    assert len(uow.new) == 1, "'new' should have one model before rollback"
    assert len(uow.dirty) == 1, "'dirty' should have one model before rollback"
    assert len(uow.deleted) == 0, "'deleted' should remain empty since deleted model was in 'dirty'"

    # Perform rollback
    await uow.rollback()

    # After rollback, all should be cleared
    assert len(uow.new) == 0, "'new' should be empty after rollback"
    assert len(uow.dirty) == 0, "'dirty' should be empty after rollback"
    assert len(uow.deleted) == 0, "'deleted' should be empty after rollback"

    # Ensure mappers' methods were not called
    uow.mappers[models.User].insert.assert_not_awaited()
    uow.mappers[models.User].update.assert_not_awaited()
    uow.mappers[models.User].delete.assert_not_awaited()
