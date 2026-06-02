"""
Notification consumer — demonstrates a push-notification channel.

Actions (client → server):
  subscribe     Subscribe to live notifications for the authenticated user.
  mark_read     Mark a notification as read.

Events (server → client):
  notification.new    A new notification was pushed to the user.
  notification.read   Acknowledgement after a successful mark_read.
"""

from __future__ import annotations

from dataclasses import dataclass

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from channels_spectacular.decorators import document_action, document_event


@dataclass
class SubscribePayload:
    user_id: int


@dataclass
class MarkReadPayload:
    notification_id: str


@dataclass
class NotificationNewPayload:
    notification_id: str
    title: str
    body: str
    category: str   # "mention" | "like" | "follow" | "system"
    created_at: str  # ISO 8601, e.g. "2026-06-01T10:30:00Z"
    is_read: bool


@dataclass
class NotificationReadPayload:
    notification_id: str
    is_read: bool


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Push notifications for a single user over a private channel."""

    async def connect(self):
        await self.accept()

    async def receive_json(self, content: dict) -> None:
        action = content.get("action", "")
        handler = getattr(self, f"handle_{action}", None)
        if handler:
            await handler(content)

    async def websocket_disconnect(self, message: dict) -> None:
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(
                self.user_group, self.channel_name
            )

    # ------------------------------------------------------------------ #
    # Actions — client → server                                           #
    # ------------------------------------------------------------------ #

    @document_action(
        summary="Subscribe to notifications",
        description=(
            "Register this connection to receive live notifications for "
            "the given user. Call this immediately after connecting. "
            "In a real app the user_id would be resolved from the auth "
            "token — it is explicit here for demonstration purposes."
        ),
        payload=SubscribePayload,
        tags=["notifications"],
        examples=[
            {
                "name": "Subscribe user 42",
                "payload": {"action": "subscribe", "user_id": 42},
            },
        ],
    )
    async def handle_subscribe(self, content: dict) -> None:
        self.user_id: int = content["user_id"]
        self.user_group: str = f"notifications_user_{self.user_id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)

    @document_action(
        summary="Mark a notification as read",
        description=(
            "Mark the given notification as read. The server replies with "
            "a `notification.read` event confirming the state change."
        ),
        payload=MarkReadPayload,
        tags=["notifications"],
        examples=[
            {
                "name": "Mark read",
                "payload": {
                    "action": "mark_read",
                    "notification_id": "notif_abc123",
                },
            },
        ],
    )
    async def handle_mark_read(self, content: dict) -> None:
        # In a real app this would update the database.
        await self.send_json(
            {
                "type": "notification.read",
                "notification_id": content["notification_id"],
                "is_read": True,
            }
        )

    # ------------------------------------------------------------------ #
    # Events — server → client                                            #
    # ------------------------------------------------------------------ #

    @document_event(
        "notification.new",
        summary="A new notification was pushed",
        description=(
            "Emitted whenever a new notification is created for the "
            "subscribed user. Sent by the server at any time after "
            "`subscribe` — no client request needed."
        ),
        payload=NotificationNewPayload,
        tags=["notifications"],
        examples=[
            {
                "name": "Mention notification",
                "payload": {
                    "type": "notification.new",
                    "notification_id": "notif_abc123",
                    "title": "Alice mentioned you",
                    "body": "Alice mentioned you in #general: "
                            "\"Hey @bob, take a look at this!\"",
                    "category": "mention",
                    "created_at": "2026-06-01T10:30:00Z",
                    "is_read": False,
                },
            },
            {
                "name": "System alert",
                "payload": {
                    "type": "notification.new",
                    "notification_id": "notif_sys001",
                    "title": "Scheduled maintenance",
                    "body": "The service will be down for 10 minutes at 03:00 UTC.",
                    "category": "system",
                    "created_at": "2026-06-01T08:00:00Z",
                    "is_read": False,
                },
            },
        ],
    )
    async def notification_new(self, event: dict) -> None:
        await self.send_json(event)

    @document_event(
        "notification.read",
        summary="Notification marked as read",
        description=(
            "Sent in response to a `mark_read` action confirming that "
            "the notification state was updated."
        ),
        payload=NotificationReadPayload,
        tags=["notifications"],
        examples=[
            {
                "name": "Read confirmation",
                "payload": {
                    "type": "notification.read",
                    "notification_id": "notif_abc123",
                    "is_read": True,
                },
            }
        ],
    )
    async def notification_read(self, event: dict) -> None:
        await self.send_json(event)
