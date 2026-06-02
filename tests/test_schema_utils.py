"""Tests for schema extraction (dataclass, DRF serializer, dict, None)."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

import pytest

from channels_spectacular.plumbing.schema_utils import extract_schema
from channels_spectacular.plumbing.type_utils import (dataclass_to_schema,
                                                      python_type_to_schema)


# ---------------------------------------------------------------------------
# extract_schema dispatch
# ---------------------------------------------------------------------------
class TestExtractSchema:
    def test_none_returns_empty(self):
        assert extract_schema(None) == {}

    def test_dict_returned_as_is(self):
        raw = {"type": "object", "properties": {"x": {"type": "string"}}}
        assert extract_schema(raw) is raw

    def test_dataclass_dispatched(self):
        @dataclass
        class Simple:
            name: str

        result = extract_schema(Simple)
        assert result["type"] == "object"
        assert "name" in result["properties"]

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError, match="Unsupported payload type"):
            extract_schema(int)

    def test_unsupported_instance_raises(self):
        with pytest.raises(TypeError):
            extract_schema("not a type")


# ---------------------------------------------------------------------------
# python_type_to_schema primitives
# ---------------------------------------------------------------------------

class TestPrimitiveTypes:
    @pytest.mark.parametrize("tp,expected", [
        (str, {"type": "string"}),
        (int, {"type": "integer"}),
        (float, {"type": "number"}),
        (bool, {"type": "boolean"}),
        (Decimal, {"type": "string", "format": "decimal"}),
        (UUID, {"type": "string", "format": "uuid"}),
        (bytes, {"type": "string", "format": "binary"}),
    ])
    def test_primitives(self, tp, expected):
        assert python_type_to_schema(tp) == expected

    def test_unknown_type_returns_empty(self):
        class Custom:
            pass
        assert python_type_to_schema(Custom) == {}

    def test_list_of_str(self):
        result = python_type_to_schema(list[str])
        assert result == {"type": "array", "items": {"type": "string"}}

    def test_list_bare(self):
        import typing
        result = python_type_to_schema(typing.List)  # noqa: UP006
        assert result == {"type": "array", "items": {}}

    def test_dict_type(self):
        result = python_type_to_schema(dict)
        assert result == {"type": "object"}

    def test_optional_unwraps(self):
        result = python_type_to_schema(Optional[str])
        assert result == {"type": "string"}

    def test_union_becomes_anyof(self):
        result = python_type_to_schema(str | int)
        assert "anyOf" in result
        assert {"type": "string"} in result["anyOf"]
        assert {"type": "integer"} in result["anyOf"]


# ---------------------------------------------------------------------------
# dataclass_to_schema
# ---------------------------------------------------------------------------

class TestDataclassToSchema:
    def test_simple_dataclass(self):
        @dataclass
        class Point:
            x: float
            y: float

        schema = dataclass_to_schema(Point)
        assert schema["type"] == "object"
        assert schema["properties"]["x"] == {"type": "number"}
        assert schema["properties"]["y"] == {"type": "number"}
        assert "x" in schema["required"]
        assert "y" in schema["required"]

    def test_optional_field_not_required(self):
        @dataclass
        class Item:
            name: str
            note: Optional[str] = None

        schema = dataclass_to_schema(Item)
        assert "name" in schema["required"]
        assert "note" not in schema["required"]

    def test_field_with_default_not_required(self):
        @dataclass
        class Config:
            mode: str = "default"

        schema = dataclass_to_schema(Config)
        assert "mode" not in schema.get("required", [])

    def test_nested_dataclass(self):
        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Inner

        schema = dataclass_to_schema(Outer)
        inner_schema = schema["properties"]["inner"]
        assert inner_schema["type"] == "object"
        assert "value" in inner_schema["properties"]

    def test_list_field(self):
        @dataclass
        class Collection:
            items: list[str]

        schema = dataclass_to_schema(Collection)
        assert schema["properties"]["items"] == {
            "type": "array",
            "items": {"type": "string"},
        }

    def test_uuid_field(self):
        @dataclass
        class Entity:
            id: UUID

        schema = dataclass_to_schema(Entity)
        assert schema["properties"]["id"] == {
            "type": "string",
            "format": "uuid",
        }

    def test_decimal_field(self):
        @dataclass
        class Price:
            amount: Decimal

        schema = dataclass_to_schema(Price)
        assert schema["properties"]["amount"] == {
            "type": "string",
            "format": "decimal",
        }


# ---------------------------------------------------------------------------
# DRF Serializer (skipped when DRF not installed)
# ---------------------------------------------------------------------------

drf = pytest.importorskip("rest_framework", reason="DRF not installed")


class TestDRFSerializer:
    def test_char_field(self):
        from rest_framework import serializers

        class S(serializers.Serializer):
            name = serializers.CharField()

        result = extract_schema(S)
        assert result["properties"]["name"] == {"type": "string"}
        assert "name" in result["required"]

    def test_optional_field_not_required(self):
        from rest_framework import serializers

        class S(serializers.Serializer):
            note = serializers.CharField(required=False)

        result = extract_schema(S)
        assert "note" not in result.get("required", [])

    def test_uuid_field(self):
        from rest_framework import serializers

        class S(serializers.Serializer):
            id = serializers.UUIDField()

        result = extract_schema(S)
        assert result["properties"]["id"] == {
            "type": "string",
            "format": "uuid",
        }

    def test_integer_field(self):
        from rest_framework import serializers

        class S(serializers.Serializer):
            count = serializers.IntegerField()

        result = extract_schema(S)
        assert result["properties"]["count"] == {"type": "integer"}

    def test_decimal_field(self):
        from rest_framework import serializers

        class S(serializers.Serializer):
            fare = serializers.DecimalField(max_digits=10, decimal_places=2)

        result = extract_schema(S)
        assert result["properties"]["fare"] == {
            "type": "string",
            "format": "decimal",
        }

    def test_choice_field_with_enum(self):
        from rest_framework import serializers

        class S(serializers.Serializer):
            status = serializers.ChoiceField(
                choices=["requested", "accepted", "completed"]
            )

        result = extract_schema(S)
        assert result["properties"]["status"]["enum"] == [
            "requested", "accepted", "completed"
        ]

    def test_nested_serializer(self):
        from rest_framework import serializers

        class Inner(serializers.Serializer):
            value = serializers.IntegerField()

        class Outer(serializers.Serializer):
            inner = Inner()

        result = extract_schema(Outer)
        inner_schema = result["properties"]["inner"]
        assert inner_schema["type"] == "object"
        assert "value" in inner_schema["properties"]

    def test_list_field(self):
        from rest_framework import serializers

        class S(serializers.Serializer):
            tags = serializers.ListField(child=serializers.CharField())

        result = extract_schema(S)
        assert result["properties"]["tags"] == {
            "type": "array",
            "items": {"type": "string"},
        }
