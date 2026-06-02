"""
Package-level settings, read from ``settings.CHANNELS_SPECTACULAR_SETTINGS``.

All keys are optional; any key not present in the user's dict falls back
to the corresponding default below.

Example Django settings::

    CHANNELS_SPECTACULAR_SETTINGS = {
        "TITLE": "Dispatch API",
        "VERSION": "2.0.0",
        "DESCRIPTION": "Real-time ride and delivery dispatch over WebSocket.",
        "CHANNEL_PATH": "/ws/dispatch/",
        "WS_HOST": "api.example.com",
        "WS_PROTOCOL": "wss",
        "TRY_IT_OUT_ENABLED": True,
        # Optional: pin the servers block instead of deriving from request.
        # Each entry must be a valid AsyncAPI server object.
        "SERVERS": {
            "production": {
                "host": "api.example.com",
                "protocol": "wss",
            },
        },
    }

``SERVERS`` takes precedence over ``WS_HOST`` / ``WS_PROTOCOL``.
When ``SERVERS`` is ``None`` (the default) the views build the servers
block dynamically from the incoming request.
"""

from __future__ import annotations

from django.conf import settings
from django.test.signals import setting_changed

_DEFAULTS: dict = {
    # AsyncAPI info object fields
    "TITLE": "WebSocket API",
    "VERSION": "1.0.0",
    "DESCRIPTION": "",
    # Channel this consumer is mounted at — used as the channel address
    # in the spec and as the default for AsyncAPISpecView.
    "CHANNEL_PATH": "/",
    # Optional static servers block.  None → views derive from request.
    "SERVERS": None,
    # Derived server fields used when SERVERS is None.
    "WS_HOST": None,      # defaults to request.get_host()
    "WS_PROTOCOL": None,  # defaults to "wss" if HTTPS else "ws"
    # Set AUTH_QUERY_PARAM to the query parameter name used for token
    # auth (e.g. "token") to add an httpApiKey scheme to the spec.
    # Set AUTH_COOKIE_NAME to the cookie name used for session auth
    # (e.g. "sessionid") to add a cookie security scheme.
    # Both are also used by the try-it-out panel's auth selector.
    "AUTH_QUERY_PARAM": None,
    "AUTH_COOKIE_NAME": None,
    # Renders the interactive try-it-out panel in the HTML viewer.
    "TRY_IT_OUT_ENABLED": False,
    # When True, the try-it-out drawer starts open on page load.
    # When False (default) it starts collapsed — click the FAB to open.
    "TRY_IT_OUT_EXPANDED": False,
}

_SETTING_KEY = "CHANNELS_SPECTACULAR_SETTINGS"


class _ChannelsSpectacularSettings:
    """Lazy proxy over ``settings.CHANNELS_SPECTACULAR_SETTINGS``."""

    def __init__(self, defaults: dict) -> None:
        self._defaults = defaults

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._defaults:
            raise AttributeError(
                f"Invalid channels_spectacular setting: {name!r}"
            )
        user = getattr(settings, _SETTING_KEY, {})
        return user.get(name, self._defaults[name])

    def reload(self) -> None:
        """No-op; reads live from Django settings on every access."""


spectacular_settings = _ChannelsSpectacularSettings(_DEFAULTS)


def _reload_settings(*, setting, **_kwargs):
    if setting == _SETTING_KEY:
        spectacular_settings.reload()


setting_changed.connect(_reload_settings)
