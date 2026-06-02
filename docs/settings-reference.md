# Settings reference

All settings are placed under the `CHANNELS_SPECTACULAR_SETTINGS` dict in
your Django settings file.

```python
CHANNELS_SPECTACULAR_SETTINGS = {
    # key: default_value
}
```

## Full reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `TITLE` | `str` | `"WebSocket API"` | Title used in the AsyncAPI `info` block and the HTML `<title>` |
| `VERSION` | `str` | `"1.0.0"` | API version in the `info` block |
| `DESCRIPTION` | `str` | `""` | Markdown description in the `info` block |
| `CHANNEL_PATH` | `str` | `"/"` | Default WebSocket path used when `channel_path` is not passed to a view or the export command |
| `SERVERS` | `dict \| None` | `None` | Verbatim AsyncAPI `servers` block. When `None`, the block is derived from the request. |
| `WS_HOST` | `str \| None` | `None` | Override host when `SERVERS` is `None`. Falls back to `request.get_host()`. |
| `WS_PROTOCOL` | `"ws" \| "wss" \| None` | `None` | Override protocol when `SERVERS` is `None`. Falls back to `"wss"` if HTTPS else `"ws"`. |
| `AUTH_QUERY_PARAM` | `str \| None` | `None` | Query parameter name for token auth (e.g. `"token"`). When set, adds an `httpApiKey` security scheme to the spec and labels the try-it-out auth selector. |
| `AUTH_COOKIE_NAME` | `str \| None` | `None` | Cookie name for JWT cookie auth (e.g. `"access_token"`). When set, adds a cookie security scheme to the spec. The try-it-out panel uses this as the default cookie name input. |
| `TRY_IT_OUT_ENABLED` | `bool` | `False` | Show the interactive WebSocket console in the docs viewer. Keep `False` in production. |
| `TRY_IT_OUT_EXPANDED` | `bool` | `False` | When `True`, the try-it-out drawer starts open on every page load. When `False` (default), it starts collapsed — click the floating button to open. |

## Example: production + dev split

```python
# settings/base.py
CHANNELS_SPECTACULAR_SETTINGS = {
    "TITLE": "Dispatch API",
    "VERSION": "1.0.0",
    "DESCRIPTION": "Real-time ride and delivery dispatch over WebSocket.",
    "CHANNEL_PATH": "/ws/dispatch/",
    "TRY_IT_OUT_ENABLED": False,
}

# settings/dev.py
CHANNELS_SPECTACULAR_SETTINGS = {
    **CHANNELS_SPECTACULAR_SETTINGS,
    "WS_HOST": "localhost:8000",
    "WS_PROTOCOL": "ws",
    "TRY_IT_OUT_ENABLED": True,
}

# settings/prod.py
CHANNELS_SPECTACULAR_SETTINGS = {
    **CHANNELS_SPECTACULAR_SETTINGS,
    "SERVERS": {
        "production": {
            "host": "api.example.com",
            "protocol": "wss",
            "description": "Production WebSocket server",
        },
    },
}
```
