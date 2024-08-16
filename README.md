# Introduction to Tooldantic

This document provides an introduction to the `tooldantic` library, a powerful tool designed to optimize schema handling when integrating Large Language Models (LLMs) into Python applications.

### Why Tooldantic?
Integrating LLMs with Python can be challenging, especially when it comes to data schema generation and validation. While `pydantic` is excellent for general-purpose data handling, it has limitations when used with LLMs. Here are some key issues:

- **Schema Order Inconsistency**: LLMs are could be sensitive to the order of keys in JSON schemas, but `pydantic` doesn't ensure consistent key order, which could affect model performance.
- **Complex Schema Structures**: `Pydantic` often generates schemas with references and definitions (`refs` and `defs`), which are unfamiliar to LLMs trained on simpler, inline schemas. This mismatch can lead to errors or inefficiencies.
- **Inefficient Token Usage**: Redundant elements in schemas waste tokens and computational resources, increasing costs and potentially reducing model efficiency.

### Four Ways to Create Pydantic Models
`Tooldantic` extends Pydantic's capabilities by providing four key methods for creating models:
1. **Pydantic Classes**: Using `tooldantic` as a drop-in replacement for `pydantic.BaseModel`.
2. **Functions**: Creating dynamic models based on function annotations.
3. **Raw Data Dictionaries**: Generating models directly from raw data.
4. **JSON Schemas**: Building models from JSON schema definitions.

Let’s dive into how `tooldantic` works and why it might be a better fit for your LLM-based applications.

## Creating a Basic Model with Tooldantic

Start by creating a simple model using `tooldantic`. This library acts as a drop-in replacement for `pydantic.BaseModel`, allowing you to define models in the same way while taking advantage of the optimizations `tooldantic` provides.

```python
import tooldantic
import pydantic
import json


class MyModel(tooldantic.ToolBaseModel):
    """This is a test model"""

    name: str
    age: int
    is_student: bool

# This ToolBaseModel subclass model is a subclass of pydantic.BaseModel
assert issubclass(MyModel, pydantic.BaseModel)
# The Field function is from pydantic and available to be imported from tooldantic for convenience
assert tooldantic.Field is pydantic.Field
```

**Output**:
```python
MyModel(name='John', age=20, is_student=True)
```

### Inspecting Nested Models in Pydantic

Before exploring `tooldantic`, take a look at how `pydantic` handles nested models. Understanding this will help you appreciate the improvements that `tooldantic` offers.

```python
from pydantic import BaseModel


class InnerModel(BaseModel):
    """nested inner model"""

    inner_value: int = 1


class OuterModel(BaseModel):
    """outer model with inner model"""

    inner_model: InnerModel


schema_pd = json.dumps(OuterModel.model_json_schema(), indent=2)
print(schema_pd[:550])
```

**Output**:
```json
{
  "$defs": {
    "InnerModel": {
      "description": "nested inner model",
      "properties": {
        "inner_value": {
          "default": 1,
          "title": "Inner Value",
          "type": "integer"
        }
      },
      "title": "InnerModel",
      "type": "object"
    }
  },
  "description": "outer model with inner model",
  "properties": {
    "inner_model": {
      "$ref": "#/$defs/InnerModel"
    }
  },
  "required": [
    "inner_model"
  ],
  "title": "OuterModel",
  "type": "object"
}
```

As you can see, `pydantic` splits the schema into definitions and references. While this structure is fine for APIs, it creates issues when working with LLMs, which expect simpler, inline schemas. This is where `tooldantic` comes in.

## Nested Models with Tooldantic

Now, let's see how `tooldantic` improves on `pydantic` when it comes to handling nested models. Define similar nested models and inspect the generated schema to see the differences.

```python
# drop in replacement for pydantic.BaseModel
from tooldantic import ToolBaseModel as BaseModel


class InnerModel(BaseModel):
    """nested inner model"""

    inner_value: int = 1


class OuterModel(BaseModel):
    """outer model with inner model"""

    inner_model: InnerModel


schema_td = json.dumps(OuterModel.model_json_schema(), indent=2)
print(schema_td)
```

