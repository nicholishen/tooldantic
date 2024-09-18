
import json
import pydantic
from tooldantic import validation_error_to_llm_feedback, is_type_or_annotation

def test_validation_error_to_llm_feedback():
    class SampleModel(pydantic.BaseModel):
        name: str
        age: int

    try:
        SampleModel(name=123, age="twenty")
    except pydantic.ValidationError as e:
        feedback = validation_error_to_llm_feedback(e)
        feedback_dict = json.loads(feedback)
        assert feedback_dict['success'] == False
        assert 'SYSTEM' in feedback_dict
        assert len(feedback_dict['errors']) == 2
        assert feedback_dict['errors'][0]['type'] == 'string_type'
        assert feedback_dict['errors'][1]['type'] == 'int_parsing'

def test_is_type_or_annotation():
    from typing import List, Union, Annotated, Optional
    assert is_type_or_annotation(str) == True
    assert is_type_or_annotation(int) == True
    assert is_type_or_annotation(Union[str, int]) == True
    assert is_type_or_annotation(List[str]) == True
    assert is_type_or_annotation(Annotated[str, "description"]) == True
    assert is_type_or_annotation(Optional[int]) == True
    assert is_type_or_annotation(42) == False
    assert is_type_or_annotation("string") == False
    assert is_type_or_annotation(None) == False
    assert is_type_or_annotation(...) == False
