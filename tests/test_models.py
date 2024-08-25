import pytest
from pydantic import ValidationError

from tooldantic.models import (
    ToolBaseModel,
    OpenAiBaseModel,
    OpenAiStrictBaseModel,
    OpenAiResponseFormatBaseModel,
    AnthropicBaseModel,
    GoogleBaseModel,
    GenericBaseModel,
)

# Sample model definitions for testing
def test_tool_base_model():
    assert hasattr(ToolBaseModel, "schema_generator")