**Output**:
```json
{
  "type": "object",
  "description": "outer model with inner model",
  "properties": {
    "inner_model": {
      "type": "object",
      "description": "nested inner model",
      "properties": {
        "inner_value": {
          "type": "integer",
          "default": 1
        }
      }
    }
  },
  "required": [
    "inner_model"
  ],
  "title": "OuterModel"
}
```

Three significant improvements occurred here:
1. **Inline Schema**: The schema was inlined, avoiding unnecessary references and better matching the format that LLMs expect.
2. **Consistent Field Order**: The order of fields was preserved, which is crucial for consistent tokenization and model performance.
3. **Token Efficiency**: Redundant elements were removed, reducing token usage and making the schema more efficient for LLM processing.

## Token Efficiency Comparison

One of the key advantages of `tooldantic` is its efficient use of tokens. In this example, compare the number of tokens used by schemas generated with `pydantic` versus `tooldantic`.

```python
import tiktoken
encoding = tiktoken.encoding_for_model('gpt-4o')
pd_tokens = len(encoding.encode(schema_pd))
td_tokens = len(encoding.encode(schema_td))
print(f'Pydantic tokens: {pd_tokens}')
print(f'Tooldantic tokens: {td_tokens}')
print(f'Token savings %: {100*(pd_tokens-td_tokens)/pd_tokens:.2f}%')
```

**Output**:
```
Pydantic tokens: 142
Tooldantic tokens: 100
Token savings %: 29.58%
```

## **~30% Token Savings!**

The results show a significant token savings when using `tooldantic`—around 30%. This translates directly into cost savings, which is crucial when working with LLMs that charge based on token usage.

## Dynamic Model Creation from Functions

`Tooldantic` also allows you to create dynamic models from annotated functions. In this example, generate a schema from a function's parameters and see how `tooldantic` simplifies this process.

```python
def my_model_function(name: str, age: int, is_student: bool):
    """This is a test model"""
    ...


MyModel2 = td.ModelBuilder().create_model_from_function(
    my_model_function, model_name="MyModel"
)

# The schema derived from the function is the same as the schema derived from the class
assert MyModel2.model_json_schema() == MyModel.model_json_schema()


@tooldantic.tool(name="MyModel")
def my_model_function_wrapped(name: str, age: int, is_student: bool):
    """This is a test model"""
    ...

# The schema derived from the wrapped function is the same as the schema derived from the class
assert my_model_function_wrapped.Model.model_json_schema() == MyModel.model_json_schema()
```

Let’s review what just happened:
1. A dynamic model was created directly from an annotated function.
2. This feature is especially useful when you need to generate models on-the-fly based on function signatures.

## Dynamic Function Creation with Tooldantic

`Tooldantic` allows you to dynamically create and execute functions, which can be especially powerful when working with generated or external code. Let’s see how it works.

```python
# !!! DON'T USE THIS. IT IS FOR CONCEPTUAL DEMONSTRATION PURPOSES ONLY !!!
import sys, types

llm_created_tool = """\
def get_weather(location: str, date: str):
    return {"location": location, "date": date}
"""


def import_code_as_module(code_text, module_name="temp_module"):
    """This function imports python text (str) code and returns a live virtual module"""
    import_code_as_module.counter = getattr(import_code_as_module, "counter", 0) + 1
    unique_module_name = f"{module_name}_{import_code_as_module.counter}"
    module = types.ModuleType(unique_module_name)
    exec(code_text, module.__dict__)
    sys.modules[unique_module_name] = module
    return module

virtual_module = import_code_as_module(llm_created_tool)
new_tool = td.tool(virtual_module.get_weather)
print(f'schema={new_tool.Model.model_json_schema()}')
print(f'func returns={new_tool(location="New York", date="2022-01-01")}')
```

