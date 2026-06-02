"""
Decorators for annotating Django Channels consumer methods with
AsyncAPI metadata.

Usage
-----
Client → server (handle_* methods):

    @document_action(
        summary="Request a ride",
        payload=RequestRideSerializer,
        responses={"ride.requested": {"ride_id": "uuid"}},
    )
    async def handle_request_ride(self, content): ...

    # Action name is inferred as "request_ride" (strips "handle_").
    # Pass action= explicitly to override, e.g. for non-standard names.

Server → client (channel-layer event handlers):

    @document_event("ride.offer", summary="Driver receives a ride offer")
    async def ride_offer(self, event): ...

    # event_type is always required because the method name doesn't
    # encode the full dotted name ("ride_offer" ≠ "ride.offer").
"""

from __future__ import annotations

from typing import Any

# Private sentinels; AsyncAPIGenerator searches for these attributes.
ASYNCAPI_ACTION_ATTR = "_channels_spectacular_action"
ASYNCAPI_EVENT_ATTR = "_channels_spectacular_event"


def document_action(
    action: str | None = None,
    *,
    summary: str = "",
    description: str = "",
    payload: Any = None,
    responses: dict[str, Any] | None = None,
    examples: list[dict] | None = None,
    deprecated: bool = False,
    tags: list[str] | None = None,
):
    """
    Marks a consumer method as a documented client→server operation.

    Args:
        action: The action name that appears in the AsyncAPI spec. If
            omitted, inferred from the method name:
            ``handle_request_ride`` → ``"request_ride"``.
            For methods that do *not* start with ``"handle_"``, the
            full method name is used unchanged. Pass explicitly when
            your consumer uses a different routing convention.
        summary: One-line description shown in the spec viewer.
        description: Longer Markdown description (optional).
        payload: Schema for the message the client sends. Accepts:

            * A DRF ``Serializer`` subclass
            * A Pydantic ``BaseModel`` subclass
            * A Python ``@dataclass`` class
            * A plain ``dict`` (raw JSON Schema fragment)
            * ``None`` — omits the payload schema
        responses: Mapping of ``event_type → payload`` describing
            server-push events this action can trigger (informational;
            not part of the formal AsyncAPI operation model).
        examples: List of example message objects. Each entry is a dict
            with optional ``name`` and ``summary`` strings and a
            required ``payload`` dict containing concrete field values.
            Rendered in the AsyncAPI viewer and useful for SDK
            consumers as reference data::

                examples=[
                    {
                        "name": "Cash payment",
                        "summary": "Rider pays with cash",
                        "payload": {
                            "action": "request_ride",
                            "pickup_lat": 6.5244,
                            "fare": "1500.00",
                            "payment_method": "cash",
                        },
                    }
                ]
        deprecated: Marks the operation as deprecated in the spec.
        tags: Tag strings for grouping operations in the viewer.
    """

    def decorator(func):
        resolved = action
        if resolved is None:
            name = func.__name__
            resolved = (
                name[len("handle_"):]
                if name.startswith("handle_")
                else name
            )
        setattr(
            func,
            ASYNCAPI_ACTION_ATTR,
            {
                "action": resolved,
                "summary": summary,
                "description": description,
                "payload": payload,
                "responses": responses or {},
                "examples": examples or [],
                "deprecated": deprecated,
                "tags": tags or [],
            },
        )
        return func

    return decorator


def document_event(
    event_type: str,
    *,
    summary: str = "",
    description: str = "",
    payload: Any = None,
    examples: list[dict] | None = None,
    deprecated: bool = False,
    tags: list[str] | None = None,
):
    """
    Marks a channel-layer event handler as a documented
    server→client (receive) operation.

    Args:
        event_type: The dotted event type string (e.g.
            ``"ride.offer"``). Always required — the method name
            (``ride_offer``) doesn't encode the full dotted name.
        summary: One-line description shown in the spec viewer.
        description: Longer Markdown description (optional).
        payload: Schema for the message the server sends. Accepts
            the same types as ``document_action``'s ``payload``.
        examples: List of example message objects. Each entry is a dict
            with optional ``name`` and ``summary`` strings and a
            required ``payload`` dict containing concrete field values.
            Rendered in the AsyncAPI viewer as concrete server-push
            payloads::

                examples=[
                    {
                        "name": "Standard offer",
                        "summary": "Offer pushed to nearest driver",
                        "payload": {
                            "type": "ride.offer",
                            "ride_id": "d290f1ee-...",
                            "fare": "1500.00",
                        },
                    }
                ]
        deprecated: Marks the operation as deprecated in the spec.
        tags: Tag strings for grouping operations in the viewer.
    """

    def decorator(func):
        setattr(
            func,
            ASYNCAPI_EVENT_ATTR,
            {
                "event_type": event_type,
                "summary": summary,
                "description": description,
                "payload": payload,
                "examples": examples or [],
                "deprecated": deprecated,
                "tags": tags or [],
            },
        )
        return func

    return decorator
