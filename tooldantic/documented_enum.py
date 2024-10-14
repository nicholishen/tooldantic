import re
from typing import Optional, Tuple
from enum import Enum


class DocumentedEnum(str, Enum):
    """
    DocumentedEnum is a subclass of str and Enum that allows for the creation of enumerations with associated descriptions.
    It also automatically generates a formatted class-level docstring that includes all valid options and their descriptions.
    Example:
        Define a new enumeration with descriptions and a templatized docstring:
        ```python
        class Status(DocumentedEnum):
            '''Return status for operation. Possible values:\n{options}'''
            SUCCESS = "SUCCESS", "Operation completed successfully."
            ERROR = "ERROR", "Operation failed."
            NOT_FOUND = "NOT_FOUND", "Resource not found."
        print(Status.__doc__)
        ```
        This will output:
        ```
        Return status for operation. Possible values:
        'SUCCESS': Operation completed successfully.
        'ERROR': Operation failed.
        'NOT_FOUND': Resource not found.
        ```
    """

    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.__doc__ = description
        return obj

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        doc_fmt = cls.__doc__ or ""
        bounds = cls._find_placeholder_bounds(doc_fmt)
        if bounds:
            # Replace placeholder with {0} so it can be any identifier
            doc_fmt = doc_fmt[: bounds[0]] + "{0}" + doc_fmt[bounds[1] :]
        else:
            doc_fmt += "\n\nValid options:\n{0}"
        cls.__doc__ = doc_fmt.format(
            "\n".join(f"'{member.value}': {member.__doc__}" for member in cls)
        )

    @classmethod
    def _find_placeholder_bounds(cls, template: str) -> Optional[Tuple[int, int]]:
        """Finds the start and end indices of a template variable like {options}"""
        # Regex to match brace template variables, ignoring double braces (ie. '{{')
        pattern = re.compile(r"(?<!\{)(?:\{\{)*(\{[^{}]*\})(?:\}\})*(?!\})")
        placeholders = list(pattern.finditer(template))
        if len(placeholders) > 1:
            raise ValueError(
                f"Only one placeholder is allowed for enum options in the `{cls.__name__}` docstring. "
                f"Found {len(placeholders)} in '{doc_fmt}'"
            )
        if placeholders:
            identifier = placeholders[0].group(1)
            if not re.match(r"\w*$", identifier.strip("{}")):
                raise ValueError(
                    f"Invalid placeholder identifier '{identifier}' in the `{cls.__name__}` docstring. "
                    f"Only alphanumerics and underscores are allowed."
                )
            return placeholders[0].start(1), placeholders[0].end(1)
        return None
