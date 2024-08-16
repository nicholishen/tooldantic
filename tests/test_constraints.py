import typing
from typing import List

import pydantic
import pytest
from pydantic import Field, confloat, conint, conlist, constr

from tooldantic import ModelBuilder


@pytest.fixture
def model_builder():
    return ModelBuilder()


def get_metadata(field_info:pydantic.fields.FieldInfo):
    def get_meta_key_value(m):
        m_name = next((n for n in dir(m) if not n.startswith("_")), None)
        m_value = getattr(m, m_name) if m_name else None
        return m_name, m_value
    return {k: v for k, v in (get_meta_key_value(m) for m in field_info.metadata) if v is not None}

def test_get_metadata():
    field_info = Field(..., ge=1, le=100)
    metadata = get_metadata(field_info)
    assert metadata == {"ge": 1, "le": 100}

def test_string_constraints(model_builder):
    details = {
        "type": "string",
        "minLength": 2,
        "maxLength": 10,
        "pattern": "^[a-z]+$"
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details, "test_field", "TestModel", False
    )
    field_info_metadata = get_metadata(field_info)
    # assert False, f'field_info_metadata: {field_info_metadata} field_type: {field_type}'
    # assert field_type == constr(min_length=2, max_length=10, pattern="^[a-z]+$")
    # assert field_info_metadata['default'] is None  # Ensure default is None for non-required fields
    assert field_info_metadata['min_length'] == 2
    assert field_info_metadata['max_length'] == 10
    assert field_info_metadata['pattern']== "^[a-z]+$"

def test_integer_constraints(model_builder):
    details = {
        "type": "integer",
        "minimum": 1,
        "maximum": 100
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details, "test_field", "TestModel", True
    )
    assert field_type is int
    # assert field_info.default == ...  # Required field should have ellipsis as default
    # assert field_info.ge == 1
    # assert field_info.le == 100
    field_info_metadata = get_metadata(field_info)
    print(f'field_info_metadata: {field_info_metadata}')
    assert field_info_metadata['ge'] == 1
    assert field_info_metadata['le'] == 100

def test_float_constraints(model_builder):
    details = {
        "type": "number",
        "minimum": 0.5,
        "maximum": 9.5,
        "multipleOf": 0.1
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details, "test_field", "TestModel", True
    )
    assert field_type is float
    field_info_metadata = get_metadata(field_info)
    assert field_info_metadata['ge'] == 0.5
    assert field_info_metadata['le'] == 9.5
    assert field_info_metadata['multiple_of'] == 0.1
    # assert field_info.default == ...
    # assert field_info.ge == 0.5
    # assert field_info.le == 9.5
    # assert field_info.multiple_of == 0.1

def test_array_constraints(model_builder):
    details = {
        "type": "array",
        "minItems": 1,
        "maxItems": 10,
        "items": {"type": "integer"}
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details, "test_field", "TestModel", False
    )
    assert field_type == List[int]
    field_info_metadata = get_metadata(field_info)
    assert field_info_metadata['min_length'] == 1
    assert field_info_metadata['max_length'] == 10
    # assert field_info.min_length == 1
    # assert field_info.max_length == 10

def test_enum_constraints(model_builder):
    details = {
        "type": "string",
        "enum": ["a", "b", "c"]
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details, "test_field", "TestModel", False
    )
    assert field_type == typing.Literal['a', 'b', 'c']
    # assert field_info.default is None

def test_boolean_field(model_builder):
    details = {
        "type": "boolean"
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details, "test_field", "TestModel", True
    )
    assert field_type == bool
    # assert field_info.default is None  # Non-required boolean field should have None as default

# Required field should have ellipsis as default

def test_optional_field_default(model_builder):
    details = {
        "type": "string"
    }
    field_type, field_info = model_builder._map_json_type_to_python(
        details, "test_field", "TestModel", False
    )
    assert field_type == str
    # assert field_info.default is None  # Optional field should have None as default
