import inspect
import json
import re
import textwrap
from typing import Annotated, Any, Callable, NewType, TypeVar, Union, get_origin, cast, Dict, List, Any

import pydantic
import pydantic_core


class ToolError(Exception):
    """Base class for exceptions raised by tools."""
    

def normalize_prompt(prompt: str, max_spaces: int = 3) -> str:
    """Helper function to dedent a multi-line prompt string and remove extra spaces."""
    prompt = "\n".join(
        re.sub(rf"(?<=\S)\s{{{max_spaces},}}", " ", line)
        for line in textwrap.dedent(prompt).split("\n")
    )
    return prompt


ModelT = TypeVar("ModelT", bound=pydantic.BaseModel)
_Unset = pydantic_core.PydanticUndefined
_Empty = inspect.Parameter.empty


TypeOrAnnotation = Union[
    type,
    Callable[..., Any],
    Union[Any, Any],
    NewType,
    Annotated[Any, Any],
]


def is_type_or_annotation(obj: Any) -> bool:
    """
    Determine if the given object is a type (like `str`) or a type annotation (like `Annotated[str]`).
    Returns `True` for types and type annotations, and `False` for instance objects.
    """
    if obj is ... or obj is _Unset:
        return False
    # Check if the object is an instance of any of the types in TypeOrAnnotation
    try:
        if isinstance(obj, TypeOrAnnotation):
            return True
    except TypeError:
        pass

    # Special cases for types with __origin__ and __args__
    if hasattr(obj, "__origin__") and hasattr(obj, "__args__"):
        return True
    if get_origin(obj) is not None:
        return True

    return False


def normalize_prompt(prompt: str, max_spaces: int = 3) -> str:
    """Helper function to dedent a multi-line prompt string and remove extra spaces."""
    prompt = "\n".join(
        re.sub(rf"(?<=\S)\s{{{max_spaces},}}", " ", line)
        for line in textwrap.dedent(prompt).split("\n")
    )
    return prompt


def validation_error_to_llm_feedback(
    error: pydantic.ValidationError,
    message_to_assistant: str = "Please pay close attention to the following "
    "pydantic errors and use them to correct your tool inputs.",
) -> str:
    """
    Convert a Pydantic ValidationError to a standardized LLM feedback message.
    Ideally, the industry could agree on a standard format for error feedback messages
    and train them into the tool calling models.

    returns: str - JSON string with the following keys
        - success: bool - False
        - message_to_assistant: str - Message to assistant
        - errors: List[Dict[str, Any]] - List of errors
    """
    def nested_objs_to_str(obj):
        if isinstance(obj, dict):
            return {k: nested_objs_to_str(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [nested_objs_to_str(v) for v in obj]
        if isinstance(obj, pydantic.ValidationError):
            return obj.errors(include_url=False)
        return str(obj)
    
    errors = [nested_objs_to_str(e) for e in error.errors(include_url=False)]


    feedback = {
        "success": False,
        "message_to_assistant": message_to_assistant,
        "errors": errors,
    }
    return json.dumps(feedback)

# from __future__ import annotations

# from typing import Any, Dict, cast

# import pydantic

# from ._pydantic import to_strict_json_schema
# from ..types.chat import ChatCompletionToolParam
# from ..types.shared_params import FunctionDefinition
# from .types import FunctionDefinition, ChatCompletionToolParam


# class PydanticFunctionTool(dict[str, Any]):
#     """Dictionary wrapper so we can pass the given base model
#     throughout the entire request stack without having to special
#     case it.
#     """

#     model: type[pydantic.BaseModel]

#     def __init__(self, defn, model: type[pydantic.BaseModel]) -> None:
#         super().__init__(defn)
#         self.model = model

#     def cast(self) -> FunctionDefinition:
#         return cast(FunctionDefinition, self)


# def pydantic_function_tool(
#     model: type[pydantic.BaseModel],
#     *,
#     name: str | None = None,  # inferred from class name by default
#     description: str | None = None,  # inferred from class docstring by default
# ) -> ChatCompletionToolParam:
#     if description is None:
#         # note: we intentionally don't use `.getdoc()` to avoid
#         # including pydantic's docstrings
#         description = model.__doc__

#     function = PydanticFunctionTool(
#         {
#             "name": name or model.__name__,
#             "strict": True,
#             "parameters": to_strict_json_schema(model),
#         },
#         model,
#     ).cast()

#     if description is not None:
#         function["description"] = description

#     return {
#         "type": "function",
#         "function": function,
#     }


# def to_strict_json_schema(model: type[pydantic.BaseModel]) -> dict[str, Any]:
#     return _ensure_strict_json_schema(model.model_json_schema(), path=())


def _ensure_strict_json_schema(
    json_schema: object,
    path: tuple[str, ...],
) -> dict[str, Any]:
    """Mutates the given JSON schema to ensure it conforms to the `strict` standard
    that the API expects.
    """
    if not isinstance(json_schema, dict):
        raise TypeError(f"Expected {json_schema} to be a dictionary; path={path}")

    typ = json_schema.get("type")
    if typ == "object" and "additionalProperties" not in json_schema:
        json_schema["additionalProperties"] = False

    # object types
    # { 'type': 'object', 'properties': { 'a':  {...} } }
    properties = json_schema.get("properties")
    if isinstance(properties, dict):
        json_schema["required"] = [prop for prop in properties.keys()]
        json_schema["properties"] = {
            key: _ensure_strict_json_schema(prop_schema, path=(*path, "properties", key))
            for key, prop_schema in properties.items()
        }

    # arrays
    # { 'type': 'array', 'items': {...} }
    items = json_schema.get("items")
    if isinstance(items, list):
        json_schema["items"] = _ensure_strict_json_schema(items, path=(*path, "items"))

    # unions
    any_of = json_schema.get("anyOf")
    if isinstance(any_of, list):
        json_schema["anyOf"] = [
            _ensure_strict_json_schema(variant, path=(*path, "anyOf", str(i))) for i, variant in enumerate(any_of)
        ]

    # intersections
    all_of = json_schema.get("allOf")
    if isinstance(all_of, list):
        json_schema["allOf"] = [
            _ensure_strict_json_schema(entry, path=(*path, "anyOf", str(i))) for i, entry in enumerate(all_of)
        ]

    defs = json_schema.get("$defs")
    if isinstance(defs, dict): #is_dict(defs):
        for def_name, def_schema in defs.items():
            _ensure_strict_json_schema(def_schema, path=(*path, "$defs", def_name))

    definitions = json_schema.get("definitions")
    if isinstance(definitions, dict):
        for definition_name, definition_schema in definitions.items():
            _ensure_strict_json_schema(definition_schema, path=(*path, "definitions", definition_name))

    return json_schema



