"""
Chat consumer — the main example showing channels-spectacular in action.

Actions (client → server):
  join          Join a named room.
  send_message  Broadcast a message to the room.
  leave         Leave the current room.

Events (server → client):
  message.new   A message was posted.
  user.joined   Someone joined the room.
  user.left     Someone left the room.
"""

from __future__ import annotations

from dataclasses import dataclass

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from channels_spectacular.decorators import document_action, document_event


@dataclass
class JoinPayload:
    username: str
    room: str


@dataclass
class SendMessagePayload:
    text: str


@dataclass
class MessageNewPayload:
    username: str
    text: str
    room: str


@dataclass
class UserEventPayload:
    username: str
    room: str


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Real-time chat consumer backed by the in-memory channel layer."""

    async def connect(self):
        # Accept all incoming connections. In a real app, you'd want to do some
        # authentication and reject unauthorized users.
        await self.accept()

    async def receive_json(self, content: dict) -> None:
        action = content.get("action", "")
        handler = getattr(self, f"handle_{action}", None)
        if handler:
            await handler(content)

    async def websocket_disconnect(self, message: dict) -> None:
        if hasattr(self, "room_group"):
            await self.channel_layer.group_discard(
                self.room_group, self.channel_name
            )

    # ------------------------------------------------------------------ #
    # Actions — client → server                                           #
    # ------------------------------------------------------------------ #

    @document_action(
        summary="Join a chat room",
        description=(
            "Subscribe to a named room. The server broadcasts a "
            "`user.joined` event to all members already in the room."
        ),
        payload=JoinPayload,
        tags=["chat"],
        examples=[
            {
                "name": "Join general",
                "payload": {"action": "join", "username": "Alice", "room": "general"},
            },
        ],
    )
    async def handle_join(self, content: dict) -> None:
        self.username: str = content["username"]
        self.room_group: str = f"chat_{content['room']}"

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "user.joined",
                "username": self.username,
                "room": content["room"],
            },
        )

    @document_action(
        summary="Send a message to the room",
        description="Broadcasts the message to every connected member of the room.",
        payload=SendMessagePayload,
        tags=["chat"],
        examples=[
            {
                "name": "Simple message",
                "payload": {"action": "send_message", "text": "Hello everyone!"},
            },
        ],
    )
    async def handle_send_message(self, content: dict) -> None:
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "message.new",
                "username": self.username,
                "text": content["text"],
                "room": self.room_group,
            },
        )

    @document_action(
        summary="Leave the current room",
        description=(
            "Unsubscribe from the room. The server broadcasts a "
            "`user.left` event before removing the connection."
        ),
        tags=["chat"],
    )
    async def handle_leave(self, content: dict) -> None:
        if hasattr(self, "room_group"):
            await self.channel_layer.group_send(
                self.room_group,
                {
                    "type": "user.left",
                    "username": self.username,
                    "room": self.room_group,
                },
            )
            await self.channel_layer.group_discard(
                self.room_group, self.channel_name
            )

    # ------------------------------------------------------------------ #
    # Events — server → client                                            #
    # ------------------------------------------------------------------ #

    @document_event(
        "message.new",
        summary="A message was posted in the room",
        payload=MessageNewPayload,
        tags=["chat"],
        examples=[
            {
                "name": "Chat message",
                "payload": {
                    "type": "message.new",
                    "username": "Alice",
                    "text": "Hello everyone!",
                    "room": "general",
                },
            }
        ],
    )
    async def message_new(self, event: dict) -> None:
        await self.send_json(event)

    @document_event(
        "user.joined",
        summary="A user joined the room",
        payload=UserEventPayload,
        tags=["chat"],
    )
    async def user_joined(self, event: dict) -> None:
        await self.send_json(event)

    @document_event(
        "user.left",
        summary="A user left the room",
        payload=UserEventPayload,
        tags=["chat"],
    )
    async def user_left(self, event: dict) -> None:
        await self.send_json(event)
