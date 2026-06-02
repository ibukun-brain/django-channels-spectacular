# Multi-consumer support

See the [Configuration](configuration) guide for full multi-consumer URL examples both the merged-spec and the separate-specs-with-switcher patterns.

## Merged spec

Pass `consumers` to `AsyncAPISpecView` to combine several consumers into
one AsyncAPI document. The generator prefixes each consumer's operation IDs
with the channel name to keep them unique.

```python
AsyncAPISpecView.as_view(
    consumers=[
        (RideConsumer,  "/ws/rides/"),
        (NotifConsumer, "/ws/notifications/"),
    ],
)
```

## Separate specs with switcher dropdown

Pass `specs` to `AsyncAPIDocView` to render a dark sticky bar at the top
of the viewer. Picking a consumer from the dropdown:

1. Re-renders the AsyncAPI React component with the new spec.
2. Auto-fills the try-it-out panel's WebSocket URL from the spec's
   `servers` block no manual editing needed.

```python
AsyncAPIDocView.as_view(
    specs=[
        ("Dispatch  /ws/dispatch/",    "/api/v1/ws-docs/dispatch/asyncapi.yaml"),
        ("Notifications  /ws/notif/",  "/api/v1/ws-docs/notif/asyncapi.yaml"),
    ],
)
```

The switcher only appears when `specs` has two or more entries.

## Generator API

```python
from channels_spectacular import AsyncAPIGenerator

generator = AsyncAPIGenerator(
    consumers=[
        (RideConsumer,  "/ws/rides/"),
        (NotifConsumer, "/ws/notifications/"),
    ],
    info={"title": "All Consumers", "version": "1.0.0"},
    servers={"prod": {"host": "api.example.com", "protocol": "wss"}},
)

yaml_str = generator.get_yaml()
```