***Output***
```
schema={'type': 'object', 'description': '', 'properties': {'location': {'type': 'string'}, 'date': {'type': 'string'}}, 'required': ['location', 'date'], 'title': 'get_weather'}
func returns={'location': 'New York', 'date': '2022-01-01'}
```

We now have a pathway for dynamically creating functions without needing to know the implementation details ahead of time. This is particularly useful in scenarios where functions need to be generated on-the-fly.

## Handling Validation Errors

What happens when the dynamically created function is called with incorrect arguments? Let’s see how `tooldantic` helps catch and handle validation errors effectively.

```python
try:
    new_tool(location="New York")
except pd.ValidationError as e:
    print(td.validation_error_to_llm_feedback(e))
```

**Output**:

```json
{"success": false, "message_to_assistant": "Please pay close attention to the following pydantic errors and use them to correct your tool inputs.", "errors": [{"type": "missing", "loc": "('date',)", "msg": "Field required", "input": {"location": "New York"}}]}
```

### Using Functional Validators with Pydantic

Functional validators allow for custom validation logic within `pydantic` models. In the following example, see how to use these validators to enforce specific rules, such as disallowing certain values.

```python
from typing import Annotated

# Define a custom validator
def name_validator(name):
    if name.lower() == 'nick':
        raise ValueError("No Nick's allowed!")
    return name

@td.tool
def say_hello(name: Annotated[str, pd.AfterValidator(name_validator)]): # pass the validator in the annotation
    return f"Hello {name}!"

try:
    say_hello(name="Nick") # call it with a forbidden name
except pd.ValidationError as e:
    print(td.validation_error_to_llm_feedback(e)) # Value error, No Nick's allowed!
```

**Output**:
```
{"success": false, "message_to_assistant": "Please pay close attention to the following pydantic errors and use them to correct your tool inputs.", "errors": [{"type": "value_error", "loc": "('name',)", "msg": "Value error, No Nick's allowed!", "input": "Nick", "ctx": {"error": "No Nick's allowed!"}}]}
```

## Dynamic Model Creation from Data

`Tooldantic` also allows you to create models dynamically based on a data dictionary. This is useful when working with external or variable data sources. Let’s see how it's done.

```python
example_data = {"name": "John", "age": 20, "is_student": True}
MyModel3 = td.ModelBuilder().create_model_from_schema_dict(
    example_data, model_name="MyModel", model_description="This is a test model"
)

# The schema derived from the example data is the same as the schema derived from the class and the function
assert MyModel3.model_json_schema() == MyModel.model_json_schema()
```

Not only can models be dynamically built from raw data, but developers can also use this capability to rapidly iterate on schema designs. This flexibility can save significant development time.

## Creating Models from Schema Dictionaries

In addition to data dictionaries, `tooldantic` can create models directly from schema dictionaries. This approach is particularly useful when dealing with predefined schemas or when working with external data sources.

```python
example_data = {"name": "John", "age": 20, "is_student": True}
MyModel3 = td.ModelBuilder().create_model_from_schema_dict(
    example_data, model_name="MyModel", model_description="This is a test model"
)

# The schema derived from the example data is the same as the schema derived from the class and the function
assert MyModel3.model_json_schema() == MyModel.model_json_schema()
```

### Note: Compatibility with Pydantic

These models are fully compatible with any framework that uses `pydantic` models. Here are a few things to note about the generated schema:
- The date field is automatically recognized and formatted.
- The schema is concise and ready for use in various applications.


### JSON Schemas to Models

Another powerful feature of `tooldantic` is the ability to create models from deserialized JSON schemas. This allows for dynamic model creation based on external JSON schema definitions.

