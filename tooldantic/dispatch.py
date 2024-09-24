import inspect
from typing import Callable, Iterable, Union

from .decorators import AsyncToolWrapper, ToolWrapper, ToolWrapperBase
from .models import ToolBaseModel
from pydantic import ValidationError


class ToolDispatch:
    """
    A class representing a tool dispatcher.
    The ToolDispatch class is responsible for managing a collection of tool functions
    and providing methods for accessing, updating, and manipulating the tools.
    Args:
        *funcs: Union[ToolWrapperBase, Callable]: Variable-length argument list of tool functions.
        base_model: Optional[type[ToolBaseModel]]: The base model for the tools.
        **pydantic_kwargs: Additional keyword arguments for configuring Pydantic models.
    Attributes:
        func_dispatch (dict): A dictionary mapping tool names to their corresponding tool functions.
        base_model (type[ToolBaseModel] | None): The base model for the tools.
        pydantic_kwargs (dict): Additional keyword arguments for configuring Pydantic models.
    Methods:
        __len__(): Returns the number of tools in the dispatcher.
        __getitem__(key: str) -> ToolWrapperBase: Returns the tool function with the specified key.
        __setitem__(key: str, value: Union[ToolWrapperBase, Callable]): Sets the tool function with the specified key.
        __iter__(): Returns an iterator over the JSON schema of each tool function.
        __or__(other: ToolDispatch): Combines two ToolDispatch instances into a new instance.
        __contains__(key: str): Checks if a tool function with the specified key exists in the dispatcher.
        pop(key: str) -> ToolWrapperBase: Removes and returns the tool function with the specified key.
        clear(): Removes all tool functions from the dispatcher.
        get(key: str, default: ToolWrapperBase) -> ToolWrapperBase: Returns the tool function with the specified key, or a default value if not found.
        items(): Returns an iterator over the key-value pairs of the tool functions.
        keys(): Returns an iterator over the keys of the tool functions.
        values(): Returns an iterator over the values of the tool functions.
    """
    
    def __init__(
        self,
        *funcs: Union[ToolWrapperBase, Callable],
        base_model: type[ToolBaseModel] | None = None,
        **pydantic_kwargs
    ):
        if funcs and isinstance(funcs[0], Iterable):
            funcs = list(funcs[0])

        self.func_dispatch = {}
        self.base_model = base_model
        self.pydantic_kwargs = pydantic_kwargs

        for func in funcs:
            func = self._wrap_func(func, **pydantic_kwargs)
            if func.name in self.func_dispatch:
                raise ValueError(f"Tool '{func.name}' already exists in dispatcher.")
            self.func_dispatch[func.name] = func

    def __len__(self):
        return len(self.func_dispatch)

    def __getitem__(self, key: str) -> ToolWrapperBase:
        if key not in self.func_dispatch:
            raise KeyError(f"Function '{key}' not found in dispatcher.")
        return self.func_dispatch[key]

    def __setitem__(self, key: str, value: Union[ToolWrapperBase, Callable]):
        # TODO: Add support for updating existing functions
        func = self._wrap_func(value, name=key)
        self.func_dispatch[key] = func

    # def __iter__(self):
    #     yield from [f.model_json_schema() for f in self.func_dispatch.values()]

    def __or__(self, other):
        if not isinstance(other, ToolDispatch):
            raise TypeError(
                f"unsupported operand type(s) for |: 'ToolDispatch' and {type(other)}")
        all_funcs = [*self.func_dispatch.values(), *other.func_dispatch.values()]
        base_model = other.base_model or self.base_model
        all_kwargs = {**self.pydantic_kwargs, **other.pydantic_kwargs, 'base_model': base_model}
        return ToolDispatch(*all_funcs, **all_kwargs)

    def __contains__(self, key):
        return key in self.func_dispatch

    def _wrap_func(self, func, **kwargs):
        if not isinstance(func, ToolWrapperBase):
            if self.base_model is None:
                raise ValueError(
                    "base_model must be provided when func is not a ToolWrapperBase")
            is_async = inspect.iscoroutinefunction(func)
            Wrapper = AsyncToolWrapper if is_async else ToolWrapper
            func = Wrapper(func, base_model=self.base_model, **kwargs)
        return func
    
    @property
    def schemas(self):
        return [f.model_json_schema() for f in self.func_dispatch.values()]

    def pop(self, key: str) -> ToolWrapperBase:
        if key not in self.func_dispatch:
            raise KeyError(f"Function '{key}' not found in dispatcher.")
        return self.func_dispatch.pop(key)

    def clear(self):
        self.func_dispatch.clear()
        return self

    def get(self, key: str, default: ToolWrapperBase) -> ToolWrapperBase:
        return self.func_dispatch.get(key, default)

    def items(self):
        yield from self.func_dispatch.items()

    def keys(self):
        yield from self.func_dispatch.keys()

    def values(self):
        yield from self.func_dispatch.values()
