import pytest
import pydantic
from tooldantic.decorators import AsyncToolWrapper
from tooldantic.dispatch import ToolDispatch
from tooldantic.models import OpenAiBaseModel

BASE_MODEL = OpenAiBaseModel

def get_weather(location: str) -> str:
    """Use this tool to get the weather in a specific location"""
    return f"The weather in {location} is sunny."

def get_sports_scores(team: str) -> str:
    """Use this tool to get the latest scores for a specific team"""
    return f"The latest scores for {team} are..."

def used_name(x: int):
    return x

async def async_tool(x: int):
    return x

@pytest.fixture
def tools():
    return ToolDispatch(get_weather, get_sports_scores, base_model=BASE_MODEL)

def test_get_sports_scores(tools):
    assert tools["get_sports_scores"]('{"team": "Manchester United"}') == "The latest scores for Manchester United are..."

def test_get_sports_scores_validation_error(tools):
    with pytest.raises(pydantic.ValidationError):
        tools["get_sports_scores"]('{"team": null}')

def test_rename_tool(tools):
    tools['x'] = used_name
    assert tools['x'](x=1) == 1
    assert tools['x']('{"x":1}') == 1
    assert tools['x'].name == 'x'
    assert list(tools.schemas)[-1]['function']['name'] == 'x'

def test_tool_dispatch_union():
    tools = ToolDispatch(get_weather, get_sports_scores, base_model=BASE_MODEL)
    other_tools = ToolDispatch(used_name, base_model=BASE_MODEL, __doc__="OTHER_TOOLS")
    new_tools = tools | other_tools
    new_tools['x'] = async_tool
    assert len(list(new_tools.schemas)) == 4
    assert 'x' in new_tools
    func_disp = {**new_tools}
    assert len(func_disp) == 4
    assert 'x' in func_disp
    assert all(isinstance(x, dict) for x in tools.schemas)

def test_async_tool(tools):
    tools['async_tool'] = async_tool
    assert isinstance(tools['async_tool'], AsyncToolWrapper)
    
def test_tool_dispatch_pop():
    tools = ToolDispatch(get_weather, get_sports_scores, base_model=BASE_MODEL)
    tool = tools.pop('get_weather')
    assert tool.name == 'get_weather'
    assert 'get_weather' not in tools
    with pytest.raises(KeyError):
        tools.pop('get_weather')

def test_tool_dispatch_clear():
    tools = ToolDispatch(get_weather, get_sports_scores, base_model=BASE_MODEL)
    tools.clear()
    assert len(tools) == 0

def test_tool_dispatch_get():
    tools = ToolDispatch(get_weather, base_model=BASE_MODEL)
    tool = tools.get('get_weather', get_sports_scores)
    assert tool.name == 'get_weather'
    tool = tools.get('nonexistent', default=None)
    assert tool is None

def test_tool_dispatch_items():
    tools = ToolDispatch(get_weather, get_sports_scores, base_model=BASE_MODEL)
    items = list(tools.items())
    assert len(items) == 2
    assert items[0][0] == 'get_weather'
    assert items[1][0] == 'get_sports_scores'

def test_tool_dispatch_keys():
    tools = ToolDispatch(get_weather, get_sports_scores, base_model=BASE_MODEL)
    keys = list(tools.keys())
    assert keys == ['get_weather', 'get_sports_scores']

def test_tool_dispatch_values():
    tools = ToolDispatch(get_weather, get_sports_scores, base_model=BASE_MODEL)
    values = list(tools.values())
    assert len(values) == 2
    assert values[0].name == 'get_weather'