```python
schema_pd = {
    "type": "object",
    "description": "This is a test model",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "is_student": {"type": "boolean"},
    },
    "required": ["name", "age", "is_student"],
    "title": "MyModel",
}

MyModel4 = td.ModelBuilder().create_model_from_json_schema(schema_pd)
print(type(MyModel4))
# Yup, it's a subclass of pydantic.BaseModel
assert issubclass(MyModel4, pd.BaseModel)
try:
    MyModel4(**example_data)
except pd.ValidationError as e:
    # The example data is valid for the schema indicating that the model was correctly built from the schema
    assert False, e

try:
    MyModel4(**{**example_data, "age": "twenty"})
except pd.ValidationError as e:
    # The example data is invalid for the schema indicating that the model was correctly built from the schema
    assert True
```

### Why Create Models from LLM JSON Schemas?

Datasets, whether custom-built or existing, are often described by JSON schemas. By leveraging these schemas, you can create models that ensure data adheres to expected formats, preventing inconsistencies and errors during model training or inference.

## Validating Data Against a Schema

In this example, validate ground truth data against a dynamically created model to identify any inconsistencies or errors in the dataset. This is crucial for maintaining data integrity.

```python
ground_truth_in_dataset = {
    "name": "John",
    "age": 20,
    "is_student": "NA", # Simulate a human error in the ground truth data see BFCLB github issues for examples
}

json_schema_in_dataset = {
    "title": "some_tool",
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "is_student": {"type": "boolean"}, # This should cause validation to fail since is_student is not a boolean in the ground truth
    },
    "required": ["name", "age", "is_student"],
}

DynamicModel = td.ModelBuilder().create_model_from_json_schema(json_schema_in_dataset)

try:
    DynamicModel(**ground_truth_in_dataset)
except pd.ValidationError as e:
    # The ground truth data is invalid for the schema indicating that the model was correctly built from the schema
    # We've successfully detected a human error in the ground truth data
    assert True
```

## Synthetic Data Creation Pipeline

Let’s say you have some target data and want to train a model to extract similar features. Use `tooldantic` in a simple pipeline to create synthetic data for training, starting from the target data alone.

```python
some_data_that_requires_fine_tuning = [
    {
        "name": "John",
        "age": 20,
        "is_student": False,
    }
]

import openai

dataset = []

for data in some_data_that_requires_fine_tuning:
    data_row = {}
    data_row["ground_truth"] = data
    DynamicModel = td.ModelBuilder().create_model_from_schema_dict(
        data,
        "data_extraction_tool",
        "Use this tool to extract target data from unstructured legal documents",
    )
    data_row["model_json_schema_in"] = DynamicModel.model_json_schema()
    r = openai.OpenAI().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You generate mock unstructured legal documents from "
                "user supplied JSON schemas and example JSON outputs. The goal is to "
                "produce a document that would be very difficult to parse, but could plausibly"
                "represent the unstructured text source from which the JSON was extracted.",
            },
            {
                "role": "user",
                "content": json.dumps(data_row),
            },
        ],
    )
    data_row["unstructured_text"] = r.choices[0].message.content
    dataset.append(data_row)
dataset
```

**Output**:
```json
[
  {
    "ground_truth": {
      "name": "John",
      "age": 20,
      "is_student": false
    },
    "model_json_schema_input": {
      "description": "Use this tool to extract target data from unstructured legal documents",
      "properties": {
        "name": {
          "title": "Name",
          "type": "string"
        },
        "age": {
          "title": "Age",
          "type": "integer"
        },
        "is_student": {
          "title": "Is Student",
          "type": "boolean"
        }
      },
      "required": [
        "name",
        "age",
        "is_student"
      ],
      "title": "data_extraction_tool",
      "type": "object"
    },
    "unstructured_text": "**Case Reference: [ABC-2023-001] In the Matter of..."
  }
]
```

### Synthetic Data and Fine-Tuning

The synthetic data generated in this pipeline can be used for fine-tuning models, helping improve their performance on specific tasks or datasets. This approach is particularly valuable when working with limited or imbalanced datasets.


### Next Steps
- Experiment with the examples provided here on your own data.
- Explore the [Tooldantic documentation](link-to-docs) for more advanced features.
- Consider combining `tooldantic` with other libraries to further optimize your LLM workflows.
