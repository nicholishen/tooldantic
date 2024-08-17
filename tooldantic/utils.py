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
