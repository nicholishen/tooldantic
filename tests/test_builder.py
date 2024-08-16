# tooldantic/tests/test_builder.py

import pytest
from pydantic import ValidationError, ConfigDict
from tooldantic.builder import ModelBuilder, ToolBaseModel
from typing import Optional


class TbmNoExtra(ToolBaseModel):
    model_config = ConfigDict(extra="forbid")

def test_create_model_from_simple_schema():
    data = {"name": "example name", "age": 30}
    model_name = "SimpleModel"
    Model = ModelBuilder().create_model_from_schema_dict(data, model_name)

    validated_data = Model(**data)
    assert validated_data.name == "example name"
    assert validated_data.age == 30


def test_create_model_from_nested_schema():
    data = {"outer": {"inner": {"name": "example name"}}}
    model_name = "NestedModel"
    Model = ModelBuilder().create_model_from_schema_dict(data, model_name)

    validated_data = Model(**data)
    assert validated_data.outer.inner.name == "example name"


def test_create_model_with_list_of_strings():
    data = {"items": ["item1", "item2", "item3"]}
    model_name = "ListModel"
    Model = ModelBuilder().create_model_from_schema_dict(data, model_name)

    validated_data = Model(**data)
    assert validated_data.items == ["item1", "item2", "item3"]


def test_create_model_with_list_of_dicts():
    data = {"items": [{"name": "item1"}, {"name": "item2"}, {"name": "item3"}]}
    model_name = "ListDictModel"
    Model = ModelBuilder().create_model_from_schema_dict(data, model_name)

    validated_data = Model(**data)
    assert validated_data.items[0].name == "item1"
    assert validated_data.items[1].name == "item2"
    assert validated_data.items[2].name == "item3"


def test_create_model_with_missing_required_field():
    data = {"name": "example name"}  # Assuming 'age' is required and missing
    model_name = "MissingFieldModel"
    Model = ModelBuilder().create_model_from_schema_dict(
        {"name": str, "age": int}, model_name
    )

    with pytest.raises(ValidationError):
        Model(**data)  # This should fail because 'age' is missing


def test_create_model_from_function():
    def example_function(name: str, age: int):
        return {"name": name, "age": age}

    model_name = "FunctionModel"
    Model = ModelBuilder().create_model_from_function(example_function, model_name)

    data = {"name": "example name", "age": 30}
    validated_data = Model(**data)
    assert validated_data.name == "example name"
    assert validated_data.age == 30


def test_create_model_from_json_schema():
    json_schema = {
        "name": "JsonSchemaModel",
        "description": "A model created from JSON schema",
        "parameters": {
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        },
    }

    Model = ModelBuilder().create_model_from_json_schema(json_schema)

    data = {"name": "example name", "age": 30}
    validated_data = Model(**data)
    assert validated_data.name == "example name"
    assert validated_data.age == 30


def test_infer_type_from_empty_list():
    data = {"items": []}
    model_name = "EmptyListModel"
    Model = ModelBuilder().create_model_from_schema_dict(data, model_name)

    validated_data = Model(**data)
    assert validated_data.items == []


def test_create_model_with_none_values():
    data = {"name": None, "age": None}
    model_name = "NoneValuesModel"
    Model = ModelBuilder().create_model_from_schema_dict(data, model_name)

    validated_data = Model(**data)
    assert validated_data.name is None
    assert validated_data.age is None


def test_reject_extra_fields():

    data = {"name": "example name", "age": 30, "extra": "not allowed"}
    model_name = "RejectExtraFieldsModel"
    Model = ModelBuilder(base_model=TbmNoExtra).create_model_from_schema_dict(
        {"name": str, "age": int}, model_name
    )

    with pytest.raises(ValidationError) as exc_info:
        Model(**data)


def test_nested_model_reject_extra_fields():
    nested_schema = {"inner": {"name": str}}
    model_name = "NestedRejectExtraModel"
    Model = ModelBuilder(base_model=TbmNoExtra).create_model_from_schema_dict(nested_schema, model_name)

    data = {"inner": {"name": "Inner Name", "extra": "not allowed"}}
    with pytest.raises(ValidationError) as exc_info:
        Model(**data)


def test_complex_nested_structure():
    complex_schema = {
        "profile": {"name": str, "details": {"age": int, "hobbies": [str]}}
    }
    model_name = "ComplexNestedModel"
    Model = ModelBuilder().create_model_from_schema_dict(complex_schema, model_name)

    data = {
        "profile": {
            "name": "Alice",
            "details": {"age": 30, "hobbies": ["reading", "swimming"]},
        }
    }
    validated_data = Model(**data)
    assert validated_data.profile.name == "Alice"
    assert validated_data.profile.details.age == 30
    assert validated_data.profile.details.hobbies == ["reading", "swimming"]


