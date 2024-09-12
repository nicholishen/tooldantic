from __future__ import annotations

from functools import update_wrapper
from typing import Callable, Optional, overload

from .builder import ModelBuilder
from .models import ToolBaseModel
from .utils import ModelT


class ToolWrapperBase:
    """
    ToolWrapperBase is a base class for creating tool wrappers.
    Args:
        func (Optional[Callable]): The function to be wrapped.
        name (Optional[str]): The name of the tool.
        description (Optional[str]): The description of the tool.
        base_model (type[ModelT]): The base model for the tool.
        is_auto_validate_json (bool): Flag indicating whether to automatically validate JSON data.
        **pydantic_kwargs: Additional keyword arguments to be passed to the Pydantic model.
    Attributes:
        func (Optional[Callable]): The wrapped function.
        base_model (type[ModelT]): The base model for the tool.
        name (str): The name of the tool.
        description (str): The description of the tool.
        is_auto_validate_json (bool): Flag indicating whether to automatically validate JSON data.
        pydantic_kwargs (dict): Additional keyword arguments passed to the Pydantic model.
        _model (type[ModelT]): The Pydantic model generated from the function.
    Methods:
        validate_json_or_data: Validates JSON data or keyword arguments.
        model_json_schema: Generates the JSON schema for the model.
    """
    
    

    def __init__(
        self,
        func: Optional[Callable] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        base_model: type[ModelT] = ToolBaseModel,
        is_auto_validate_json: bool = True,
        # TODO: Add support for response model = False. This will allow for functions to return a default response without validation.
        # maybe `response_format_return`
        **pydantic_kwargs
    ):
        self.func = func
        self.base_model = base_model
        self.name = name or (func.__name__ if func else None)
        self.description = description or (func.__doc__ if func else None)
        self.is_auto_validate_json = is_auto_validate_json
        self.pydantic_kwargs = pydantic_kwargs

        if func:
            self._model = self._create_model_from_function(func)
            update_wrapper(self, func)
        else:
            self._model = None

    def _create_model_from_function(self, func: Callable):
        return ModelBuilder(base_model=self.base_model, **self.pydantic_kwargs).model_from_function(
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
    """
    ToolWrapper class is a decorator that wraps a function and provides additional functionality.
    Properties from the super class (ToolWrapperBase):
    - name: The name of the tool.
    - description: The description of the tool.
    - model: The model associated with the tool.
    Attributes:
        func (function): The wrapped function.
    Methods:
        __call__(*args, **kwargs): Executes the wrapped function with the provided arguments after validating the JSON or data.
    Raises:
        ValueError: If the function is not provided.
    Returns:
        ToolWrapper: The instance of the ToolWrapper class.
    Example usage:
        @ToolWrapper
        def my_tool(data):
            # Function implementation
        my_tool.name = "My Tool"
        my_tool.description = "This is a tool for processing data"
        my_tool.model = "My Model"
        result = my_tool(data)
    """
    
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
    """
    AsyncToolWrapper is a class that serves as a decorator for asynchronous tool functions.
    Properties from super class (ToolWrapperBase):
    - func: The wrapped function.
    - name: The name of the tool.
    - description: The description of the tool.
    Methods:
    - __call__(self, *args, **kwargs): Overrides the call behavior of the decorator. It validates the input arguments, creates a model from the wrapped function, and returns a wrapper function that executes the wrapped function asynchronously.
    Example usage:
    @AsyncToolWrapper
    async def my_tool(input_data):
        # Tool logic goes here
    my_tool.name = "My Tool"
    my_tool.description = "This is a tool for processing input data asynchronously."
    """
    
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