# Configuration

All settings live under the `CHANNELS_SPECTACULAR_SETTINGS` dict in your
Django settings file. Every key is optional; the defaults are shown below.

```python
# settings.py
CHANNELS_SPECTACULAR_SETTINGS = {
    # Spec metadata
    "TITLE": "WebSocket API",
    "VERSION": "0.1.0",
    "DESCRIPTION": "",

    # Default channel path used when no channel_path is passed to the view
    # or management command.
    "CHANNEL_PATH": "/ws/",

    # ── Servers block ──────────────────────────────────────────────────────
    # When set, this dict is used verbatim as the AsyncAPI `servers` block.
    # When None (default), the block is derived from the incoming request
    # using WS_HOST and WS_PROTOCOL below.
    "SERVERS": None,

    # Fallbacks used when SERVERS is None:
    "WS_HOST": None,        # defaults to request.get_host()
    "WS_PROTOCOL": None,    # defaults to "wss" if request.is_secure() else "ws"

    # ── Try-it-out panel ───────────────────────────────────────────────────
    # Enable the interactive WebSocket console in the docs viewer.
    # Keep False in production, it is only useful during development.
    "TRY_IT_OUT_ENABLED": False,
}
```

## Setting static servers

Provide a `SERVERS` dict to lock the spec to specific environments:

```python
CHANNELS_SPECTACULAR_SETTINGS = {
    "SERVERS": {
        "production": {
            "host": "api.example.com",
            "protocol": "wss",
            "description": "Production server",
        },
        "staging": {
            "host": "staging.example.com",
            "protocol": "wss",
        },
        "local": {
            "host": "localhost:8000",
            "protocol": "ws",
        },
    },
}
```

## Single consumer (per-view overrides)

Both `AsyncAPISpecView` and `AsyncAPIDocView` accept class attributes that
take precedence over the global settings:

```python
# urls.py
from channels_spectacular.views import AsyncAPIDocView, AsyncAPISpecView
from myapp.consumers import DispatchConsumer

urlpatterns = [
    path("ws-docs/", AsyncAPIDocView.as_view()),
    path(
        "ws-docs/asyncapi.yaml",
        AsyncAPISpecView.as_view(
            consumer=DispatchConsumer,
            channel_path="/ws/dispatch/",
            servers={
                "custom": {"host": "custom.example.com", "protocol": "wss"},
            },
        ),
    ),
]
```

## Multiple consumers (merged spec)

Pass `consumers` to generate a single spec that covers all your channels.
The generator prefixes each consumer's operations with its channel name so
operation IDs stay unique across the merged document.

```python
from myapp.consumers import DispatchConsumer, NotifConsumer

urlpatterns = [
    path("ws-docs/", AsyncAPIDocView.as_view()),
    path(
        "ws-docs/asyncapi.yaml",
        AsyncAPISpecView.as_view(
            consumers=[
                (DispatchConsumer, "/ws/dispatch/"),
                (NotifConsumer,    "/ws/notifications/"),
            ],
            servers={
                "production": {"host": "api.example.com", "protocol": "wss"},
            },
        ),
    ),
]
```

## Multiple consumers (separate specs with switcher dropdown)

Serve each consumer at its own URL and render a dropdown in the docs viewer
that lets readers switch between them. The try-it-out panel's WebSocket URL
updates automatically when a different consumer is selected.

```python
from myapp.consumers import DispatchConsumer, NotifConsumer, PaymentConsumer

urlpatterns = [
    # Viewer with switcher
    path(
        "ws-docs/",
        AsyncAPIDocView.as_view(
            specs=[
                ("Dispatch  /ws/dispatch/",         "/api/v1/ws-docs/dispatch/asyncapi.yaml"),
                ("Notifications  /ws/notif/",       "/api/v1/ws-docs/notif/asyncapi.yaml"),
                ("Payments  /ws/payments/",         "/api/v1/ws-docs/payments/asyncapi.yaml"),
            ],
        ),
    ),
    # Individual spec endpoints
    path(
        "ws-docs/dispatch/asyncapi.yaml",
        AsyncAPISpecView.as_view(consumer=DispatchConsumer, channel_path="/ws/dispatch/"),
    ),
    path(
        "ws-docs/notif/asyncapi.yaml",
        AsyncAPISpecView.as_view(consumer=NotifConsumer, channel_path="/ws/notifications/"),
    ),
    path(
        "ws-docs/payments/asyncapi.yaml",
        AsyncAPISpecView.as_view(consumer=PaymentConsumer, channel_path="/ws/payments/"),
    ),
]
```

Each spec URL is a standalone AsyncAPI document. The switcher bar appears
only when `specs` has two or more entries.

## Priority order

For `servers`, the resolution order is (highest to lowest):

1. `servers` passed to `as_view(...)`
2. `CHANNELS_SPECTACULAR_SETTINGS["SERVERS"]`
3. Derived from the request using `WS_HOST` / `WS_PROTOCOL`
