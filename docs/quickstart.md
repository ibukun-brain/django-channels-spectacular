# Quick start

This guide gets you from zero to a live AsyncAPI 3.0 docs page in three steps.

## 1. Annotate your consumer

Use `@document_action` on methods that handle messages **from** the client, and
`@document_event` on methods that handle messages **pushed to** the client from
the channel layer.

```python
# myapp/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels_spectacular import document_action, document_event
from myapp.serializers import RequestRideSerializer, AcceptOfferSerializer

class DispatchConsumer(AsyncJsonWebsocketConsumer):

    @document_action(
        summary="Request a ride",
        payload=RequestRideSerializer,
        responses={"ride.requested": {"ride_id": "uuid"}},
        tags=["rides"],
    )
    async def handle_request_ride(self, content):
        ...

    @document_action(
        summary="Accept a driver offer",
        payload=AcceptOfferSerializer,
    )
    async def handle_accept_offer(self, content):
        ...

    @document_event(
        "ride.offer",
        summary="Server pushes a fare offer to the rider",
        payload=RideOfferSerializer,
    )
    async def ride_offer(self, event):
        ...
```

`@document_action` automatically derives the action name from the method name by removing the `handle_` prefix. For example, `handle_request_ride` becomes `"request_ride"`. If your consumer follows a different naming convention, you can override the generated name with `action="my_name"`.


`@document_event` always requires the event type as the first positional
argument because the method name (`ride_offer`) would lose the dotted form
(`"ride.offer"`).

## 2. Wire up the URLs

```python
# myapp/urls.py
from django.urls import path
from channels_spectacular.views import AsyncAPIDocView, AsyncAPISpecView
from myapp.consumers import DispatchConsumer

urlpatterns = [
    # HTML viewer
    path("ws-docs/", AsyncAPIDocView.as_view()),
    # Raw YAML spec
    path(
        "ws-docs/asyncapi.yaml",
        AsyncAPISpecView.as_view(
            consumer=DispatchConsumer,
            channel_path="/ws/dispatch/",
        ),
    ),
]
```

Include these patterns in your root `urls.py`:

```python
# project/urls.py
urlpatterns = [
    path("api/v1/", include("myapp.urls")),
    ...
]
```

## 3. Browse the docs

Start your development server and open:

* **`/api/v1/ws-docs/`** interactive AsyncAPI viewer powered by React
* **`/api/v1/ws-docs/asyncapi.yaml`** raw AsyncAPI YAML specification

The specification is generated dynamically from your consumer annotations. When you update an action handler, there is no build step or regeneration process required—simply refresh the page to see the changes.

## Next steps

* [Configuration](configuration) - customize the API title, version, and server settings
* [Multi-consumer support](multi-consumer) - expose multiple consumers with a built-in consumer switcher
* [Export command](export-command) - export the generated specification for SDK generation, validation, or CI workflows
* [Payload types](payload-types) - detailed reference for DRF serializers, Pydantic models, dataclasses, and dictionary-based payloads
