from typing import Any, Dict

from pydantic.json_schema import GenerateJsonSchema



class CompatibilitySchemaGenerator(GenerateJsonSchema):
    """
    Custom schema generator that:
        1. Inlines all references for LLM tools (resolves refs/defs).
        2. Reorders keys for LLM optimization.
        3. Removes redundant titles
    """

    key_order = (
        "name",
        "title",
        "type",
        "description",
        "strict",
        "format",
        "enum",
        "properties",
        "required",
        "items",
        "additionalProperties",
    )

    is_reordered_keys = False
    is_removed_titles = False
    is_inlined_refs = False
    is_apply_strict_rules = False

    def generate(self, schema, mode):
        json_schema = super().generate(schema, mode)
        title = json_schema.get("title")
        if self.is_apply_strict_rules:
            json_schema = self._ensure_strict_json_schema(json_schema, path=())
        if self.is_inlined_refs and "$defs" in json_schema:
            definitions = json_schema.pop("$defs")
            json_schema = self._inline_references(json_schema, definitions)
            json_schema = self._inline_all_of(json_schema)
        if self.is_reordered_keys:
            json_schema = self._reorder_keys(json_schema)
        if self.is_removed_titles:
            top_level_title = json_schema.pop("title", title)
            json_schema = self._remove_target_key(json_schema, "title")
            # This will get popped downstream and used as the name
            json_schema["title"] = top_level_title  
        return json_schema

    def _inline_references(self, schema, definitions, visited=None, parent=None):
        if visited is None:
            visited = set()

        if isinstance(schema, dict):
            for key, value in list(schema.items()):
                if key == "$ref":
                    ref_key = value.split("/")[-1]
                    if ref_key in visited:
                        # Directly reference the definition to indicate recursion simply.
                        schema[key] = "#"
                        continue
                    visited.add(ref_key)
                    if ref_key in definitions:
                        schema.update(definitions[ref_key])
                        schema.pop("$ref")
                    # Pass the current schema as parent to detect direct recursions
                    self._inline_references(schema, definitions, visited, schema)
                else:
                    schema[key] = self._inline_references(
                        value, definitions, visited, parent
                    )
        elif isinstance(schema, list):
            schema = [
                self._inline_references(item, definitions, visited, parent)
                for item in schema
            ]
        return schema

    def _reorder_keys(self, schema):
        if not isinstance(schema, dict):
            return schema
        ordered_dict = {k: schema.pop(k) for k in self.key_order if k in schema}
        # Add remaining keys
        ordered_dict.update({k: self._reorder_keys(v) for k, v in schema.items()})
        return {k: self._reorder_keys(v) for k, v in ordered_dict.items()}

    def _remove_target_key(self, schema, target_key="title"):
        if isinstance(schema, dict):
            new_dict = {}
            for key, value in schema.items():
                if key == target_key and isinstance(value, str):
                    continue  # Skip string titles
                new_dict[key] = self._remove_target_key(value, target_key)
            return new_dict
        elif isinstance(schema, list):
            return [self._remove_target_key(item, target_key) for item in schema]
        return schema

    def _inline_all_of(self, schema):
        """Inlines allOf schemas if the allOf list contains only one item."""
        if isinstance(schema, dict):
            if "allOf" in schema and len(schema["allOf"]) == 1:
                # Replace the allOf construct with its single contained schema
                inlined_schema = self._inline_all_of(schema["allOf"][0])
                # If the inlined schema is a dictionary, merge it with the current schema
                if isinstance(inlined_schema, dict):
                    schema.update(inlined_schema)
                    schema.pop("allOf")
                return schema
            # Recursively apply this method to all dictionary values
            for key, value in schema.items():
                schema[key] = self._inline_all_of(value)
        elif isinstance(schema, list):
            # Recursively apply this method to all items in the list
            return [self._inline_all_of(item) for item in schema]
        return schema

    def _ensure_strict_json_schema(
        self,
        json_schema: object,
        path: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Mutates the given JSON schema to ensure it conforms to the `strict` standard
        that the API expects.
        """
        if not isinstance(json_schema, dict):
            raise TypeError(f"Expected {json_schema} to be a dictionary; path={path}")

        typ = json_schema.get("type")
        if typ == "object" and "additionalProperties" not in json_schema:
            json_schema["additionalProperties"] = False

        # object types
        # { 'type': 'object', 'properties': { 'a':  {...} } }
        properties = json_schema.get("properties")
        if isinstance(properties, dict):
            json_schema["required"] = [prop for prop in properties.keys()]
            json_schema["properties"] = {
                key: self._ensure_strict_json_schema(
                    prop_schema, path=(*path, "properties", key)
                )
                for key, prop_schema in properties.items()
            }
        # arrays
        # { 'type': 'array', 'items': {...} }
        items = json_schema.get("items")
        if isinstance(items, list):
            json_schema["items"] = self._ensure_strict_json_schema(
                items, path=(*path, "items")
            )
        # unions
        any_of = json_schema.get("anyOf")
        if isinstance(any_of, list):
            json_schema["anyOf"] = [
                self._ensure_strict_json_schema(variant, path=(*path, "anyOf", str(i)))
                for i, variant in enumerate(any_of)
            ]
        # intersections
        all_of = json_schema.get("allOf")
        if isinstance(all_of, list):
            json_schema["allOf"] = [
                self._ensure_strict_json_schema(entry, path=(*path, "anyOf", str(i)))
                for i, entry in enumerate(all_of)
            ]
        defs = json_schema.get("$defs")
        if isinstance(defs, dict):  # is_dict(defs):
            for def_name, def_schema in defs.items():
                self._ensure_strict_json_schema(def_schema, path=(*path, "$defs", def_name))

        definitions = json_schema.get("definitions")
        if isinstance(definitions, dict):
            for definition_name, definition_schema in definitions.items():
                self._ensure_strict_json_schema(
                    definition_schema, path=(*path, "definitions", definition_name)
                )
        return json_schema


class GenericSchemaGenerator(CompatibilitySchemaGenerator):
    """
    Schema generator for generic functions, extending ParamsSchemaGenerator.
    """

    def generate(self, schema, mode):
        json_schema = super().generate(schema, mode)
        func_name = json_schema.pop("title", "function")
        func_description = json_schema.pop("description", "")
        tool_schema = {
            "name": func_name,
            "description": func_description,
            "parameters": json_schema,
        }
        return tool_schema


class GoogleSchemaGenerator(GenericSchemaGenerator):
    """
    Schema generator for Google functions, extending GenericFunctionSchemaGenerator.
    """

    def generate(self, schema, mode):
        json_schema = super().generate(schema, mode)
        json_schema = self._remove_target_key(json_schema, "default")
        return json_schema


class StrictBaseSchemaGenerator(CompatibilitySchemaGenerator):
    """
    Schema generator for OpenAI functions, extending GenericFunctionSchemaGenerator.
    """

    is_apply_strict_rules = True
    is_inlined_refs = True
    is_removed_titles = True
    is_reordered_keys = True

    def generate(self, schema, mode):
        json_schema = super().generate(schema, mode)
        func_name = json_schema.pop("title", "function")
        # if "description" not in json_schema:
        #     raise ValueError(f"Description/Docstring missing for {func_name}")
        func_description = json_schema.pop("description", "")
        tool_schema = {
            "name": func_name,
            "description": func_description,
            "strict": True,
            "parameters": json_schema,
        }

        return tool_schema


class OpenAiStrictSchemaGenerator(StrictBaseSchemaGenerator):
    """
    Schema generator for OpenAI functions, extending GenericFunctionSchemaGenerator.
    """

    is_inlined_refs = False  # OpenAI works with refs

    def generate(self, schema, mode):
        json_schema = super().generate(schema, mode)
        tool_schema = {
            "type": "function",
            "function": json_schema,
        }
        return tool_schema


class OpenAiResponseFormatGenerator(StrictBaseSchemaGenerator):
    """
    Schema generator for OpenAI functions, extending GenericFunctionSchemaGenerator.
    """

    def generate(self, schema, mode):
        json_schema = super().generate(schema, mode)
        json_schema["schema"] = json_schema.pop("parameters")
        tool_schema = {
            "type": "json_schema",
            "json_schema": json_schema,
        }
        return tool_schema


class OpenAiSchemaGenerator(OpenAiStrictSchemaGenerator):
    is_apply_strict_rules = False


class AnthropicSchemaGenerator(GenericSchemaGenerator):
    """
    Schema generator for Anthropic functions, extending GenericFunctionSchemaGenerator.
    """

    def generate(self, schema, mode):
        json_schema = super().generate(schema, mode)
        json_schema["input_schema"] = json_schema.pop("parameters")
        return json_schema
