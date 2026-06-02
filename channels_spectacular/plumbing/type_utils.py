"""
Python type annotation → JSON Schema fragment mapping.

Only the types that commonly appear in WebSocket message payloads are
handled. Unknown types fall back to ``{}`` (any) rather than raising,
so a partially-annotated payload still produces a useful schema.
"""

from __future__ import annotations

import types
import typing
from dataclasses import MISSING
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from decimal import Decimal
from typing import Any, Union, get_args, get_origin
from uuid import UUID

# Python 3.10+ unions written as ``X | Y`` have origin ``types.UnionType``
# (3.11-3.13); 3.14 reports ``typing.Union``, handled by the ``Union`` check.
_UNION_TYPE = getattr(types, "UnionType", None)


def python_type_to_schema(tp: Any) -> dict:
    """
    Convert a single Python type to a JSON Schema dict.

    Args:
        tp: A Python type, e.g. ``str``, ``int``, ``list[str]``,
            ``UUID``, or a nested ``@dataclass``.

    Returns:
        A JSON Schema fragment such as ``{"type": "string"}`` or
        ``{"type": "array", "items": {"type": "string"}}``.
        Returns ``{}`` for unrecognised types.
    """
    origin = get_origin(tp)
    args = get_args(tp)

    # Optional[X] / X | None / Union[X, None] → unwrap to just X.
    # A true multi-type union becomes anyOf.
    is_union = origin is Union or (
        _UNION_TYPE is not None and origin is _UNION_TYPE
    )
    if is_union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return python_type_to_schema(non_none[0])
        return {"anyOf": [python_type_to_schema(a) for a in non_none]}

    # list[T] / List[T]
    if origin in (list, typing.List):  # noqa: UP006
        item_args = get_args(tp)
        items = python_type_to_schema(item_args[0]) if item_args else {}
        return {"type": "array", "items": items}

    # dict / dict[K, V] / Dict[K, V]
    # Plain `dict` has origin=None, so check tp directly as well.
    if tp is dict or origin in (dict, typing.Dict):  # noqa: UP006
        return {"type": "object"}

    _PRIMITIVE_MAP: dict[type, dict] = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        Decimal: {"type": "string", "format": "decimal"},
        UUID: {"type": "string", "format": "uuid"},
        bytes: {"type": "string", "format": "binary"},
    }
    if tp in _PRIMITIVE_MAP:
        return _PRIMITIVE_MAP[tp]

    # Nested dataclass → recurse
    if is_dataclass(tp) and isinstance(tp, type):
        return dataclass_to_schema(tp)

    return {}


def dataclass_to_schema(cls: type) -> dict:
    """
    Convert a ``@dataclass`` class to a JSON Schema object.

    Args:
        cls: A dataclass *class* (not an instance).

    Returns:
        ``{"type": "object", "properties": {...}, "required": [...]}``
    """
    try:
        hints = typing.get_type_hints(cls)
    except Exception:
        hints = {f.name: f.type for f in dataclass_fields(cls)}

    properties: dict[str, dict] = {}
    required: list[str] = []

    for field in dataclass_fields(cls):
        tp = hints.get(field.name, Any)
        properties[field.name] = python_type_to_schema(tp)

        # Required = no default value AND not Optional.
        no_default = (
            field.default is MISSING
            and field.default_factory is MISSING  # type: ignore[misc]
        )
        if no_default:
            origin = get_origin(tp)
            args = get_args(tp)
            is_optional = (
                origin is Union
                or (_UNION_TYPE is not None and origin is _UNION_TYPE)
            ) and type(None) in args
            if not is_optional:
                required.append(field.name)

    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema
