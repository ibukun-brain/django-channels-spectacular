# Payload types

`@document_action` and `@document_event` both accept a `payload` argument.
Four formats are supported.

## `None` (no schema)

```python
@document_action(summary="Ping")
async def handle_ping(self, content):
    ...
```

Produces no `payload` block in the spec. A discriminator `action` / `type`
constant is still injected.

## `dict` (raw JSON Schema)

Pass a dict and it is used verbatim as the JSON Schema fragment.

```python
@document_action(
    summary="Request a ride",
    payload={
        "type": "object",
        "properties": {
            "pickup": {"$ref": "#/components/schemas/LatLng"},
            "fare": {"type": "string", "format": "decimal"},
        },
        "required": ["pickup", "fare"],
    },
)
async def handle_request_ride(self, content):
    ...
```

## `@dataclass` class

The generator inspects `__dataclass_fields__` and converts each field's
type annotation to a JSON Schema property.

```python
from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal

@dataclass
class RequestRidePayload:
    pickup_lat: float
    pickup_lng: float
    fare: Decimal
    payment_method: str
    ride_id: UUID | None = None  # Optional → not in `required`

@document_action(summary="Request a ride", payload=RequestRidePayload)
async def handle_request_ride(self, content):
    ...
```

### Type mapping

| Python type | JSON Schema |
|-------------|------------|
| `str` | `{"type": "string"}` |
| `int` | `{"type": "integer"}` |
| `float` | `{"type": "number"}` |
| `bool` | `{"type": "boolean"}` |
| `Decimal` | `{"type": "string", "format": "decimal"}` |
| `UUID` | `{"type": "string", "format": "uuid"}` |
| `list[T]` | `{"type": "array", "items": <T-schema>}` |
| `T \| None` / `Optional[T]` | `<T-schema>` (field omitted from `required`) |
| Nested `@dataclass` | Recursive `{"type": "object", ...}` |

## DRF `Serializer` subclass

Requires the `drf` extra (`pip install django-channels-spectacular[drf]`).

The generator calls `get_fields()` on the serializer and maps each field
to a JSON Schema property.

```python
from rest_framework import serializers

class RequestRideSerializer(serializers.Serializer):
    pickup_lat = serializers.FloatField()
    pickup_lng = serializers.FloatField()
    fare = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=["cash", "card", "wallet"])

@document_action(summary="Request a ride", payload=RequestRideSerializer)
async def handle_request_ride(self, content): ...
```

Supported DRF fields: `CharField`, `UUIDField`, `IntegerField`, `FloatField`,
`DecimalField`, `BooleanField`, `DateField`, `DateTimeField`,
`ChoiceField` (mapped to `enum`), `ListField`, and nested `Serializer`.

## Pydantic `BaseModel`

No extra dependency required when Pydantic is already installed.

```python
from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal

class RequestRidePayload(BaseModel):
    pickup_lat: float
    pickup_lng: float
    fare: Decimal
    payment_method: str

@document_action(summary="Request a ride", payload=RequestRidePayload)
async def handle_request_ride(self, content): ...
```

Pydantic v2 is introspected via `model_json_schema()`; v1 via `schema()`.
