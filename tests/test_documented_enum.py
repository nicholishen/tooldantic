# test_documented_enum.py
import re
from enum import Enum
from typing import Optional, Tuple

import pytest

# Import the module instead of the class
import tooldantic.documented_enum as documented_enum


def test_enum_member_creation():
    class Status(documented_enum.DocumentedEnum):
        '''Return status for operation. Possible values:\n{options}'''
        SUCCESS = "SUCCESS", "Operation completed successfully."
        ERROR = "ERROR", "Operation failed."
        NOT_FOUND = "NOT_FOUND", "Resource not found."

    assert Status.SUCCESS.value == "SUCCESS"
    assert Status.SUCCESS.__doc__ == "Operation completed successfully."
    assert Status.ERROR.value == "ERROR"
    assert Status.ERROR.__doc__ == "Operation failed."
    assert Status.NOT_FOUND.value == "NOT_FOUND"
    assert Status.NOT_FOUND.__doc__ == "Resource not found."


def test_docstring_generation_with_placeholder():
    class Status(documented_enum.DocumentedEnum):
        '''Return status for operation. Possible values:\n{options}'''
        SUCCESS = "SUCCESS", "Operation completed successfully."
        ERROR = "ERROR", "Operation failed."
        NOT_FOUND = "NOT_FOUND", "Resource not found."

    expected_doc = (
        "Return status for operation. Possible values:\n"
        "'SUCCESS': Operation completed successfully.\n"
        "'ERROR': Operation failed.\n"
        "'NOT_FOUND': Resource not found."
    )
    assert Status.__doc__ == expected_doc


def test_docstring_generation_without_placeholder():
    class SimpleEnum(documented_enum.DocumentedEnum):
        '''A simple enumeration without placeholders.'''
        OPTION_A = "A", "Description for option A."
        OPTION_B = "B", "Description for option B."

    expected_doc = (
        "A simple enumeration without placeholders.\nValid options:\n"
        "'A': Description for option A.\n"
        "'B': Description for option B."
    )
    assert SimpleEnum.__doc__ == expected_doc


def test_placeholder_replacement_at_various_positions():
    # Placeholder at the beginning
    class BeginPlaceholderEnum(documented_enum.DocumentedEnum):
        '''{options} are the available options.'''
        FIRST = "FIRST", "First option."
        SECOND = "SECOND", "Second option."

    expected_doc_begin = "{0} are the available options.".format(
        "\n".join(f"'{member.value}': {member.__doc__}" for member in BeginPlaceholderEnum)
    )
    assert BeginPlaceholderEnum.__doc__ == expected_doc_begin

    # Placeholder in the middle
    class MiddlePlaceholderEnum(documented_enum.DocumentedEnum):
        '''Available options:\n{options}\nPlease choose one.'''
        ONE = "ONE", "First choice."
        TWO = "TWO", "Second choice."

    expected_doc_middle = (
        "Available options:\n"
        "'ONE': First choice.\n"
        "'TWO': Second choice.\n"
        "Please choose one."
    )
    assert MiddlePlaceholderEnum.__doc__ == expected_doc_middle

    # Placeholder at the end
    class EndPlaceholderEnum(documented_enum.DocumentedEnum):
        '''Choose an option:\n{options}'''
        X = "X", "Option X."
        Y = "Y", "Option Y."

    expected_doc_end = (
        "Choose an option:\n"
        "'X': Option X.\n"
        "'Y': Option Y."
    )
    assert EndPlaceholderEnum.__doc__ == expected_doc_end


def test_multiple_placeholders_raise_error():
    with pytest.raises(ValueError) as exc_info:
        class InvalidEnumMultiplePlaceholders(documented_enum.DocumentedEnum):
            '''First placeholder {options1} and second placeholder {options2}.'''
            ITEM1 = "ITEM1", "First item."
            ITEM2 = "ITEM2", "Second item."

    assert "Only one placeholder is allowed for enum options in the `InvalidEnumMultiplePlaceholders` docstring." in str(
        exc_info.value)


def test_invalid_placeholder_identifier():
    with pytest.raises(ValueError) as exc_info:
        class InvalidEnumPlaceholderIdentifier(documented_enum.DocumentedEnum):
            '''Options: {opt!ons}'''
            ITEM1 = "ITEM1", "First item."
            ITEM2 = "ITEM2", "Second item."

    assert "Invalid placeholder identifier '{opt!ons}' in the `InvalidEnumPlaceholderIdentifier` docstring." in str(
        exc_info.value)


def test_no_docstring():
    class NoDocEnum(documented_enum.DocumentedEnum):
        ITEM1 = "ITEM1", "First item."
        ITEM2 = "ITEM2", "Second item."

    expected_doc = (
        "\nValid options:\n"
        "'ITEM1': First item.\n"
        "'ITEM2': Second item."
    )
    assert NoDocEnum.__doc__ == expected_doc


def test_docstring_with_escaped_braces():
    class EscapedBracesEnum(documented_enum.DocumentedEnum):
        '''Options with braces: {{ not a placeholder }}\n{options}'''
        ALPHA = "ALPHA", "Alpha option."
        BETA = "BETA", "Beta option."

    expected_doc = (
        "Options with braces: { not a placeholder }\n"
        "'ALPHA': Alpha option.\n"
        "'BETA': Beta option."
    )
    assert EscapedBracesEnum.__doc__ == expected_doc


def test_enum_members_iteration():
    class IterEnum(documented_enum.DocumentedEnum):
        FIRST = "FIRST", "First member."
        SECOND = "SECOND", "Second member."

    members = list(IterEnum)
    assert len(members) == 2
    assert members[0] is IterEnum.FIRST
    assert members[1] is IterEnum.SECOND


