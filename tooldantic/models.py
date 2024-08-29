import pydantic

from .schema_generators import (
    AnthropicSchemaGenerator,
    CompatibilitySchemaGenerator,
    GenerateJsonSchema,
    GenericSchemaGenerator,
    GoogleSchemaGenerator,
    OpenAiSchemaGenerator,
    OpenAiStrictSchemaGenerator,
    OpenAiResponseFormatGenerator,
)

from typing import ClassVar, Optional


class ToolBaseModel(pydantic.BaseModel):
    """
    Subclass of `pydantic.BaseModel` that provides additional functionality for LLM tool schema generation.
    """

    _schema_generator: ClassVar[Optional[GenerateJsonSchema]] = None

    @classmethod
    def model_bind_schema_generator(cls, schema_generator: GenerateJsonSchema) -> None:
        """
        Bind a schema generator to the model class.

        Args:
            schema_generator: The schema generator to bind to the model class.
        """
        cls._schema_generator = schema_generator

    @classmethod
    def model_json_schema(cls, schema_generator=None, **kwargs):
        # explicitly pass the ref template in case pydantic changes the default
        schema_generator = (
            schema_generator or cls._schema_generator or CompatibilitySchemaGenerator
        )
        default_kwargs = {
            "ref_template": "#/$defs/{model}",
            "mode": "serialization",
            "schema_generator": schema_generator,
            **kwargs,
        }
        return super().model_json_schema(**default_kwargs)


class OpenAiBaseModel(ToolBaseModel):
    schema_generator = OpenAiSchemaGenerator


class OpenAiStrictBaseModel(ToolBaseModel):
    """This model sets up the model so that the schema includes:
    `additionalProperties=False`"""

    schema_generator = OpenAiStrictSchemaGenerator


class OpenAiResponseFormatBaseModel(ToolBaseModel):
    schema_generator = OpenAiResponseFormatGenerator


class AnthropicBaseModel(ToolBaseModel):
    schema_generator = AnthropicSchemaGenerator


class GoogleBaseModel(ToolBaseModel):
    schema_generator = GoogleSchemaGenerator


class GenericBaseModel(ToolBaseModel):
    schema_generator = GenericSchemaGenerator
