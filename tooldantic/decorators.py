from __future__ import annotations

import inspect
import json
from functools import update_wrapper
from typing import Callable, Optional, overload

from .builder import ModelBuilder
from .models import ToolBaseModel
from .utils import ModelT


class ToolWrapperBase:
    """
    A ToolWrapperBase class provides a flexible mechanism for wrapping functions with
    automatic input validation, model generation, and metadata handling.

    Key Features:
    1. Wraps a function and generates a Pydantic model based on its input and output types.
    2. Validates and processes inputs before invoking the function, ensuring type safety and consistency.
    3. Outputs are returned as validated Pydantic models, ensuring reliable downstream processing.
    4. Provides a JSON schema for the function's model, useful for generating API documentation or validating input formats.
    5. Can be used as a decorator or a callable object, allowing flexible application to functions.
    6. Supports both synchronous and asynchronous function execution, enabling it to adapt to different use cases.
    7. Integrates seamlessly as a bound method within classes, maintaining the correct `self` reference.
    8. Easily extendable to add custom functionality through subclassing, making it adaptable to specific needs.
    """

    def __init__(
        self,
        func: Optional[Callable] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        base_model: type[ModelT] = ToolBaseModel,
        is_auto_validate_json: bool = True,
    ):
        self.func = func
        self.base_model = base_model
        self.name = name or (func.__name__ if func else None)
        self.description = description or (func.__doc__ if func else None)
        self.is_auto_validate_json = is_auto_validate_json

        if func:
            self._model = self._create_model_from_function(func)
            update_wrapper(self, func)
        else:
            self._model = None

    def _create_model_from_function(self, func: Callable):
        return ModelBuilder(base_model=self.base_model).create_model_from_function(
            func,
            model_name=self.name,
            model_description=self.description,
            is_parse_docstrings=True,
        )

    @overload
    def validate_json_or_data(self, json_data: str): ...

    @overload
    def validate_json_or_data(self, **kwargs): ...

    def validate_json_or_data(self, json_data: Optional[str] = None, **kwargs):
        if self.is_auto_validate_json and json_data:
            return self.Model.model_validate_json(json_data).model_dump()
        return self.Model(**kwargs).model_dump()

    def model_json_schema(self, schema_generator=None, **kwargs):
        if schema_generator:
            kwargs["schema_generator"] = schema_generator
        return self.Model.model_json_schema(**kwargs)

    def __get__(self, instance, owner):
        wrapped_func = self.func.__get__(instance, owner)
        new_instance = self.__class__(
            func=wrapped_func,
            name=self.name,
            description=self.description,
            base_model=self.base_model,
            is_auto_validate_json=self.is_auto_validate_json,
        )
        update_wrapper(new_instance, wrapped_func)
        return new_instance

    @property
    def Model(self) -> type[ModelT]:
        if self._model is None and self.func is not None:
            self._model = self._create_model_from_function(self.func)
        return self._model


class ToolWrapper(ToolWrapperBase):
    def __call__(self, *args, **kwargs):
        if self.func is None:
            if not args or not callable(args[0]):
                raise ValueError("Function not provided.")

            self.func = args[0]
            self._model = self._create_model_from_function(self.func)
            self.name = self.name or self.func.__name__
            self.description = self.description or self.func.__doc__

            return self

        return self.func(**self.validate_json_or_data(*args, **kwargs))


class AsyncToolWrapper(ToolWrapperBase):

    def __call__(self, *args, **kwargs):
        if self.func is None:
            if not args or not callable(args[0]):
                raise ValueError("Function not provided.")

            self.func = args[0]
            self._model = self._create_model_from_function(self.func)
            self.name = self.name or self.func.__name__
            self.description = self.description or self.func.__doc__
            return self

        async def wrapper():
            return await self.func(**self.validate_json_or_data(*args, **kwargs))

        return wrapper()
