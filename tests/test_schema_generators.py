import pytest
from pydantic import BaseModel
from tooldantic.schema_generators import (
    CompatibilitySchemaGenerator,
    GenericSchemaGenerator,
    GoogleSchemaGenerator,
    OpenAiStrictSchemaGenerator,
    OpenAiResponseFormatGenerator,
    OpenAiSchemaGenerator,
    AnthropicSchemaGenerator,
    StrictBaseSchemaGenerator,
)



class InnerModel(BaseModel):
    item: str

class ExampleModel(BaseModel):
    name: str
    age: int
    is_student: bool
    inner: list[InnerModel]


@pytest.fixture
def example_schema():
    return {
        "title": "ExampleModel",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "is_student": {"type": "boolean"},
        },
        "required": ["name", "age", "is_student"],
    }


def test_compatibility_schema_generator():
    standard_pydantic_schema = ExampleModel.model_json_schema()
    generated_schema = ExampleModel.model_json_schema(schema_generator=CompatibilitySchemaGenerator)
    assert generated_schema == standard_pydantic_schema

    CompatibilitySchemaGenerator.is_inlined_refs = True
    generated_schema = ExampleModel.model_json_schema(schema_generator=CompatibilitySchemaGenerator)
    assert "$defs" not in generated_schema



 



def test_generic_schema_generator():
    generated_schema = ExampleModel.model_json_schema(schema_generator=GenericSchemaGenerator)

    assert generated_schema["name"] == "ExampleModel"
    assert generated_schema["description"] == ""
    assert "parameters" in generated_schema
    assert "properties" in generated_schema["parameters"]


def test_google_schema_generator():
    generated_schema = ExampleModel.model_json_schema(schema_generator=GoogleSchemaGenerator)

    assert "default" not in str(generated_schema)  # Ensure no default values


def test_strict_base_schema_generator():
    generated_schema = ExampleModel.model_json_schema(schema_generator=StrictBaseSchemaGenerator)

    assert generated_schema["strict"]
    assert generated_schema["parameters"]["additionalProperties"] is False


def test_openai_strict_schema_generator():
    generated_schema = ExampleModel.model_json_schema(schema_generator=OpenAiStrictSchemaGenerator)

    assert "function" in generated_schema
    assert generated_schema["function"]["strict"]
    assert generated_schema["function"]["parameters"]["type"] == "object"


def test_openai_response_format_generator():
    generated_schema = ExampleModel.model_json_schema(schema_generator=OpenAiResponseFormatGenerator)

    assert "json_schema" in generated_schema
    assert "schema" in generated_schema["json_schema"]
    assert generated_schema["json_schema"]["schema"]["type"] == "object"


def test_openai_schema_generator():
    generated_schema = ExampleModel.model_json_schema(schema_generator=OpenAiSchemaGenerator)

    assert "type" in generated_schema
    assert generated_schema["function"]["parameters"]["type"] == "object"


def test_anthropic_schema_generator():
    generated_schema = ExampleModel.model_json_schema(schema_generator=AnthropicSchemaGenerator)

    assert "input_schema" in generated_schema
    assert generated_schema["input_schema"]["type"] == "object"