def test_dynamic_field_types():
    from typing import Any

    dynamic_schema = {"value": Any}
    model_name = "DynamicFieldModel"
    Model = ModelBuilder().create_model_from_schema_dict(dynamic_schema, model_name)

    for input_value in [123, "abc", [1, 2, 3], {"key": "value"}]:
        data = {"value": input_value}
        validated_data = Model(**data)
        assert validated_data.value == input_value


import pytest
from pydantic import ValidationError
from tooldantic.builder import ModelBuilder


# Test creating a model from a schema with all basic types
def test_create_model_from_all_basic_types_schema():
    data = {
        "name": "example name",
        "age": 30,
        "is_active": True,
        "balance": 100.50,
        "join_date": "2023-01-01",
    }
    schema = {
        "name": str,
        "age": int,
        "is_active": bool,
        "balance": float,
        "join_date": "date",
    }
    model_name = "AllBasicTypesModel"
    Model = ModelBuilder().create_model_from_schema_dict(schema, model_name)

    validated_data = Model(**data)
    assert validated_data.name == "example name"
    assert validated_data.age == 30
    assert validated_data.is_active is True
    assert validated_data.balance == 100.50
    assert validated_data.join_date == "2023-01-01"


# Test creating a model from a schema with a default value
def test_create_model_with_default_values():

    def f(name: str = "default name", age: int = 18):
        pass

    Model = ModelBuilder().create_model_from_function(f)

    data = {}
    validated_data = Model(**data)
    assert validated_data.name == "default name"
    assert validated_data.age == 18


# Test creating a model from a schema with optional fields
def test_create_model_with_optional_fields():

    def f(name: str, age: Optional[int] = None):
        pass

    model_name = "OptionalFieldsModel"
    Model = ModelBuilder().create_model_from_function(f, model_name)

    data = {"name": "example name"}
    validated_data = Model(**data)
    assert validated_data.name == "example name"
    assert validated_data.age is None


# Test creating a model from a complex JSON schema
def test_create_model_from_complex_json_schema():
    json_schema = {
        "name": "ComplexJsonSchemaModel",
        "description": "A complex model created from JSON schema",
        "parameters": {
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                    },
                    "required": ["street"],
                },
            },
            "required": ["name", "address"],
        },
    }

    Model = ModelBuilder().create_model_from_json_schema(json_schema)

    data = {
        "name": "example name",
        "age": 30,
        "address": {"street": "123 Main St", "city": "Anytown"},
    }
    validated_data = Model(**data)
    assert validated_data.name == "example name"
    assert validated_data.age == 30
    assert validated_data.address.street == "123 Main St"
    assert validated_data.address.city == "Anytown"


# Test creating a model with constraints
def test_create_model_with_constraints():
    json_schema = {
        "name": "ConstrainedModel",
        "description": "A model with constraints",
        "parameters": {
            "properties": {
                "username": {"type": "string", "minLength": 3, "maxLength": 15},
                "age": {"type": "integer", "minimum": 18, "maximum": 99},
            },
            "required": ["username", "age"],
        },
    }

    Model = ModelBuilder().create_model_from_json_schema(json_schema)

    valid_data = {"username": "user123", "age": 30}
    validated_data = Model(**valid_data)
    assert validated_data.username == "user123"
    assert validated_data.age == 30

    invalid_data = {"username": "us", "age": 17}
    with pytest.raises(ValidationError):
        Model(**invalid_data)


# Test creating a model with nested lists
def test_create_model_with_nested_lists():
    schema = {"items": [{"name": str, "quantity": int}]}
    model_name = "NestedListsModel"
    Model = ModelBuilder().create_model_from_schema_dict(schema, model_name)

    data = {
        "items": [{"name": "item1", "quantity": 5}, {"name": "item2", "quantity": 10}]
    }
    validated_data = Model(**data)
    assert validated_data.items[0].name == "item1"
    assert validated_data.items[0].quantity == 5
    assert validated_data.items[1].name == "item2"
    assert validated_data.items[1].quantity == 10


