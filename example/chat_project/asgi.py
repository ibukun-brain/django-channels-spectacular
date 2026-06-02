"""ASGI config for the chat example app."""

import os

import chat.routing  # noqa: E402 — must be imported after Django setup
import notifications.routing  # noqa: E402
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat_project.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
                + notifications.routing.websocket_urlpatterns
            )
        ),
    }
)
