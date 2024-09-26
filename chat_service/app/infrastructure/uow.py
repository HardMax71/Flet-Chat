# app/infrastructure/uow.py

from typing import Dict, Any, Type


class UoWModel:
    def __init__(self, model: Any, uow: 'UnitOfWork'):
        self.__dict__['_model'] = model
        self.__dict__['_uow'] = uow

    def __getattr__(self, key):
        return getattr(self._model, key)

    def __setattr__(self, key, value):
        setattr(self._model, key, value)
        self._uow.register_dirty(self._model)


class UnitOfWork:
    def __init__(self):
        self.dirty: Dict[int, Any] = {}
        self.new: Dict[int, Any] = {}
        self.deleted: Dict[int, Any] = {}
        self.mappers: Dict[Type, Any] = {}

    def register_dirty(self, model: Any):
        if isinstance(model, UoWModel):
            model = model._model
        model_id = id(model)
        if model_id not in self.new:
            self.dirty[model_id] = model

    def register_deleted(self, model: Any):
        if isinstance(model, UoWModel):
            model = model._model
        model_id = id(model)
        if model_id in self.new:
            # If the model is new, just delete it
            self.new.pop(model_id)
        elif model_id in self.dirty:
            # If model was supposed to be updated, remove it from dirty
            self.dirty.pop(model_id)

        # Always add to deleted, regardless of previous state
        self.deleted[model_id] = model

    def register_new(self, model: Any):
        if isinstance(model, UoWModel):
            model = model._model
        model_id = id(model)
        self.new[model_id] = model
        return UoWModel(model, self)

    async def commit(self):
        for model in self.new.values():
            await self.mappers[type(model)].insert(model)
        for model in self.dirty.values():
            await self.mappers[type(model)].update(model)
        for model in self.deleted.values():
            await self.mappers[type(model)].delete(model)
        self.clear()

    async def rollback(self):
        self.clear()

    def clear(self):
        self.dirty.clear()
        self.new.clear()
        self.deleted.clear()