# Test creating a model with deeply nested structures
def test_create_model_with_deeply_nested_structures():
    schema = {"level1": {"level2": {"level3": {"level4": {"name": str, "value": int}}}}}
    model_name = "DeeplyNestedModel"
    Model = ModelBuilder().create_model_from_schema_dict(schema, model_name)

    data = {"level1": {"level2": {"level3": {"level4": {"name": "deep", "value": 42}}}}}
    validated_data = Model(**data)
    assert validated_data.level1.level2.level3.level4.name == "deep"
    assert validated_data.level1.level2.level3.level4.value == 42


# Test dynamic adaptation to changes in data requirements
def test_dynamic_schema_adaptation():
    schema_v1 = {"name": str}
    schema_v2 = {"name": str, "age": int}

    model_name_v1 = "DynamicModelV1"
    model_name_v2 = "DynamicModelV2"

    ModelV1 = ModelBuilder(base_model=TbmNoExtra).create_model_from_schema_dict(schema_v1, model_name_v1)
    ModelV2 = ModelBuilder().create_model_from_schema_dict(schema_v2, model_name_v2)

    data_v1 = {"name": "example name"}
    validated_data_v1 = ModelV1(**data_v1)
    assert validated_data_v1.name == "example name"

    data_v2 = {"name": "example name", "age": 30}
    validated_data_v2 = ModelV2(**data_v2)
    assert validated_data_v2.name == "example name"
    assert validated_data_v2.age == 30

    with pytest.raises(ValidationError):
        ModelV1(**data_v2)


# Test schema extraction and validation for LLM outputs
def test_llm_output_validation():
    json_schema = {
        "name": "LLMOutputModel",
        "description": "Model for validating LLM outputs",
        "parameters": {
            "properties": {"text": {"type": "string"}, "score": {"type": "number"}},
            "required": ["text"],
        },
    }

    Model = ModelBuilder().create_model_from_json_schema(json_schema)

    valid_output = {"text": "This is a response", "score": 0.95}
    validated_output = Model(**valid_output)
    assert validated_output.text == "This is a response"
    assert validated_output.score == 0.95

    invalid_output = {"score": 0.95}
    with pytest.raises(ValidationError):
        Model(**invalid_output)


# Test schema with optional and required fields
def test_schema_with_optional_and_required_fields():

    def f(required_field: str, optional_field: str | None = None):
        pass

    model_name = "OptionalAndRequiredFieldsModel"
    Model = ModelBuilder().create_model_from_function(f, model_name)
    data = {"required_field": "example"}
    validated_data = Model(**data)
    assert validated_data.required_field == "example"
    assert validated_data.optional_field is None


# Test schema with boolean field
def test_schema_with_boolean_field():
    schema = {"is_active": bool}
    model_name = "BooleanFieldModel"
    Model = ModelBuilder().create_model_from_schema_dict(schema, model_name)

    data = {"is_active": True}
    validated_data = Model(**data)
    assert validated_data.is_active is True

    data = {"is_active": False}
    validated_data = Model(**data)
    assert validated_data.is_active is False


# Test creating model with various field names and types
def test_create_model_with_various_field_names_and_types():
    from datetime import date

    schema = {
        "field1": str,
        "field2": int,
        "field3": float,
        "field4": bool,
        "field5": date,
    }
    model_name = "VariousFieldNamesAndTypesModel"
    Model = ModelBuilder().create_model_from_schema_dict(schema, model_name)

    data = {
        "field1": "string_value",
        "field2": 123,
        "field3": 456.78,
        "field4": True,
        "field5": "2023-01-01",
    }
    validated_data = Model(**data)
    assert validated_data.field1 == "string_value"
    assert validated_data.field2 == 123
    assert validated_data.field3 == 456.78
    assert validated_data.field4 is True
    assert validated_data.field5 == date(2023, 1, 1)

def test_create_model_with_any_type_in_json_schema():
    json_schema = {
        "name": "AnyTypeModel",
        "description": "Model with any type",
        "parameters": {
            "properties": {"value": {}},
            "required": ["value"],
        },
    }

    Model = ModelBuilder().create_model_from_json_schema(json_schema)

    data = {"value": 123}
    validated_data = Model(**data)
    assert validated_data.value == 123

    data = {"value": "abc"}
    validated_data = Model(**data)
    assert validated_data.value == "abc"

    data = {"value": [1, 2, 3]}
    validated_data = Model(**data)
    assert validated_data.value == [1, 2, 3]

    data = {"value": {"key": "value"}}
    validated_data = Model(**data)
    assert validated_data.value == {"key": "value"}


def test_create_model_kwargs_in_function_signature():

    def f(**kwargs):
        pass

    ModelBuilder().create_model_from_function(f)
    assert True