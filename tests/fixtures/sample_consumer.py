"""
Annotated consumers used as fixtures across all test modules.

``SampleConsumer`` intentionally exercises every supported payload type
and edge case:
  - handle_ prefix inference
  - explicit action= override
  - raw dict payload
  - None payload (no schema)
  - deprecated flag
  - tags
  - examples (single and multiple)
  - DRF serializer payload (imported lazily so tests run without DRF)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from channels_spectacular.decorators import document_action, document_event


# ---------------------------------------------------------------------------
# Payload dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RideRequestPayload:
    pickup_address: str
    fare: Decimal
    passenger_count: int
    ride_id: Optional[UUID] = None  # not required (has default)


@dataclass(frozen=True, slots=True)
class RideOfferPayload:
    ride_id: UUID
    driver_name: str
    expires_at: float


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------

class SampleConsumer:
    """Minimal consumer for testing — not a real Channels consumer."""

    # --- Client → server actions ---

    @document_action(
        summary="Request a ride",
        description="Rider sends pickup details to initiate dispatch.",
        payload=RideRequestPayload,
        responses={"ride.requested": {"ride_id": "uuid"}},
        tags=["rides"],
        examples=[
            {
                "name": "Cash payment",
                "summary": "Rider requests with cash",
                "payload": {
                    "action": "request_ride",
                    "pickup_address": "123 Main St",
                    "fare": "1500.00",
                    "passenger_count": 1,
                },
            },
            {
                "name": "Card payment",
                "summary": "Rider requests with card",
                "payload": {
                    "action": "request_ride",
                    "pickup_address": "456 Side Ave",
                    "fare": "2000.00",
                    "passenger_count": 2,
                },
            },
        ],
    )
    async def handle_request_ride(self, content):
        pass

    @document_action(
        summary="Accept an offer",
        payload={
            "type": "object",
            "properties": {"ride_id": {"type": "string"}},
        },
        tags=["rides"],
    )
    async def handle_accept_offer(self, content):
        pass

    @document_action(
        action="ping",
        summary="Health check",
        # No payload — discriminator-only schema
    )
    async def handle_ping(self, content):
        pass

    @document_action(
        summary="Deprecated cancel action",
        deprecated=True,
    )
    async def handle_cancel_ride(self, content):
        pass

    # An action with an explicit name that doesn't follow handle_ convention
    @document_action(action="custom_action", summary="Custom routing")
    async def my_router(self, content):
        pass

    # --- Server → client events ---

    @document_event(
        "ride.offer",
        summary="Driver receives a ride offer",
        payload=RideOfferPayload,
        tags=["rides"],
        examples=[
            {
                "name": "Standard offer",
                "summary": "Offer pushed to nearest available driver",
                "payload": {
                    "type": "ride.offer",
                    "ride_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
                    "driver_name": "Emeka",
                    "expires_at": 1717000000.0,
                },
            },
        ],
    )
    async def ride_offer(self, event):
        pass

    @document_event(
        "ride.accepted",
        summary="Ride accepted by driver",
        payload={
            "type": "object",
            "properties": {"driver_name": {"type": "string"}},
        },
    )
    async def ride_accepted(self, event):
        pass

    @document_event(
        "ride.cancelled",
        summary="Ride was cancelled",
        deprecated=True,
    )
    async def ride_cancelled(self, event):
        pass


# ---------------------------------------------------------------------------
# Second consumer — used for multi-consumer spec tests
# ---------------------------------------------------------------------------

class NotificationConsumer:
    """Minimal second consumer for multi-channel spec tests."""

    @document_action(
        summary="Subscribe to a topic",
        payload={
            "type": "object",
            "properties": {"topic": {"type": "string"}},
        },
    )
    async def handle_subscribe(self, content):
        pass

    @document_action(
        summary="Unsubscribe from a topic",
        payload={
            "type": "object",
            "properties": {"topic": {"type": "string"}},
        },
    )
    async def handle_unsubscribe(self, content):
        pass

    @document_event(
        "notification.new",
        summary="A new notification has arrived",
        payload={
            "type": "object",
            "properties": {"message": {"type": "string"}},
        },
    )
    async def new_notification(self, event):
        pass