def test_docstring_with_multiple_braces():
    class MultipleBracesEnum(documented_enum.DocumentedEnum):
        '''Options with multiple braces: {{not a placeholder}} and {options}'''
        ITEM1 = "ITEM1", "First item."
        ITEM2 = "ITEM2", "Second item."

    expected_doc = (
        "Options with multiple braces: {not a placeholder} and "
        "'ITEM1': First item.\n"
        "'ITEM2': Second item."
    )
    assert MultipleBracesEnum.__doc__ == expected_doc


def test_docstring_with_braces_and_special_characters():
    class BracesSpecialCharsEnum(documented_enum.DocumentedEnum):
        '''Options with special characters: {{not a placeholder}} and {options}'''
        ITEM1 = "ITEM1", "First item."
        ITEM2 = "ITEM2", "Second item."

    expected_doc = (
        "Options with special characters: {not a placeholder} and "
        "'ITEM1': First item.\n"
        "'ITEM2': Second item."
    )
    assert BracesSpecialCharsEnum.__doc__ == expected_doc


def test_docstring_with_braces_and_numbers():
    class BracesNumbersEnum(documented_enum.DocumentedEnum):
        '''Options with numbers: {{not a placeholder}} and {options}'''
        ITEM1 = "ITEM1", "First item."
        ITEM2 = "ITEM2", "Second item."

    expected_doc = (
        "Options with numbers: {not a placeholder} and "
        "'ITEM1': First item.\n"
        "'ITEM2': Second item."
    )
    assert BracesNumbersEnum.__doc__ == expected_doc


def test_placeholder_with_underscores():
    class PlaceholderWithUnderscoresEnum(documented_enum.DocumentedEnum):
        '''Available choices:\n{valid_options}'''
        YES = "YES", "Affirmative."
        NO = "NO", "Negative."

    expected_doc = (
        "Available choices:\n"
        "'YES': Affirmative.\n"
        "'NO': Negative."
    )
    assert PlaceholderWithUnderscoresEnum.__doc__ == expected_doc


def test_placeholder_with_numeric_identifier():
    class PlaceholderWithNumericEnum(documented_enum.DocumentedEnum):
        '''Options list:\n{options1}'''
        ONE = "ONE", "First option."
        TWO = "TWO", "Second option."

    expected_doc = (
        "Options list:\n"
        "'ONE': First option.\n"
        "'TWO': Second option."
    )
    assert PlaceholderWithNumericEnum.__doc__ == expected_doc


def test_placeholder_with_mixed_characters():
    class PlaceholderMixedCharEnum(documented_enum.DocumentedEnum):
        '''List of options:\n{option_list}'''
        A = "A", "Option A."
        B = "B", "Option B."

    expected_doc = (
        "List of options:\n"
        "'A': Option A.\n"
        "'B': Option B."
    )
    assert PlaceholderMixedCharEnum.__doc__ == expected_doc


def test_class_without_subclassing():
    # Ensure that DocumentedEnum itself does not process __init_subclass__
    original_doc = documented_enum.DocumentedEnum.__doc__
    assert documented_enum.DocumentedEnum.__doc__ == original_doc


def test_subclass_without_description():
    class NoDescriptionEnum(documented_enum.DocumentedEnum):
        '''Enum without descriptions:\n{options}'''
        ITEM1 = "ITEM1", ""
        ITEM2 = "ITEM2", ""

    expected_doc = (
        "Enum without descriptions:\n"
        "'ITEM1': \n"
        "'ITEM2': "
    )
    assert NoDescriptionEnum.__doc__ == expected_doc


def test_enum_with_no_members_and_placeholder():
    class NoMembersWithPlaceholder(documented_enum.DocumentedEnum):
        '''No options available:\n{options}'''

    expected_doc = "No options available:\n"
    assert NoMembersWithPlaceholder.__doc__ == expected_doc
    assert list(NoMembersWithPlaceholder) == []


def test_placeholder_with_whitespace():
    with pytest.raises(ValueError) as exc_info:
        class PlaceholderWithWhitespaceEnum(documented_enum.DocumentedEnum):
            '''Options:\n{ options }'''
            ITEM1 = "ITEM1", "First item."

    assert "Invalid placeholder identifier '{ options }' in the `PlaceholderWithWhitespaceEnum` docstring." in str(
        exc_info.value)


def test_placeholder_with_special_characters():
    with pytest.raises(ValueError) as exc_info:
        class PlaceholderWithSpecialCharEnum(documented_enum.DocumentedEnum):
            '''Options:\n{opt#ions}'''
            ITEM1 = "ITEM1", "First item."

    assert "Invalid placeholder identifier '{opt#ions}' in the `PlaceholderWithSpecialCharEnum` docstring." in str(
        exc_info.value)


def test_class_with_no_placeholder_but_formatted_string():
    class NoPlaceholderFormattedEnum(documented_enum.DocumentedEnum):
        '''Options list:\n{0}'''
        ITEM1 = "ITEM1", "First item."
        ITEM2 = "ITEM2", "Second item."

    # Since {0} is already present, it should replace {0} with the options
    expected_doc = (
        "Options list:\n"
        "'ITEM1': First item.\n"
        "'ITEM2': Second item."
    )
    assert NoPlaceholderFormattedEnum.__doc__ == expected_doc


def test_enum_with_unicode_characters():
    class UnicodeEnum(documented_enum.DocumentedEnum):
        '''Unicode options:\n{options}'''
        ALPHA = "α", "Alpha in Greek."
        BETA = "β", "Beta in Greek."

    expected_doc = (
        "Unicode options:\n"
        "'α': Alpha in Greek.\n"
        "'β': Beta in Greek."
    )
    assert UnicodeEnum.__doc__ == expected_doc
