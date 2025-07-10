# app/infrastructure/uow.py

from typing import Dict, Any, Type


class UoWModel:
    def __init__(self, model: Any, uow: "UnitOfWork"):
        self.__dict__["_model"] = model
        self.__dict__["_uow"] = uow

    def __getattr__(self, key):
        return getattr(self._model, key)

    def __setattr__(self, key, value):
        setattr(self._model, key, value)
        # if it's not a new model, register it as dirty,
        # otherwise, it's already in the new models and doesn't need to be registered
        # as dirty cause it doesnt exist in the database yet
        if id(self._model) not in self._uow.new:
            self._uow.register_dirty(self._model)


class UnitOfWork:
    def __init__(self) -> None:
        self.dirty: Dict[int, Any] = {}
        self.new: Dict[int, Any] = {}
        self.deleted: Dict[int, Any] = {}
        self.mappers: Dict[Type, Any] = {}

    def register_dirty(self, model: Any) -> None:
        if isinstance(model, UoWModel):
            model = model._model
        model_id = id(model)
        if model_id not in self.new:
            self.dirty[model_id] = model

    def register_deleted(self, model: Any) -> None:
        if isinstance(model, UoWModel):
            model = model._model
        model_id = id(model)
        if model_id in self.new:
            # If the model is new, just delete it and go back
            self.new.pop(model_id)
            return
        elif model_id in self.dirty:
            # If model was supposed to be updated, remove it from dirty
            self.dirty.pop(model_id)

        # Always add to deleted, regardless of previous state
        self.deleted[model_id] = model

    def register_new(self, model: Any) -> UoWModel:
        if isinstance(model, UoWModel):
            model = model._model
        model_id = id(model)
        self.new[model_id] = model
        return UoWModel(model, self)

    async def commit(self) -> None:
        for model in self.new.values():
            await self.mappers[type(model)].insert(model)
        for model in self.dirty.values():
            await self.mappers[type(model)].update(model)
        for model in self.deleted.values():
            await self.mappers[type(model)].delete(model)
        
        # Clear all pending operations after successful commit
        self.new.clear()
        self.dirty.clear()
        self.deleted.clear()
