# Try-it-out panel

The docs viewer includes an interactive WebSocket console that lets you
connect, send messages, and watch server events all from the browser,
without leaving the docs page.

## Enabling it

The panel is hidden by default. Enable it in your dev settings:

```python
# settings/dev.py
CHANNELS_SPECTACULAR_SETTINGS = {
    "TRY_IT_OUT_ENABLED": True,
}
```

**Keep it disabled in production.** The panel opens a live WebSocket
connection to whatever URL is in the input, enabling it on a public docs
page would let anyone connect to your production socket.

## What it does

Once enabled, a floating button appears which when clicked opens a fixed panel appears at the bottom-right of the viewer:

1. **WebSocket URL** pre-filled from the spec's `servers` block. In
   multi-consumer mode it updates automatically when you switch consumers.
2. **Auth method** choose how the connection authenticates: *Session
   cookie (auto)*, *Cookie JWT*, or *Query param*. See [Auth flow](#auth-flow)
   below.
3. **Connect / Disconnect** opens or closes the WebSocket.
4. **Action selector** a dropdown populated from the spec's `send`
   operations. Picking an action fills in a JSON template in the payload box.
5. **Payload** an editable JSON textarea.
6. **Send** sends `{"action": "<selected>", ...payload}` over the socket.
7. **Event log** scrollable log of outbound (blue) and inbound (green)
   messages, plus connection events and errors.

## Auth flow

The panel supports three authentication methods via the **Auth method**
selector:

**Session cookie (auto)** the default. The browser forwards your Django
session cookie (`sessionid`, or whatever `SESSION_COOKIE_NAME` is set to)
automatically on same-origin connections. No action is needed in the panel
just make sure you are logged in (e.g. to the Django admin) for the same
origin.

**Cookie JWT** for a JWT carried in a cookie. Enter the cookie name
(prefilled from `AUTH_COOKIE_NAME`, default `"access_token"`) and the token
value, then click **Apply**. The panel sets `<cookie name>=<token>` as a
same-origin cookie (`path=/; SameSite=Strict`) so the browser forwards it on
your next **Connect**; **Clear** deletes it.

**Query param** paste a token into the token input. On **Connect** it is
appended as `?<AUTH_QUERY_PARAM>=<token>` to the WebSocket URL (e.g.
`ws://localhost:8000/ws/?token=eyJ...`). The param name is taken from
`AUTH_QUERY_PARAM` in your settings (default `"token"`).

See [Authentication](authentication) for how to configure the corresponding
server-side middleware for each scheme.

## Multi-consumer mode

When `AsyncAPIDocView` is configured with `specs=[...]`, the try-it-out
panel's WebSocket URL updates automatically each time you switch consumers
from the dropdown. The URL is derived by fetching the newly selected spec
and reading `servers[0].protocol + "://" + servers[0].host + channels[0].address`.
