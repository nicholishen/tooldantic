import inspect
import json
from typing import *

try:
    import openai
except ImportError as e:
    openai = None
    print("openai not installed. Install it with `pip install openai`")
    raise ImportError(e)

from pydantic import Field, create_model

from ..builder import ModelBuilder
from ..models import ToolBaseModel
from ..utils import normalize_prompt


# TODO: This module needs a lot of work.
CLIENT = openai.OpenAI()
MODEL = "gpt-4o-mini"


class ToolWrapper:
    def __init__(self, f, validate_parameters=True):
        self.f = f
        self.validate_parameters = validate_parameters
        self._model = ModelBuilder().create_model_from_function(f)
        self._schema = self._model.model_json_schema_openai()

    def __call__(self, **kwargs):
        if self.validate_parameters:
            kwargs = self._model(**kwargs).model_dump()
        return self.f(**kwargs)

    @property
    def schema(self) -> Dict:
        return self._schema

    @property
    def model(self) -> ToolBaseModel:
        return self._model


class PydanticConstraint(ToolBaseModel):
    """Use this to define a pydantic constraint for a field."""

    name: str = Field(
        ...,
        description="The name of the constraint. Can be any pydantic constraint "
        "argument that could be used in a `pydantic.Field`",
        examples=["gt", "le", "ge", "lt", "min_length", "max_length", "pattern"],
    )
    value: Any = Field(
        ...,
        description="The value of the constraint",
    )


class DefaultValue(ToolBaseModel):
    is_required: bool = Field(
        description="Whether the parameter is required or not. "
        "False is has default value else True."
    )
    value: Any | None = Field(
        None,
        description="The default value of the parameter if it has one. "
        "Use None if it does not have a default value.",
    )


class FieldAnnotation(ToolBaseModel):
    parameter_name: str = Field(
        ...,
        description="The name of the parameter. This MUST be exactly the "
        "same as the parameter name in the function signature.",
    )
    thought_process: str = Field(
        description="Use this to document your thought process "
        "about the parameter and its type annotation."
    )
    type_annotation: str = Field(
        ...,
        description="The Python type of the field",
        examples=[
            "str",
            "int",
            "float",
            "bool",
            "typing.List[str]",
            "typing.Literal['a', 'b']",
        ],
    )
    default_value: DefaultValue = Field(
        ..., description="The default value of the parameter if it has one. "
    )
    description: str = Field(
        ...,
        description="The full description of the parameter that includes its purpose.",
    )
    constraints: list[PydanticConstraint] = Field(
        ..., description="The constraints for the field."
    )


@ToolWrapper
def annotate_function(
    func_name: str = Field(..., description="The name of the function."),
    refactored_docstring: str = Field(
        ...,
        description="Write this docstring per your system instructions.",
    ),
    annotated_parameters: List[FieldAnnotation] = Field(
        ..., description="The annotated parameters of the function."
    ),
    # return_type: str | None = Field("The return type of the function if known, otherwise `None`."),
) -> type[ToolBaseModel]:
    """Use this tool to annotate a function with pydantic fields."""
    # create fields for the model
    fields = {}
    for param in annotated_parameters:
        constraints = dict(c.values() for c in param["constraints"])
        default = param["default_value"]
        if default["is_required"]:
            default_value = ...
        else:
            default_value = default["value"]
        field_info = Field(
            default=default_value, description=param["description"], **constraints
        )
        fields[param["parameter_name"]] = (param["type_annotation"], field_info)

    Model = create_model(
        func_name,
        __base__=ToolBaseModel,
        __doc__=refactored_docstring,
        **fields,
    )
    return Model


class LlmFuncSigParser(ToolBaseModel):
    """Use this to parse the output of the standard LLM tool."""

    use_llm_callback: Callable[[str, str, Callable], type[ToolBaseModel]] = Field(
        description="A callback with params: `system_message`, `user_message`, "
        "`tool_schema` return a dict of args for the parsing tool to run."
    )
    system_message: str = normalize_prompt(
        """\
        You are an expert in python annotations and pydantic v2. When a user \
        pastes a function in the chat, you will convert the function signature by: 
        - All annotations that are not a standard type should be documented as \
        `typing.<Type>`. Assume that typing has been imported as `import typing`. \
        Don't assume that other <Types> have been imported from the typing module. \
        For example, if you need `typing.Optional`, you should write \
        `typing.Optional` instead of `Optional`.  
        - Remove the args from the docstring since they are now documented \
        in the annotations, and rewrite the docstring to be concise, complete, and clear. \
        The docstring will be used as a description for the LLM's tool so write it as if you \
        were explaining the function to someone who has never seen it before. \
        eg. `Use this tool to...`.
        - Analyze the code and write a comprehensive description of the function's purpose.
        - Evaluate the use of the parameters in the code and write better descriptions \
        for them if the docstring does not provide enough information.
        - Make sure that all parameters are annotated with the correct type and constraints, \
        even if they are not used in the code or have default values.
        - DO NOT ANNOTATE `**kwargs` OR `*args`.
        - If an argument has a default value, use the default value in the annotation.
        - If an argument is optional, use `typing.Optional` in the annotation.
        - Be on the lookout for strings literal used as enums and annotate them as `typing.Literal`.

        The most important part of your task is to closely adhere to all \
        instructions in your `annotate_function` tool. \
        """
    )
    llm_parsing_tool: Callable = annotate_function

    def __call__(self, func_text: str):
        return self.use_llm_callback(
            self.system_message, func_text, self.llm_parsing_tool
        )


def llm_callback(system_message, user_message, llm_parsing_tool):
    if isinstance(llm_parsing_tool, ToolWrapper):
        tool_schema = llm_parsing_tool.schema
    else:
        tool_schema = (
            ModelBuilder()
            .create_model_from_function(llm_parsing_tool)
            .model_json_schema_openai()
        )
    r = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        tools=[tool_schema],
        tool_choice="required",
        temperature=0.1,
    )
    args = json.loads(r.choices[0].message.tool_calls[0].function.arguments)
    NewModel = llm_parsing_tool(**args)
    return NewModel


class LlmModelBuilder(ModelBuilder):

    def create_model_from_function_with_llm(
        self,
        func: Callable,
        use_parser: Callable[[str], type[ToolBaseModel]] = LlmFuncSigParser(
            use_llm_callback=llm_callback
        ),
    ) -> ToolBaseModel:
        # extract the func as full text. signature, docstring, and all
        func_text = inspect.getsource(func)
        Model = use_parser(func_text)
        return Model
