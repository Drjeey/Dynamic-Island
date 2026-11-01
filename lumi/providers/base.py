"""What every chat provider gives Lumi: one conversation that streams text and asks for tools.

A provider's chat has one method, send(message, on_text) -> (text, calls):
  message  - the user's words (str), or the results of the last tool calls: [(ToolCall, result text), ...]
  on_text  - called with the reply so far each time more text arrives
  calls    - the tools the model wants run before it answers ([] once it has answered in words)
The chat keeps its own history in the provider's format; Lumi's tool loop (chat.py) is the same for all of them.
"""
import inspect
import typing
from dataclasses import dataclass

REQUEST_TIMEOUT = 60  # seconds without an answer before a request fails, so Lumi never waits forever
JSON_TYPES = {int: 'integer', float: 'number', str: 'string', bool: 'boolean'}


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict | None  # None when the model's arguments couldn't be read or don't fit the tool


class Declined(Exception):
    """The model declined to answer (a safety refusal), as opposed to failing."""


def tool_schemas(functions):
    """JSON schemas for Lumi's tools, built from each method's name, type hints and docstring."""
    schemas = []
    for f in functions:
        hints = typing.get_type_hints(f)
        properties, required = {}, []
        for name, param in inspect.signature(f).parameters.items():
            properties[name] = {'type': JSON_TYPES.get(hints.get(name), 'string')}
            if param.default is inspect.Parameter.empty:
                required.append(name)
        schemas.append({'name': f.__name__, 'description': inspect.getdoc(f) or '',
                        'parameters': {'type': 'object', 'properties': properties, 'required': required,
                                       'additionalProperties': False}})
    return schemas


def checked_args(schema, args):
    """The arguments if they fit the tool's schema (whole-number floats become ints), otherwise None.
    Unknown tools pass through unchanged so the tool runner can report them."""
    if schema is None:
        return dict(args) if isinstance(args, dict) else None
    if not isinstance(args, dict):
        return None
    properties, required = schema['parameters']['properties'], schema['parameters']['required']
    if set(args) - set(properties) or any(name not in args for name in required):
        return None
    checked = {}
    for name, value in args.items():
        kind = properties[name]['type']
        if kind == 'integer' and isinstance(value, float) and value.is_integer():
            value = int(value)
        fits = {'integer': isinstance(value, int) and not isinstance(value, bool),
                'number': isinstance(value, (int, float)) and not isinstance(value, bool),
                'string': isinstance(value, str),
                'boolean': isinstance(value, bool)}[kind]
        if not fits:
            return None
        checked[name] = value
    return checked
