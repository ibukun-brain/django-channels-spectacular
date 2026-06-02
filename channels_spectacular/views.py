"""
Django views for serving the AsyncAPI documentation.

Two views are provided:

``AsyncAPIDocView``
    Renders the HTML page that hosts the AsyncAPI React viewer.  Point
    it at any URL and set ``spec_url`` (or leave it as ``None`` to
    auto-derive from the sibling ``asyncapi.yaml`` path).

``AsyncAPISpecView``
    Returns the AsyncAPI 3.0 spec as ``application/yaml``.  Wire it up
    alongside ``AsyncAPIDocView``::

        # urls.py — single consumer
        from channels_spectacular.views import (
            AsyncAPIDocView, AsyncAPISpecView,
        )
        from myapp.consumers import MyConsumer

        urlpatterns = [
            path("ws-docs/", AsyncAPIDocView.as_view()),
            path(
                "ws-docs/asyncapi.yaml",
                AsyncAPISpecView.as_view(consumer=MyConsumer),
            ),
        ]

        # urls.py — multiple consumers in one spec
        urlpatterns = [
            path("ws-docs/", AsyncAPIDocView.as_view()),
            path(
                "ws-docs/asyncapi.yaml",
                AsyncAPISpecView.as_view(
                    consumers=[
                        (RideConsumer, "/ws/rides/"),
                        (NotificationConsumer, "/ws/notifications/"),
                    ],
                ),
            ),
        ]

All arguments to both views are optional when the corresponding keys
are set in ``CHANNELS_SPECTACULAR_SETTINGS``.
"""

from __future__ import annotations

from django.conf import settings as django_settings
from django.http import HttpResponse
from django.views.generic import TemplateView, View

from channels_spectacular.generator import AsyncAPIGenerator
from channels_spectacular.settings import spectacular_settings


class AsyncAPISpecView(View):
    """
    Returns the AsyncAPI 3.0 spec as ``application/yaml``.

    Class attributes (all optional — fall back to settings):
        consumer: Single annotated consumer class.  Mutually exclusive
            with ``consumers``.
        consumers: List of ``(consumer_class, channel_path)`` pairs for
            a multi-channel spec.  Mutually exclusive with ``consumer``.
        info: AsyncAPI ``info`` object dict.
        servers: AsyncAPI ``servers`` mapping.  When ``None`` (default),
            built dynamically from the incoming request using
            ``WS_HOST`` / ``WS_PROTOCOL`` settings.
        channel_path: WebSocket URL path for the single consumer.
            Ignored when ``consumers`` is provided.
    """

    consumer: type | None = None
    consumers: list | None = None
    info: dict | None = None
    servers: dict | None = None
    channel_path: str | None = None

    def get(self, request, *args, **kwargs):
        if self.consumer is None and self.consumers is None:
            raise ValueError(
                "AsyncAPISpecView requires a `consumer` class or "
                "`consumers` list. Pass it via "
                "as_view(consumer=MyConsumer) or "
                "as_view(consumers=[(MyConsumer, '/ws/path/')]) "
                "or set the class attribute."
            )

        resolved_servers = self._resolve_servers(request)

        if self.consumers is not None:
            generator = AsyncAPIGenerator(
                consumers=self.consumers,
                info=self.info,
                servers=resolved_servers,
            )
        else:
            generator = AsyncAPIGenerator(
                self.consumer,
                info=self.info,
                servers=resolved_servers,
                channel_path=self.channel_path,
            )
        return HttpResponse(
            generator.get_yaml(),
            content_type="application/yaml",
        )

    def _resolve_servers(self, request) -> dict | None:
        # Explicit servers on the view take highest priority.
        if self.servers is not None:
            return self.servers

        # Static servers from settings.
        if spectacular_settings.SERVERS is not None:
            return spectacular_settings.SERVERS

        # Derive from the request.
        host = spectacular_settings.WS_HOST or request.get_host()
        if spectacular_settings.WS_PROTOCOL:
            protocol = spectacular_settings.WS_PROTOCOL
        else:
            protocol = "wss" if request.is_secure() else "ws"

        return {"default": {"host": host, "protocol": protocol}}


class AsyncAPIDocView(TemplateView):
    """
    Renders the HTML page that hosts the AsyncAPI React viewer.

    Single-consumer usage (``spec_url`` defaults to the sibling
    ``asyncapi.yaml`` path)::

        path("ws-docs/", AsyncAPIDocView.as_view()),

    Multi-consumer usage — pass a ``specs`` list of
    ``(label, spec_url)`` pairs.  A dropdown appears at the top of the
    page so the reader can switch between consumers; the try-it-out
    panel's WebSocket URL updates automatically when they do::

        path(
            "ws-docs/",
            AsyncAPIDocView.as_view(
                specs=[
                    (
                        "Dispatch /ws/dispatch/",
                        "/api/v1/ws-docs/dispatch/asyncapi.yaml",
                    ),
                    (
                        "Notifications /ws/notifications/",
                        "/api/v1/ws-docs/notif/asyncapi.yaml",
                    ),
                ],
            ),
        ),

    Class attributes:
        spec_url: URL of the YAML spec for the single-consumer case.
        specs: List of ``(label, spec_url)`` pairs for the
            multi-consumer case.  Takes precedence over ``spec_url``.
        template_name: Template to render.  Override for a custom layout.
    """

    template_name = "channels_spectacular/asyncapi_viewer.html"
    spec_url: str | None = None
    specs: list[tuple[str, str]] | None = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["try_it_out"] = spectacular_settings.TRY_IT_OUT_ENABLED
        ctx["title"] = spectacular_settings.TITLE
        ctx["auth_query_param"] = (
            spectacular_settings.AUTH_QUERY_PARAM or "token"
        )
        ctx["auth_cookie_name"] = (
            spectacular_settings.AUTH_COOKIE_NAME or "access_token"
        )
        ctx["auth_session_cookie"] = getattr(
            django_settings, "SESSION_COOKIE_NAME", "sessionid"
        )
        ctx["try_it_out_expanded"] = spectacular_settings.TRY_IT_OUT_EXPANDED

        if self.specs:
            # Multi-consumer mode: pass all (label, url) pairs to the
            # template; the initial spec is the first in the list.
            ctx["specs"] = [
                {"label": label, "url": url} for label, url in self.specs
            ]
            ctx["spec_url"] = self.specs[0][1]
        else:
            ctx["specs"] = []
            if self.spec_url:
                ctx["spec_url"] = self.spec_url
            else:
                base = self.request.path.rstrip("/")
                ctx["spec_url"] = f"{base}/asyncapi.yaml"

        return ctx
