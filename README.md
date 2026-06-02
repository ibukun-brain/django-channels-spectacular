# django-channels-spectacular

[![PyPI](https://img.shields.io/pypi/v/django-channels-spectacular.svg?v=2)](https://pypi.org/project/django-channels-spectacular/)
[![License: BSD-3](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)
[![CI](https://github.com/ibukun-brain/django-channels-spectacular/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/ibukun-brain/django-channels-spectacular/actions/workflows/ci.yml)
[![Docs](https://readthedocs.org/projects/django-channels-spectacular/badge/?version=latest)](https://django-channels-spectacular.readthedocs.io)
[![Coverage](https://codecov.io/gh/ibukun-brain/django-channels-spectacular/branch/master/graph/badge.svg)](https://codecov.io/gh/ibukun-brain/django-channels-spectacular)

AsyncAPI 3.0 documentation generator for Django Channels WebSocket consumers.

Think of it as drf-spectacular for Django Channels: annotate your consumer's action handlers once and the package generates and serves the spec automatically. No more hand-maintaining YAML that slowly drifts out of sync with your actual implementation.

---

## Features

- **Decorator-based annotation:** `@document_action` / `@document_event` on consumer methods
- **Multi-consumer specs:** merge several consumers into one spec or serve them separately with a built-in switcher dropdown
- **Hand-written YAML support:** render existing AsyncAPI templates via `manage.py export_asyncapi --template`
- **Interactive try-it-out panel:** connect, send, and observe messages directly in the docs browser
- **DRF / Pydantic / dataclass payload introspection:** no hand-written schemas needed
- **AsyncAPI 3.0:** compliant spec rendered via the official `@asyncapi/react-component`

---

## Installation

```bash
pip install django-channels-spectacular
# or
uv add django-channels-spectacular
```

With DRF serializer support:

```bash
pip install "django-channels-spectacular[drf]"
uv add "django-channels-spectacular[drf]"
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "daphne",
    ...
    "channels",
    "channels_spectacular",
]
```

---

## Quick start

### 1. Annotate your consumer

```python
# myapp/consumers.py
from channels_spectacular import document_action, document_event

class DispatchConsumer(AsyncJsonWebsocketConsumer):

    @document_action(
        summary="Request a ride",
        payload=RequestRideSerializer,   # DRF, Pydantic, dataclass, or dict
        responses={"ride.requested": {"ride_id": "uuid"}},
        tags=["rides"],
        examples=[
            {
                "name": "Cash payment",
                "summary": "Rider pays with cash",
                "payload": {
                    "action": "request_ride",
                    "pickup_lat": 6.5244,
                    "pickup_lng": 3.3792,
                    "fare": "1500.00",
                    "payment_method": "cash",
                },
            },
        ],
    )
    async def handle_request_ride(self, content):
        ...

    @document_action(summary="Accept an offer", payload=AcceptOfferSerializer)
    async def handle_accept_offer(self, content):
        ...

    @document_event(
        "ride.offer",
        summary="Offer pushed to driver",
        payload=RideOfferSerializer,
        examples=[
            {
                "name": "Standard offer",
                "payload": {
                    "type": "ride.offer",
                    "ride_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                    "fare": "1500.00",
                    "driver_name": "Emeka",
                },
            },
        ],
    )
    async def ride_offer(self, event):
        ...

    @document_event("ride.accepted", summary="Ride accepted by driver")
    async def ride_accepted(self, event):
        ...
```

**Action name inference:** `@document_action` strips the `handle_` prefix automatically, so `handle_request_ride` is documented as `request_ride`. Pass `action=` explicitly if you need to override that default.

**Event type** is always explicit on `@document_event` because the method name
(`ride_offer`) doesn't encode the full dotted type (`"ride.offer"`).

### 2. Wire up the views

```python
# myapp/urls.py
from django.urls import path
from channels_spectacular.views import AsyncAPIDocView, AsyncAPISpecView
from myapp.consumers import DispatchConsumer

urlpatterns = [
    path("ws-docs/", AsyncAPIDocView.as_view()),
    path(
        "ws-docs/asyncapi.yaml",
        AsyncAPISpecView.as_view(consumer=DispatchConsumer),
    ),
]
```

Visit `/ws-docs/` for the interactive HTML viewer.
Visit `/ws-docs/asyncapi.yaml` for the raw spec.

---

## Full example: A Dispatch API

A realistic consumer showing all decorator features and all three payload
formats (dataclass, DRF serializer, Pydantic model):

```python
# dispatch/consumers.py
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels_spectacular import document_action, document_event

# --------------------------------------------------------------------------
# Payload option 1: Python dataclass (no extra dependency)
# --------------------------------------------------------------------------
@dataclass
class RequestRidePayload:
    pickup_address: str
    fare: Decimal
    passenger_count: int
    note: Optional[str] = None          # Optional[T] → not required in schema


# --------------------------------------------------------------------------
# Payload option 2: DRF Serializer (pip install djangorestframework)
# --------------------------------------------------------------------------
from rest_framework import serializers

class AcceptOfferSerializer(serializers.Serializer):
    ride_id   = serializers.UUIDField()
    driver_id = serializers.UUIDField()


# --------------------------------------------------------------------------
# Payload option 3: Pydantic model (pip install pydantic)
# --------------------------------------------------------------------------
from pydantic import BaseModel

class RideOfferPayload(BaseModel):
    ride_id:     UUID
    driver_name: str
    eta_minutes: int


# --------------------------------------------------------------------------
# Consumer
# --------------------------------------------------------------------------
class DispatchConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close(code=4401)
            return
        await self.accept()

    # ---- client → server actions ----------------------------------------

    @document_action(
        summary="Request a ride",
        description="Rider sends pickup details to start dispatch.",
        payload=RequestRidePayload,       # ← dataclass
        responses={"ride.requested": {"ride_id": "uuid"}},
        tags=["rides"],
        examples=[
            {
                "name": "Cash ride",
                "summary": "Standard cash pickup",
                "payload": {
                    "action": "request_ride",
                    "pickup_address": "23 Marina Rd, Lagos",
                    "fare": "1500.00",
                    "passenger_count": 1,
                },
            }
        ],
    )
    async def handle_request_ride(self, content):
        ...

    @document_action(
        summary="Accept a driver offer",
        payload=AcceptOfferSerializer,    # ← DRF serializer
        tags=["rides"],
    )
    async def handle_accept_offer(self, content):
        ...

    @document_action(
        action="ping",
        summary="Health check, expects a pong event in return",
        # payload=None → discriminator-only schema (no extra fields)
    )
    async def handle_ping(self, content):
        ...

    @document_action(summary="Cancel an active ride request", deprecated=True)
    async def handle_cancel_ride(self, content):
        ...

    # ---- server → client events -----------------------------------------

    @document_event(
        "ride.offer",
        summary="Server pushes a driver offer to the rider",
        payload=RideOfferPayload,         # ← Pydantic model
        tags=["rides"],
        examples=[
            {
                "name": "Standard offer",
                "payload": {
                    "type": "ride.offer",
                    "ride_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                    "driver_name": "Emeka",
                    "eta_minutes": 4,
                },
            }
        ],
    )
    async def ride_offer(self, event):
        ...

    @document_event(
        "ride.accepted",
        summary="Ride accepted by a driver",
        payload={"type": "object", "properties": {"driver_name": {"type": "string"}}},
    )
    async def ride_accepted(self, event):
        ...
```

All four payload formats produce a JSON Schema fragment in the spec; the
table in [Payload formats](#payload-formats) shows the mapping in detail.

---

## Authentication

WebSocket handshakes are HTTP upgrade requests, so Django's standard auth mechanisms apply out of the box. They just need to run in the ASGI middleware layer before the connection reaches your consumer.

### Cookie / session auth (browser clients)

The browser sends the `sessionid` cookie automatically on same-origin
connections. Wrap your router with `AuthMiddlewareStack`:

```python
# myproject/asgi.py
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from dispatch.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

`AuthMiddlewareStack` reads the `sessionid` cookie from the handshake
headers and populates `scope["user"]`.

### Query parameter auth (API / mobile clients)

Apps that can't set cookies attach a short-lived JWT as a URL query param:
`wss://api.example.com/ws/?token=<jwt>`. Write a small ASGI middleware that
reads it from `scope["query_string"]`:

```python
# dispatch/middleware.py
from urllib.parse import parse_qs
from http.cookies import SimpleCookie
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
import jwt

@database_sync_to_async
def get_user_from_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(pk=payload["user_id"])
    except Exception:
        return AnonymousUser()

class QueryTokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            qs = parse_qs(scope["query_string"].decode())
            token = qs.get("token", [None])[0]
            scope["user"] = (
                await get_user_from_token(token) if token else AnonymousUser()
            )
        return await self.inner(scope, receive, send)

class CookieJWTAuthMiddleware:
    """
    Reads a JWT from the `access_token` cookie and populates scope["user"].

    Falls back to AnonymousUser when the cookie is absent or the token is
    invalid/expired.
    """

    cookie_name = "access_token"

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            token = None
            for name, value in scope.get("headers", []):
                if name == b"cookie":
                    cookies = SimpleCookie()
                    cookies.load(value.decode())
                    morsel = cookies.get(self.cookie_name)
                    token = morsel.value if morsel else None
                    break
            scope["user"] = (
                await get_user_from_token(token)
                if token
                else AnonymousUser()
            )
        return await self.inner(scope, receive, send)
```

### Documenting auth in the spec

Add these settings and the generator inserts `securitySchemes` into the spec:

```python
CHANNELS_SPECTACULAR_SETTINGS = {
    "AUTH_QUERY_PARAM": "token",      # adds httpApiKey query scheme
    "AUTH_COOKIE_NAME": "access_token",  # adds httpApiKey cookie scheme
}
```

### Try-it-out panel

The interactive viewer's auth selector (`TRY_IT_OUT_ENABLED = True`) supports
both schemes:

- **Query param**: paste a token and click **Apply**; it appends
  `?token=<jwt>` to the WebSocket URL before connecting.
- **Session cookie (automatic)**: the browser sends `sessionid`
  automatically; just confirm you are logged in on the same origin.

---

### 3. Configure (optional)

```python
# settings.py
CHANNELS_SPECTACULAR_SETTINGS = {
    "TITLE": "Dispatch API",
    "VERSION": "1.0.0",
    "DESCRIPTION": "Real-time ride and delivery dispatch.",
    "CHANNEL_PATH": "/ws/dispatch/",
    # Static servers block - omit to derive from the request.
    "SERVERS": {
        "production": {"host": "api.example.com", "protocol": "wss"},
    },
    # Fallbacks when SERVERS is None:
    "WS_HOST": None,           # defaults to request.get_host()
    "WS_PROTOCOL": None,       # defaults to "wss" if HTTPS else "ws"
    # Enable the interactive try-it-out panel (dev only):
    "TRY_IT_OUT_ENABLED": False,
    "ASYNCAPI_VERSION": "3.0.0",
}
```

---

## Multi-consumer support

### Multiple consumers in one spec

Merge several consumers into a single spec by passing a `consumers` list
to `AsyncAPISpecView`. The generator prefixes operations with the consumer's
channel name to keep them unique.

```python
urlpatterns = [
    path("ws-docs/", AsyncAPIDocView.as_view()),
    path(
        "ws-docs/asyncapi.yaml",
        AsyncAPISpecView.as_view(
            consumers=[
                (RideConsumer,  "/ws/rides/"),
                (NotifConsumer, "/ws/notifications/"),
            ],
        ),
    ),
]
```

### Separate specs with a switcher dropdown

Serve each consumer under its own URL and let users switch between them
with a built-in dropdown in the docs viewer:

```python
urlpatterns = [
    path(
        "ws-docs/",
        AsyncAPIDocView.as_view(
            specs=[
                ("Dispatch  /ws/dispatch/", "/api/v1/ws-docs/dispatch/asyncapi.yaml"),
                ("Notifications  /ws/notif/", "/api/v1/ws-docs/notif/asyncapi.yaml"),
            ],
        ),
    ),
    path(
        "ws-docs/dispatch/asyncapi.yaml",
        AsyncAPISpecView.as_view(consumer=DispatchConsumer, channel_path="/ws/dispatch/"),
    ),
    path(
        "ws-docs/notif/asyncapi.yaml",
        AsyncAPISpecView.as_view(consumer=NotifConsumer, channel_path="/ws/notifications/"),
    ),
]
```

Switching consumers re-renders the full AsyncAPI React component and automatically populates the try-it-out panel's WebSocket URL from the selected spec's `servers` block, so there is no manual URL editing involved.

---

## Management command: `export_asyncapi`

Export the spec to a YAML file for SDK generation, CI artefacts, or
committing alongside your API contracts.

### Generator mode from annotated consumers

```bash
# Single consumer
python manage.py export_asyncapi \
    --consumer myapp.consumers.DispatchConsumer:/ws/dispatch/ \
    --output docs/asyncapi.yaml

# Multiple consumers in one file
python manage.py export_asyncapi \
    --consumer myapp.consumers.RideConsumer:/ws/rides/ \
    --consumer myapp.consumers.NotifConsumer:/ws/notifications/ \
    --output docs/asyncapi.yaml
```

### Template mode from a hand-written YAML

For projects that maintain a hand-written AsyncAPI YAML (or a Django
template with `{{ WS_HOST }}` / `{{ WS_PROTOCOL }}` placeholders), use
`--template`:

```bash
python manage.py export_asyncapi \
    --template rides/templates/rides/asyncapi.yaml \
    --output docs/asyncapi.yaml \
    --host localhost:8000 \
    --protocol ws
```

The command:
1. Substitutes `{{ WS_HOST }}` / `{{ WS_PROTOCOL }}` (both Django and uppercase variants)
2. Injects `title` into payload schemas that lack one, so SDK generators
   (`@asyncapi/generator`, Modelina) produce readable type names instead of
   `AnonymousSchema_N`

### Full reference

```
usage: manage.py export_asyncapi [--consumer DOTTED.PATH[:/ws/path/] | --template FILE]
                                  [--output FILE] [--host HOST] [--protocol {ws,wss}]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--consumer` | - | Dotted import path, optionally `:channel_path`. Repeatable. |
| `--template` | - | Path to a hand-written AsyncAPI YAML template. |
| `-o / --output` | `asyncapi.yaml` | Destination file. Parent dirs created automatically. |
| `--host` | settings / `localhost:8000` | WS host for the servers block. |
| `--protocol` | settings / `ws` | `ws` or `wss`. |

---

## Payload formats

`document_action` and `document_event` accept four payload types:

| Type | How it's converted |
|------|--------------------|
| `None` | No payload schema |
| `dict` | Returned as-is (raw JSON Schema fragment) |
| `@dataclass` class | Introspects type annotations recursively |
| DRF `Serializer` subclass | Introspects `get_fields()` |
| Pydantic `BaseModel` subclass | `model_json_schema()` (v2) or `schema()` (v1) |


### Python / dataclass → JSON Schema

| Python type | JSON Schema |
|-------------|------------|
| `str` | `{"type": "string"}` |
| `int` | `{"type": "integer"}` |
| `float` | `{"type": "number"}` |
| `bool` | `{"type": "boolean"}` |
| `Decimal` | `{"type": "string", "format": "decimal"}` |
| `UUID` | `{"type": "string", "format": "uuid"}` |
| `list[T]` | `{"type": "array", "items": <T-schema>}` |
| `T \| None` / `Optional[T]` | `<T-schema>` (not in `required`) |
| Nested `@dataclass` | Recursive `{"type": "object", ...}` |

### DRF field → JSON Schema

`CharField`, `UUIDField`, `IntegerField`, `FloatField`, `DecimalField`,
`BooleanField`, `DateField`, `DateTimeField`, `ChoiceField` (with `enum`),
`ListField`, nested `Serializer`, and more are all mapped automatically.

---

## Using the generator directly

```python
from channels_spectacular import AsyncAPIGenerator
from myapp.consumers import DispatchConsumer

# Single consumer
generator = AsyncAPIGenerator(
    DispatchConsumer,
    info={"title": "Dispatch API", "version": "1.0.0"},
    servers={"prod": {"host": "api.example.com", "protocol": "wss"}},
    channel_path="/ws/dispatch/",
)

# Multiple consumers
generator = AsyncAPIGenerator(
    consumers=[
        (RideConsumer,  "/ws/rides/"),
        (NotifConsumer, "/ws/notifications/"),
    ],
    info={"title": "All Consumers", "version": "1.0.0"},
    servers={"prod": {"host": "api.example.com", "protocol": "wss"}},
)

spec_dict = generator.get_spec()   # Python dict
spec_yaml = generator.get_yaml()   # YAML string
```

---

## Inheritance

Annotated methods are discovered by walking `__mro__`, so subclasses can
extend a base consumer's documented actions:

```python
class BaseConsumer(AsyncJsonWebsocketConsumer):
    @document_action(summary="Ping")
    async def handle_ping(self, content): ...

class ExtendedConsumer(BaseConsumer):
    @document_action(summary="Override ping with more detail")
    async def handle_ping(self, content): ...  # overrides parent

    @document_action(summary="Extra action")
    async def handle_extra(self, content): ...
```

---

## Running the tests

```bash
cd django-channels-spectacular
pip install -e ".[dev]"
python runtests.py
```

---

## Contributing

Contributions, bug reports, feature requests, and pull requests alike are welcome.

### Setting up a development environment

```bash
git clone https://github.com/ibukun-brain/django-channels-spectacular.git
cd django-channels-spectacular

pip install -e ".[dev]"
# or
uv sync --extra dev
```

### Submitting a pull request

1. Fork the repository.
2. Make your changes and add tests.
3. Open a pull request with a clear title and description.
4. One feature or fix per PR makes review faster.

### Reporting bugs

Open a [GitHub issue](https://github.com/ibukun-brain/django-channels-spectacular/issues)
with the Python/Django/Channels versions, a minimal reproduction, and the full traceback.

---

## License

[BSD 3-Clause](LICENSE)
