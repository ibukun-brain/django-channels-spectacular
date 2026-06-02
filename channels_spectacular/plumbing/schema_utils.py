"""
Convert a ``payload`` argument to a JSON Schema dict.

Accepted input forms
--------------------
* ``None`` → ``{}``
* ``dict`` → returned as-is (raw JSON Schema fragment)
* ``@dataclass`` class → via :func:`dataclass_to_schema`
* Pydantic ``BaseModel`` subclass → delegates to Pydantic's own
  ``model_json_schema()`` (v2) or ``schema()`` (v1), which are more
  accurate than anything we could reconstruct.
* DRF ``Serializer`` subclass → via :func:`serializer_to_schema`

Pydantic and DRF are optional dependencies.  Passing their types
without the library installed raises ``ImportError``.

Known limitation
----------------
Pydantic ``$defs`` references are returned as-is.  The caller
(:mod:`channels_spectacular.generator`) is responsible for hoisting
them into ``components.schemas`` if desired.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any

from channels_spectacular.plumbing.type_utils import dataclass_to_schema


def extract_schema(payload: Any) -> dict:
    """
    Convert *payload* to a JSON Schema dict.

    Args:
        payload: ``None``, a ``dict``, a ``@dataclass`` class, a
            Pydantic ``BaseModel`` subclass, or a DRF ``Serializer``
            subclass.

    Returns:
        A JSON Schema object fragment (``{}`` when *payload* is
        ``None``).

    Raises:
        TypeError: For any unsupported type.
    """
    if payload is None:
        return {}

    if isinstance(payload, dict):
        return payload

    if is_dataclass(payload) and isinstance(payload, type):
        return dataclass_to_schema(payload)

    pydantic_schema = _try_pydantic(payload)
    if pydantic_schema is not None:
        return pydantic_schema

    drf_schema = _try_drf(payload)
    if drf_schema is not None:
        return drf_schema

    raise TypeError(
        f"Unsupported payload type: {payload!r}. "
        "Expected None, dict, a @dataclass class, "
        "a Pydantic BaseModel subclass, "
        "or a DRF Serializer subclass."
    )


# ---------------------------------------------------------------------------
# Pydantic (optional)
# ---------------------------------------------------------------------------

def _try_pydantic(payload: Any) -> dict | None:
    """
    Return the Pydantic JSON Schema if *payload* is a ``BaseModel``
    subclass, else ``None``.

    Supports Pydantic v2 (``model_json_schema()``) and v1
    (``schema()``).  Both versions' ``$defs`` / ``definitions``
    blocks are returned unchanged.
    """
    try:
        from pydantic import BaseModel as _BM
    except ImportError:
        return None

    if not (isinstance(payload, type) and issubclass(payload, _BM)):
        return None

    # Pydantic v2
    if hasattr(payload, "model_json_schema"):
        return payload.model_json_schema()
    # Pydantic v1 fallback
    if hasattr(payload, "schema"):
        return payload.schema()

    return None


# ---------------------------------------------------------------------------
# DRF Serializer (optional)
# ---------------------------------------------------------------------------

def _try_drf(payload: Any) -> dict | None:
    """
    Return a JSON Schema dict if *payload* is a DRF ``Serializer``
    subclass, else ``None``.
    """
    try:
        from rest_framework.serializers import Serializer as _Serializer
    except ImportError:
        return None

    if isinstance(payload, type) and issubclass(payload, _Serializer):
        return serializer_to_schema(payload)

    return None


def serializer_to_schema(serializer_cls: type) -> dict:
    """
    Convert a DRF ``Serializer`` *class* to a JSON Schema object.

    Instantiates the serializer with no arguments to get its field
    list.

    Args:
        serializer_cls: A DRF ``Serializer`` subclass (not an
            instance).

    Returns:
        ``{"type": "object", "properties": {...}, "required": [...]}``
    """
    instance = serializer_cls()
    fields = instance.get_fields()

    properties: dict[str, dict] = {}
    required: list[str] = []

    for name, field in fields.items():
        properties[name] = _drf_field_to_schema(field)
        if field.required:
            required.append(name)

    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _drf_field_to_schema(field) -> dict:  # noqa: ANN001
    """Map a single DRF field instance to a JSON Schema fragment."""
    from rest_framework import serializers

    if isinstance(field, serializers.Serializer):
        return serializer_to_schema(type(field))

    if isinstance(field, serializers.ListSerializer):
        return {
            "type": "array",
            "items": _drf_field_to_schema(field.child),
        }

    if isinstance(field, serializers.ListField):
        items = _drf_field_to_schema(field.child) if field.child else {}
        return {"type": "array", "items": items}

    _MAP = {
        serializers.EmailField: {"type": "string", "format": "email"},
        serializers.URLField: {"type": "string", "format": "uri"},
        serializers.UUIDField: {"type": "string", "format": "uuid"},
        serializers.CharField: {"type": "string"},
        serializers.SlugField: {"type": "string"},
        serializers.RegexField: {"type": "string"},
        serializers.IPAddressField: {"type": "string", "format": "ipv4"},
        serializers.IntegerField: {"type": "integer"},
        serializers.FloatField: {"type": "number"},
        serializers.DecimalField: {"type": "string", "format": "decimal"},
        serializers.BooleanField: {"type": "boolean"},
        serializers.DateField: {"type": "string", "format": "date"},
        serializers.DateTimeField: {"type": "string", "format": "date-time"},
        serializers.TimeField: {"type": "string", "format": "time"},
        serializers.DurationField: {"type": "string"},
        serializers.FileField: {"type": "string", "format": "binary"},
        serializers.ImageField: {"type": "string", "format": "binary"},
        serializers.MultipleChoiceField: {
            "type": "array",
            "items": {"type": "string"},
        },
        serializers.ChoiceField: {"type": "string"},
        serializers.JSONField: {},
        serializers.DictField: {"type": "object"},
        serializers.HStoreField: {"type": "object"},
        serializers.SerializerMethodField: {},
    }

    for cls, fragment in _MAP.items():
        if isinstance(field, cls):
            if (
                isinstance(field, serializers.ChoiceField)
                and hasattr(field, "choices")
            ):
                choices = list(field.choices.keys())
                if all(isinstance(c, (str, int)) for c in choices):
                    return {**fragment, "enum": choices}
            return dict(fragment)

    if hasattr(serializers, "PrimaryKeyRelatedField") and isinstance(
        field, serializers.PrimaryKeyRelatedField
    ):
        return {"type": "string"}

    return {}
