import pytest
from pydantic import ValidationError, ConfigDict
from tooldantic.builder import ModelBuilder, ToolBaseModel
from typing import Optional, Any
from datetime import date


class TbmNoExtra(ToolBaseModel):
    model_config = ConfigDict(extra="forbid")


# Basic Model Creation Tests
def test_create_model_from_simple_schema():
    data = {"name": "example name", "age": 30}
    Model = ModelBuilder().model_from_dict(data, "SimpleModel")
    validated_data = Model(**data)
    assert validated_data.name == "example name"
    assert validated_data.age == 30


def test_create_model_with_missing_required_field():
    schema = {"name": str, "age": int}
    data = {"name": "example name"}  # Missing 'age'
    Model = ModelBuilder().model_from_dict(schema, "MissingFieldModel")
    with pytest.raises(ValidationError):
        Model(**data)


def test_create_model_with_default_values():
    def example_function(name: str = "default name", age: int = 18):
        pass

    Model = ModelBuilder().model_from_function(example_function)
    validated_data = Model()
    assert validated_data.name == "default name"
    assert validated_data.age == 18


def test_create_model_with_optional_fields():
    def example_function(name: str, age: Optional[int] = None):
        pass

    Model = ModelBuilder().model_from_function(example_function)
    validated_data = Model(name="example name")
    assert validated_data.name == "example name"
    assert validated_data.age is None


# Nested Structure Tests
def test_create_model_from_nested_schema():
    schema = {"outer": {"inner": {"name": str}}}
    data = {"outer": {"inner": {"name": "example name"}}}
    Model = ModelBuilder().model_from_dict(schema, "NestedModel")
    validated_data = Model(**data)
    assert validated_data.outer.inner.name == "example name"


def test_complex_nested_structure():
    schema = {"profile": {"name": str, "details": {"age": int, "hobbies": [str]}}}
    data = {"profile": {"name": "Alice", "details": {"age": 30, "hobbies": ["reading", "swimming"]}}}
    Model = ModelBuilder().model_from_dict(schema, "ComplexNestedModel")
    validated_data = Model(**data)
    assert validated_data.profile.name == "Alice"
    assert validated_data.profile.details.age == 30
    assert validated_data.profile.details.hobbies == ["reading", "swimming"]


def test_create_model_with_deeply_nested_structures():
    schema = {"level1": {"level2": {"level3": {"level4": {"name": str, "value": int}}}}}
    data = {"level1": {"level2": {"level3": {"level4": {"name": "deep", "value": 42}}}}}
    Model = ModelBuilder().model_from_dict(schema, "DeeplyNestedModel")
    validated_data = Model(**data)
    assert validated_data.level1.level2.level3.level4.name == "deep"
    assert validated_data.level1.level2.level3.level4.value == 42


# List and Dynamic Types Tests
def test_create_model_with_list_of_strings():
    schema = {"items": [str]}
    data = {"items": ["item1", "item2", "item3"]}
    Model = ModelBuilder().model_from_dict(schema, "ListModel")
    validated_data = Model(**data)
    assert validated_data.items == ["item1", "item2", "item3"]


def test_create_model_with_list_of_dicts():
    schema = {"items": [{"name": str}]}
    data = {"items": [{"name": "item1"}, {"name": "item2"}, {"name": "item3"}]}
    Model = ModelBuilder().model_from_dict(schema, "ListDictModel")
    validated_data = Model(**data)
    assert validated_data.items[0].name == "item1"
    assert validated_data.items[1].name == "item2"
    assert validated_data.items[2].name == "item3"


def test_create_model_with_nested_lists():
    schema = {"items": [{"name": str, "quantity": int}]}
    data = {"items": [{"name": "item1", "quantity": 5}, {"name": "item2", "quantity": 10}]}
    Model = ModelBuilder().model_from_dict(schema, "NestedListsModel")
    validated_data = Model(**data)
    assert validated_data.items[0].name == "item1"
    assert validated_data.items[0].quantity == 5
    assert validated_data.items[1].name == "item2"
    assert validated_data.items[1].quantity == 10


def test_create_model_with_any_type():
    schema = {"value": Any}
    Model = ModelBuilder().model_from_dict(schema, "AnyTypeModel")

    for input_value in [123, "abc", [1, 2, 3], {"key": "value"}]:
        validated_data = Model(value=input_value)
        assert validated_data.value == input_value


# JSON Schema Tests
def test_create_model_from_json_schema():
    json_schema = {
        "name": "JsonSchemaModel",
        "description": "A model created from JSON schema",
        "parameters": {
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        },
    }
    Model = ModelBuilder().model_from_json_schema(json_schema)
    validated_data = Model(name="example name", age=30)
    assert validated_data.name == "example name"
    assert validated_data.age == 30


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
    Model = ModelBuilder().model_from_json_schema(json_schema)
    data = {"name": "example name", "age": 30, "address": {"street": "123 Main St", "city": "Anytown"}}
    validated_data = Model(**data)
    assert validated_data.name == "example name"
    assert validated_data.age == 30
    assert validated_data.address.street == "123 Main St"
    assert validated_data.address.city == "Anytown"


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
    Model = ModelBuilder().model_from_json_schema(json_schema)
    valid_data = {"username": "user123", "age": 30}
    validated_data = Model(**valid_data)
    assert validated_data.username == "user123"
    assert validated_data.age == 30

    invalid_data = {"username": "us", "age": 17}
    with pytest.raises(ValidationError):
        Model(**invalid_data)


# Handling Extra Fields
def test_reject_extra_fields():
    schema = {"name": str, "age": int}
    data = {"name": "example name", "age": 30, "extra": "not allowed"}
    Model = ModelBuilder(base_model=TbmNoExtra).model_from_dict(schema, "RejectExtraFieldsModel")
    with pytest.raises(ValidationError):
        Model(**data)


def test_nested_model_reject_extra_fields():
    nested_schema = {"inner": {"name": str}}
    data = {"inner": {"name": "Inner Name", "extra": "not allowed"}}
    Model = ModelBuilder(base_model=TbmNoExtra).model_from_dict(nested_schema, "NestedRejectExtraModel")
    with pytest.raises(ValidationError):
        Model(**data)


# Miscellaneous Tests
def test_dynamic_schema_adaptation():
    schema_v1 = {"name": str}
    schema_v2 = {"name": str, "age": int}

    ModelV1 = ModelBuilder(base_model=TbmNoExtra).model_from_dict(schema_v1, "DynamicModelV1")
    ModelV2 = ModelBuilder().model_from_dict(schema_v2, "DynamicModelV2")

    validated_data_v1 = ModelV1(name="example name")
    assert validated_data_v1.name == "example name"

    validated_data_v2 = ModelV2(name="example name", age=30)
    assert validated_data_v2.name == "example name"
    assert validated_data_v2.age == 30

    with pytest.raises(ValidationError):
        ModelV1(name="example name", age=30)


def test_create_model_kwargs_in_function_signature():
    def example_function(**kwargs):
        pass

    ModelBuilder().model_from_function(example_function)
    assert True  # Ensure no exception is raised


def test_schema_with_boolean_field():
    schema = {"is_active": bool}
    Model = ModelBuilder().model_from_dict(schema, "BooleanFieldModel")
    validated_data_true = Model(is_active=True)
    validated_data_false = Model(is_active=False)
    assert validated_data_true.is_active is True
    assert validated_data_false.is_active is False


def test_create_model_with_various_field_names_and_types():
    schema = {"field1": str, "field2": int, "field3": float, "field4": bool, "field5": date}
    data = {"field1": "string_value", "field2": 123, "field3": 456.78, "field4": True, "field5": "2023-01-01"}
    Model = ModelBuilder().model_from_dict(schema, "VariousFieldNamesAndTypesModel")
    validated_data = Model(**data)
    assert validated_data.field1 == "string_value"
    assert validated_data.field2 == 123
    assert validated_data.field3 == 456.78
    assert validated_data.field4 is True
    assert validated_data.field5 == date(2023, 1, 1)







def test_nested_data_to_schema_back_to_model_and_validate():
    from tooldantic.models import GenericBaseModel


    data = {'inners': [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]}
    model_builder = ModelBuilder(base_model=GenericBaseModel)
    schema_from_data = model_builder.model_from_dict(data, 'NestedModel').model_json_schema()
    ModelFromSchema = model_builder.model_from_json_schema(schema_from_data, "NestedModel")
    validated_data = ModelFromSchema(**data)
    assert validated_data.inners[0].name == 'Alice'
    

def test_map_json_type_to_python_with_format():
    import pydantic, datetime
    model_builder = ModelBuilder()
    details_email = {
        "type": "string",
        "format": "email"
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details_email, "email_field", "TestModel", False
    )
    assert field_type == pydantic.EmailStr

    details_uri = {
        "type": "string",
        "format": "uri"
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details_uri, "uri_field", "TestModel", False
    )
    assert field_type == pydantic.AnyUrl

    details_datetime = {
        "type": "string",
        "format": "date-time"
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details_datetime, "datetime_field", "TestModel", False
    )
    assert field_type == datetime.datetime

    details_date = {
        "type": "string",
        "format": "date"
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details_date, "date_field", "TestModel", False
    )
    assert field_type == datetime.date
