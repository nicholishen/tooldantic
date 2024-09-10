import datetime
import inspect
import logging
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

import docstring_parser
import pydantic
from pydantic import BaseModel, Field, create_model

from .models import ToolBaseModel
from .utils import ModelT, ToolError, _Empty, _Unset, is_type_or_annotation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CONSTRAINTS_MAP = {
    "minLength": "min_length",
    "maxLength": "max_length",
    "maxItems": "max_length",
    "minItems": "min_length",
    "minimum": "ge",
    "maximum": "le",
    "multipleOf": "multiple_of",
    "pattern": "pattern",
}


class ModelBuilder(BaseModel):

    base_model: Type[BaseModel] = ToolBaseModel
    default_type_for_none: Type = Any
    is_set_defaults_from_values: bool = False
    is_parse_docstrings: bool = False

    def model_from_function(
        self,
        func: Callable[..., Any],
        model_name: Optional[str] = None,
        model_description: Optional[str] = None,
        is_parse_docstrings: bool = False,
    ) -> Type[ModelT]:
        if self.is_parse_docstrings or is_parse_docstrings:
            docstring = docstring_parser.parse(func.__doc__)
            docstring = {
                p.arg_name: {
                    "description": p.description,
                    "type_name": (
                        f"typing.Optional[{p.type_name}]"
                        if p.is_optional
                        else p.type_name
                    ),
                }
                for p in docstring.params
            }
            model_description = model_description or docstring.get("description")
        else:
            docstring = {}
        signature = inspect.signature(func)
        fields = {}
        for name, param in signature.parameters.items():
            if name in ("self", "cls") and param.annotation is _Empty:
                continue
            annotation = (
                docstring.get(name, {}).get("type_name")
                if param.annotation is _Empty
                else param.annotation
            )
            if annotation is None:
                # allow kwargs in tools!
                if param.kind == param.VAR_KEYWORD:
                    continue
                message = f"Parameter `{name}` in function `{func.__name__}` has no annotation or docstring type."
                raise ToolError(message)
            if param.default is not _Empty:
                default = param.default
            elif (
                docstring_default := docstring.get(name, {}).get("default") is not None
            ):
                default = docstring_default
            else:
                default = _Empty
            processed_field = self._process_field(
                field_name=name,
                annotation=annotation,
                default=default,
                model_name=model_name or func.__name__,
                use_defaults=True,  # Always use defaults from function parameters
            )
            if processed_field == (_Empty, ...):
                message = f"Parameter `{name}` in function `{func.__name__}` has no annotation or default value."
                raise ToolError(message)
            fields[name] = processed_field

        model_name = model_name or func.__name__
        model_description = model_description or func.__doc__

        return self._create_pydantic_model(model_name, fields, model_description)

    def model_from_dict(
        self,
        schema_dict: Dict[str, Any],
        model_name: str,
        model_description: Optional[str] = None,
        is_set_defaults_from_values: bool = False,
        is_set_descriptions_from_str_values: bool = False,
    ) -> Type[ModelT]:
        logger.debug(f"Creating model from schema dict: {model_name}")
        fields = {}
        for name, value in schema_dict.items():
            processed_field = self._process_field(
                field_name=name,
                annotation=_Empty,
                default=value,
                model_name=model_name,
                use_defaults=is_set_defaults_from_values,  # Never use defaults from schema dict
                use_descriptions=is_set_descriptions_from_str_values,
            )
            fields[name] = processed_field
        logger.debug(f"Processed fields from schema dict: {fields}")
        return self._create_pydantic_model(model_name, fields, model_description)

    def model_from_json_schema(
        self, schema: Dict[str, Any], model_name: Optional[str] = None
    ) -> Type[ModelT]:
        # TODO: Add support for nested models with `$ref` and `definitions`
        logger.debug("Creating model from JSON schema")
        name, description, parameters = self._extract_schema_details(schema)
        logger.debug(
            f"Extracted schema details: name={name}, description={description}, parameters={parameters}"
        )
        model_name = model_name or name
        if parameters is None:
            raise ValueError("No parameters found in the schema.")
        if "$defs" in parameters:
            raise NotImplementedError(
                "Nested models and schemas with '$defs' are not supported yet. "
                "Try using inlined schema."
            )
        fields = self._parse_parameters(parameters, model_name)
        logger.debug(f"Processed fields from JSON schema: {fields}")
        return self._create_pydantic_model(
            model_name=model_name, model_description=description or None, fields=fields
        )

    def _extract_schema_details(self, schema: Dict[str, Any]) -> Tuple[str, str, Dict]:
        logger.debug(f"Extracting schema details from: {schema}")

        def find_keys(schema_part, keys, result=None):
            if result is None:
                result = {}
            for key in keys:
                if key in schema_part:
                    result[key] = schema_part[key]
            if len(result) < len(keys):
                for value in schema_part.values():
                    if isinstance(value, dict):
                        deeper_result = find_keys(value, keys, result)
                        result.update(deeper_result)
            return result

        title_or_name = "title" if "title" in schema else "name"
      
        inner_schema = "schema" if "json_schema" in schema else "parameters"
     
        keys_to_find = [title_or_name, "description", inner_schema]
        found = find_keys(schema, keys_to_find)
        if "schema" in found:
            found['parameters'] = found.pop('schema')
        if "parameters" not in found:
            found["parameters"] = schema
        logger.debug(f"Found keys: {found}")
        return (
            found.get(title_or_name),
            found.get("description"),
            found.get("parameters"),
        )

    def _parse_parameters(
        self, parameters: Dict[str, Any], parent_model_name: str
    ) -> Dict[str, Any]:
        logger.debug(
            f"Parsing parameters: {parameters} for parent model: {parent_model_name}"
        )
        fields = {}
        required_fields = parameters.get("required", [])
        if "properties" in parameters:
            for field_name, details in parameters["properties"].items():
                field_type, field_default = self._map_json_type_to_python(
                    details,
                    field_name,
                    parent_model_name,
                    field_name in required_fields,
                )
                fields[field_name] = (field_type, field_default)
        logger.debug(f"Parsed fields: {fields}")
        return fields

    def _map_json_type_to_python(
        self,
        details: Dict[str, Any],
        field_name: str,
        parent_model_name: str,
        is_required: bool,
    ) -> Tuple[Union[Type, Any], pydantic.fields.FieldInfo]:
        logger.debug(
            f"Mapping JSON type to Python for field: {field_name} with details: {details}"
        )

        json_type = details.get("type", Any)
        default = details.get("default", ...)
        examples = details.get("examples", _Unset)
        format = details.get("format")

        constraints = {
            v: details[k] for k, v in CONSTRAINTS_MAP.items() if k in details
        }
        format_map = {
            "date": datetime.date,
            "date-time": datetime.datetime,
            "email": pydantic.EmailStr,
            "uri": pydantic.AnyUrl,
        }
        field_info = Field(
            default=default,
            description=details.get("description"),
            examples=examples,
            **constraints,
        )
        if json_type == "string":
            if "enum" in details:
                enums = details["enum"]
                return Literal.__getitem__(tuple(enums)), field_info
            if format is not None and format in format_map:
                return format_map[format], field_info
            return str, field_info
        elif json_type == "integer":
            return int, field_info
        elif json_type == "number":
            return float, field_info
        elif json_type == "boolean":
            return bool, field_info
        elif json_type == "array":
            item_details = details.get("items", {})
            item_type, _ = self._map_json_type_to_python(
                item_details, f"{field_name}_item", parent_model_name, True
            )
            return List[item_type], field_info
        elif json_type == "object":
            model_name = f"{parent_model_name}_{field_name.capitalize()}"
            nested_fields = self._parse_parameters(details, model_name)
            nested_model = create_model(model_name, **nested_fields)
            return nested_model, field_info
        return Any, field_info

    def _create_pydantic_model(
        self,
        model_name: str,
        fields: Dict[str, Tuple],
        model_description: Optional[str],
    ) -> Type[ModelT]:
        logger.debug(
            f"Creating Pydantic model: {model_name} with fields: {fields} and description: {model_description}"
        )
        # This fixes the issue where a description is passed as None and other dynamically
        # derived models retain the __doc__ of the previous model. Pydantic bug???
        # We need to set it to string with a \s to avoid inadvertently misguiding the LLM with a default Model description.
        # TODO: Submit to Pydantic to fix this?
        model_description = (
            model_description or " "
        )  # f"Model for {model_name}" DO NOT DELETE THIS FIX - IT IS IMPORTANT
        return pydantic.create_model(
            model_name,
            __base__=self.base_model,
            __doc__=model_description,
            **fields,
        )

    def _process_field(
        self,
        field_name: str,
        model_name: str,
        annotation: Union[Type, _Empty, None],
        default: Any = _Empty,
        use_defaults: Optional[bool] = None,
        use_descriptions: Optional[bool] = None,
    ) -> Tuple[Type, Any]:
        logger.debug(
            f"Processing field: {field_name} in model: {model_name} with annotation: {annotation} and default: {default}"
        )

        # use_defaults = (
        #     self.is_set_defaults_from_values if use_defaults is None else use_defaults
        # )
        effective_default = ... if default is _Empty else default
        if not use_defaults:
            effective_default = ...
        if use_descriptions and isinstance(default, str):
            effective_default = Field(description=default)

        logger.debug(
            f"Effective default for field: {field_name} is: {effective_default}"
        )

        if annotation is _Empty:
            annotation, default = self._handle_empty_annotation(
                default, model_name, field_name
            )
            if annotation is str and use_descriptions:
                default = effective_default
            logger.debug(
                f"Handled empty annotation for field: {field_name}, resulting annotation: {annotation}, default: {default}"
            )

        if isinstance(annotation, dict):
            logger.debug(f"Interpreting schema dict for field: {field_name}")
            return self._interpret_schema_dict(field_name, annotation)

        if isinstance(effective_default, dict):
            logger.debug(
                f"Interpreting schema dict for field: {field_name} with default as dict"
            )
            return self._interpret_schema_dict(field_name, effective_default)

        if self._is_list_type(annotation):
            logger.debug(f"Field: {field_name} is a list type")
            return self._handle_list_type(annotation), effective_default

        elif isinstance(effective_default, list):
            logger.debug(f"Default for field: {field_name} is a list")
            return (
                self._handle_list_default(effective_default, model_name),
                effective_default,
            )

        if self._is_annotated_type(annotation):
            logger.debug(f"Field: {field_name} is an annotated type")
            return self._interpret_annotated_type(annotation, effective_default)

        logger.debug(
            f"Processed field: {field_name} with annotation: {annotation}, default: {effective_default}"
        )
        return (annotation or type(effective_default)), effective_default

    def _handle_empty_annotation(self, default, model_name, field_name):
        logger.debug(
            f"Handling empty annotation for field: {field_name} in model: {model_name} with default: {default}"
        )
        if default is None:
            return self.default_type_for_none, default
        elif is_type_or_annotation(default):
            return default, ...
        elif isinstance(default, dict):
            return (
                self.model_from_dict(
                    default, f"{model_name}_{field_name.capitalize()}"
                ),
                ...,
            )
        elif isinstance(default, list):
            return self._handle_list_default(default, model_name), ...
        else:
            return type(default), default if self.is_set_defaults_from_values else ...

    def _is_list_type(self, annotation):
        return isinstance(annotation, list) or get_origin(annotation) is list

    def _handle_list_type(self, annotation):
        logger.debug(f"Handling list type annotation: {annotation}")
        item_type = (
            annotation[0] if isinstance(annotation, list) else get_args(annotation)[0]
        )
        return List[item_type]

    def _handle_list_default(self, default, model_name):
        logger.debug(
            f"Handling list default for model: {model_name} with default: {default}"
        )
        if not default:
            return List[Any]
        item = default[0]
        if isinstance(item, dict):
            return List[self.model_from_dict(item, model_name=f"{model_name}_Item")]
        item_type = item if is_type_or_annotation(item) else type(item)
        return List[item_type]

    def _is_annotated_type(self, annotation):
        return get_origin(annotation) is Annotated

    def _interpret_annotated_type(self, annotation, default):
        logger.debug(f"Interpreting annotated type: {annotation}")
        field_type, *metadata = get_args(annotation)
        if all(isinstance(meta, str) for meta in metadata):
            return field_type, Field(
                default, description=metadata[0], examples=metadata[1:] or None
            )
        return annotation, default

    def _interpret_schema_dict(self, field_name, value):
        logger.debug(
            f"Interpreting schema dict for field: {field_name} with value: {value}"
        )
        nested_model_name = f"{field_name.capitalize()}_Model"
        nested_model = self.model_from_dict(value, nested_model_name)
        return nested_model, ...
