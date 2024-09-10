import pytest
from typing import List, Literal, Annotated
from pydantic import BaseModel, ValidationError, Field
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from tooldantic.builder import ModelBuilder, _Empty
from tooldantic.utils import ToolError, Any as ToolAny
import tooldantic as td


# Fixture for the ModelBuilder
@pytest.fixture
def model_builder():
    return ModelBuilder()


def test_create_model_from_function(model_builder):
    def sample_function(name: str, age: int, is_student: bool = False):
        """Sample function for testing"""
        return f"{name}, {age}, {'student' if is_student else 'non-student'}"

    model = model_builder.model_from_function(sample_function)

    assert issubclass(model, BaseModel)
    assert model.__name__ == "sample_function"
    assert model.__doc__ == "Sample function for testing"

    instance = model(name="John", age=25)
    assert instance.name == "John"
    assert instance.age == 25
    assert instance.is_student is False

    with pytest.raises(ValidationError):
        model(name="John")


def test_create_model_from_function_no_annotation(model_builder):
    def incomplete_function(name):
        return name

    with pytest.raises(ToolError):
        model_builder.model_from_function(incomplete_function)


def test_create_model_from_function_no_default_value(model_builder):
    def incomplete_function(name: str):
        return name

    model = model_builder.model_from_function(incomplete_function)
    instance = model(name="John")
    assert instance.name == "John"


def test_create_model_from_schema_dict(model_builder):
    sample_schema_dict = {
        "name": "John",
        "age": 30,
        "is_student": True,
    }
    model = model_builder.model_from_dict(
        sample_schema_dict, "SampleModel"
    )

    assert issubclass(model, BaseModel)
    assert model.__name__ == "SampleModel"

    instance = model(name="John", age=30, is_student=True)
    assert instance.name == "John"
    assert instance.age == 30
    assert instance.is_student is True


def test_create_model_from_schema_dict_no_defaults(model_builder):
    sample_schema_dict = {
        "name": "John",
        "age": 30,
        "is_student": None,
    }
    model = model_builder.model_from_dict(
        sample_schema_dict, "SampleModel", is_set_defaults_from_values=False
    )

    # Adjust to match the actual behavior of the method
    with pytest.raises(ValidationError):
        model(name="John", age=30)


def test_create_model_from_json_schema(model_builder):
    sample_json_schema = {
        "name": "sample_json_schema",
        "description": "Sample JSON schema for testing",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "is_student": {"type": "boolean", "default": False},
            },
            "required": ["name", "age"],
        },
    }
    model = model_builder.model_from_json_schema(sample_json_schema)

    assert issubclass(model, BaseModel)
    assert model.__name__ == "sample_json_schema"

    instance = model(name="John", age=25)
    assert instance.name == "John"
    assert instance.age == 25
    assert instance.is_student is False


def test_extract_schema_details(model_builder):
    sample_json_schema = {
        "name": "sample_json_schema",
        "description": "Sample JSON schema for testing",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "is_student": {"type": "boolean", "default": False},
            },
            "required": ["name", "age"],
        },
    }

    name, description, parameters = model_builder._extract_schema_details(
        sample_json_schema
    )

    assert name == "sample_json_schema"
    assert description == "Sample JSON schema for testing"
    assert "name" in parameters["properties"]
    assert "age" in parameters["properties"]


def test_parse_parameters(model_builder):
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "is_student": {"type": "boolean", "default": False},
        },
        "required": ["name", "age"],
    }
    fields = model_builder._parse_parameters(parameters, "SampleModel")

    assert "name" in fields
    assert fields["name"][0] == str
    assert isinstance(fields["name"][1], FieldInfo)

    assert "age" in fields
    assert fields["age"][0] == int


def test_map_json_type_to_python(model_builder):
    field_type, field_default = model_builder._map_json_type_to_python(
        {"type": "string", "default": "John"},
        "name",
        "SampleModel",
        is_required=True,
    )

    assert field_type == str
    assert field_default.default == "John"

    field_type, field_default = model_builder._map_json_type_to_python(
        {"type": "integer", "default": 30},
        "age",
        "SampleModel",
        is_required=True,
    )

    assert field_type == int
    assert field_default.default == 30

    field_type, field_default = model_builder._map_json_type_to_python(
        {"type": "string", "enum": ["red", "green", "blue"]},
        "color",
        "SampleModel",
        is_required=True,
    )

    assert field_type == Literal["red", "green", "blue"]
    assert field_default.default == PydanticUndefined


def test_process_field_with_annotation(model_builder):
    annotation = str
    default = "default_value"
    field_type, field_default = model_builder._process_field(
        field_name="test_field",
        model_name="TestModel",
        annotation=annotation,
        default=default,
        use_defaults=True,
    )

    assert field_type == str
    assert field_default == "default_value"

def test_new_response_format():
    class SampleModel(td.OpenAiResponseFormatBaseModel):
        """Sample model for testing"""
        name: str
        
    schema = SampleModel.model_json_schema()
    
    model_builder = ModelBuilder(base_model=td.OpenAiResponseFormatBaseModel)
    
    Model = model_builder.model_from_json_schema(schema)
    
