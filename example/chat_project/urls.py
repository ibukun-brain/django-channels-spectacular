"""URL configuration for the chat example app."""

from chat.consumers import ChatConsumer
from chat.views import index
from django.urls import path
from notifications.consumers import NotificationConsumer

from channels_spectacular.views import AsyncAPIDocView, AsyncAPISpecView

urlpatterns = [
    path("", index, name="chat-index"),

    # ------------------------------------------------------------------ #
    # Individual specs — one URL per consumer                             #
    # ------------------------------------------------------------------ #
    path(
        "ws-docs/chat/asyncapi.yaml",
        AsyncAPISpecView.as_view(
            consumer=ChatConsumer,
            channel_path="/ws/chat/",
        ), 
        name="asyncapi-spec-chat",
    ),
    path(
        "ws-docs/notifications/asyncapi.yaml",
        AsyncAPISpecView.as_view(
            consumer=NotificationConsumer,
            channel_path="/ws/notifications/",
        ),
        name="asyncapi-spec-notifications",
    ),

    # ------------------------------------------------------------------ #
    # Merged spec — both consumers in a single AsyncAPI document          #
    # ------------------------------------------------------------------ #
    path(
        "ws-docs/merged/asyncapi.yaml",
        AsyncAPISpecView.as_view(
            consumers=[
                (ChatConsumer, "/ws/chat/"),
                (NotificationConsumer, "/ws/notifications/"),
            ],
        ),
        name="asyncapi-spec-merged",
    ),

    # ------------------------------------------------------------------ #
    # Doc viewer with spec-switcher dropdown                              #
    # ------------------------------------------------------------------ #
    path(
        "ws-docs/",
        AsyncAPIDocView.as_view(
            specs=[
                ("Chat  /ws/chat/", "/ws-docs/chat/asyncapi.yaml"),
                ("Notifications  /ws/notifications/", "/ws-docs/notifications/asyncapi.yaml"),
                ("Merged (both consumers)", "/ws-docs/merged/asyncapi.yaml"),
            ],
        ),
        name="asyncapi-doc",
    ),
]
