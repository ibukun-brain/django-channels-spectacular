# API Reference

## Decorators

### `document_action`

```python
from channels_spectacular import document_action

@document_action(
    summary: str = "",
    description: str = "",
    payload = None,
    responses: dict | None = None,
    tags: list[str] | None = None,
    action: str | None = None,
    deprecated: bool = False,
)
```

Marks a consumer method as a **client → server** action.

| Parameter | Type | Description |
|-----------|------|-------------|
| `summary` | `str` | Short human-readable description shown in the viewer sidebar |
| `description` | `str` | Extended Markdown description |
| `payload` | see [Payload types](payload-types) | Incoming message schema |
| `responses` | `{event_type: payload}` | Events the server emits in response |
| `examples` | `list[dict] \| None` | Concrete message examples (see below) |
| `tags` | `list[str]` | Groups the operation in the sidebar |
| `action` | `str` \| `None` | Override the inferred action name (`handle_` stripped) |
| `deprecated` | `bool` | Marks the operation deprecated in the spec |

---

### `document_event`

```python
from channels_spectacular import document_event

@document_event(
    event_type: str,
    summary: str = "",
    description: str = "",
    payload = None,
    tags: list[str] | None = None,
    deprecated: bool = False,
)
```

Marks a consumer method as a **server → client** event handler.

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_type` | `str` | The dotted event type string, e.g. `"ride.offer"` |
| `summary` | `str` | Short description |
| `description` | `str` | Extended Markdown description |
| `payload` | see [Payload types](payload-types) | Outbound message schema |
| `examples` | `list[dict] \| None` | Concrete message examples (see below) |
| `tags` | `list[str]` | Groups the operation in the viewer |
| `deprecated` | `bool` | Marks the operation deprecated |

### Examples format

Each entry in the `examples` list is a dict with:

| Key | Required | Description |
|-----|----------|-------------|
| `name` | no | Short label shown in the viewer (e.g. `"Cash payment"`) |
| `summary` | no | One-line description of the example |
| `payload` | yes | Dict of concrete field values |

```python
examples=[
    {
        "name": "Cash payment",
        "summary": "Rider pays with cash at destination",
        "payload": {
            "action": "request_ride",
            "pickup_lat": 6.5244,
            "pickup_lng": 3.3792,
            "fare": "1500.00",
            "payment_method": "cash",
        },
    },
    {
        "name": "Card payment",
        "payload": {
            "action": "request_ride",
            "fare": "1800.00",
            "payment_method": "card",
        },
    },
]
```

Examples are passed through verbatim into the AsyncAPI `messages[name].examples`
field — no validation or transformation is applied.

---

## `AsyncAPIGenerator`

```python
from channels_spectacular import AsyncAPIGenerator

# Single consumer
generator = AsyncAPIGenerator(
    consumer_class,
    info: dict | None = None,
    servers: dict | None = None,
    channel_path: str | None = None,
)

# Multiple consumers
generator = AsyncAPIGenerator(
    consumers: list[tuple[type, str]],
    info: dict | None = None,
    servers: dict | None = None,
)
```

A low-level generator. Use this when you need the spec as a Python object or
YAML string outside of a Django request.

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_spec()` | `dict` | Full AsyncAPI 3.0 spec as a Python dict |
| `get_yaml()` | `str` | YAML-serialized spec string |

---

## Views

### `AsyncAPISpecView`

```
GET /ws-docs/asyncapi.yaml
```

Returns the AsyncAPI spec as `application/yaml`.

**Class attributes** (all override `CHANNELS_SPECTACULAR_SETTINGS`):

| Attribute | Type | Description |
|-----------|------|-------------|
| `consumer` | `type \| None` | Single annotated consumer class |
| `consumers` | `list[(type, str)] \| None` | Multiple `(consumer, channel_path)` pairs |
| `info` | `dict \| None` | AsyncAPI `info` object override |
| `servers` | `dict \| None` | AsyncAPI `servers` block override |
| `channel_path` | `str \| None` | WebSocket path for the single-consumer case |

Either `consumer` or `consumers` must be set; passing neither raises `ValueError`.

---

### `AsyncAPIDocView`

```
GET /ws-docs/
```

Renders the HTML page hosting the AsyncAPI React viewer.

**Class attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `spec_url` | `str \| None` | URL of the YAML spec (single-consumer case). Defaults to `<path>/asyncapi.yaml` |
| `specs` | `list[(label, url)] \| None` | Multi-consumer mode: renders a switcher dropdown. Takes precedence over `spec_url` |
| `template_name` | `str` | Override to provide a custom HTML template |

---

## Management command

See [Export command](export-command) for the full `export_asyncapi` reference.
