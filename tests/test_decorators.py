

from tooldantic import ToolWrapper

def test_tool_wrapper_as_method():
    class MyClass:
        @ToolWrapper
        def my_method(self, x: int) -> int:
            """Multiply x by 2"""
            return x * 2

    instance = MyClass()
    result = instance.my_method(x=3)
    assert result == 6
