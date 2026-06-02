# Authentication

WebSocket handshakes start life as standard HTTP upgrade requests, which means any authentication mechanism that works in a regular Django view will work just as well within the Channels ASGI stack. The only requirement is that your authentication logic runs as ASGI middleware before the connection reaches your consumer.

This guide walks through the three authentication patterns the try-it-out panel supports: session cookie, JWT-in-cookie, and JWT-in-query-param, how to describe each one in your AsyncAPI spec, and how to use the built-in try-it-out panel to test them.


---

## Session authentication

The browser sends all cookies, including Django's `sessionid`, automatically
on same-origin WebSocket connections. No extra work is needed on the client
side. On the server, wire `SessionMiddlewareStack` (or the lower-level
`AuthMiddlewareStack`) around your ASGI application:

```python
# myproject/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from myapp.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

`AuthMiddlewareStack` reads the `sessionid` cookie from the WebSocket handshake headers, looks up the session in the database, and populates `scope["user"]` with the same user object you would get from `request.user` in a regular view.

Inside your consumer:

```python
class DispatchConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        await self.accept()
```

Cookie auth is the browser default for a reason: the browser enforces the same same-origin policy on cookies as it does on regular HTTP requests, so a production site on `https://api.example.com` will naturally send the `sessionid` cookie for that origin whenever the page opens a WebSocket to the same host.

---

## Cookie JWT authentication

If you issue JWTs but want to keep them out of the URL, store the token in a cookie (for example `access_token`) instead of the `sessionid` session cookie. The browser forwards the cookie on the handshake exactly like `sessionid`, but your middleware decodes it as a JWT rather than looking up a database session, so you get stateless auth without exposing the token in the WebSocket URL.

This is also a natural fit when your frontend and backend share the same domain through a reverse proxy. In that setup, the browser handles the cookie automatically with no extra client-side wiring needed.

That said, any cookie carrying an auth token should be treated as a sensitive credential. Set `HttpOnly` to prevent JavaScript from reading the token directly, Secure to ensure it is only transmitted over HTTPS, and `SameSite=Strict` (or `Lax` if your setup requires cross-site navigation) to cut off the most common CSRF vectors. If your threat model calls for an extra layer, pair the cookie with a CSRF token validated in your middleware before the WebSocket upgrade is accepted.

Set `AUTH_COOKIE_NAME` to the cookie that carries the token:

```python
# settings.py
CHANNELS_SPECTACULAR_SETTINGS = {
    "AUTH_COOKIE_NAME": "access_token",
}
```

Write a middleware that reads the cookie from the handshake headers and decodes
it. Reuse the `get_user_from_token` helper from the query-param section below:

```python
# myapp/middleware.py
from http.cookies import SimpleCookie

from django.contrib.auth.models import AnonymousUser


class CookieJWTAuthMiddleware:
    """
    Reads a JWT from the `access_token` cookie and populates scope["user"].

    Falls back to AnonymousUser when the cookie is absent or the token is
    invalid/expired.
    """

    cookie_name = "access_token"

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            token = None
            for name, value in scope.get("headers", []):
                if name == b"cookie":
                    cookies = SimpleCookie()
                    cookies.load(value.decode())
                    morsel = cookies.get(self.cookie_name)
                    token = morsel.value if morsel else None
                    break
            scope["user"] = (
                await get_user_from_token(token)
                if token
                else AnonymousUser()
            )
        return await self.inner(scope, receive, send)
```

Wire it into your ASGI stack:

```python
# myproject/asgi.py
from myapp.middleware import CookieJWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": CookieJWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
```

Cookie JWT vs. session cookie: both ride on a cookie the browser sends automatically, so neither requires the client to touch the WebSocket URL. The difference is entirely server-side. `sessionid` triggers a database-backed session lookup, while the JWT cookie is decoded statelessly in memory. Reach for the JWT cookie when you want the stateless benefits of a token without giving up the transport convenience of a cookie.

---

## Query parameter authentication

Some mobile apps, CLI tools, and API clients running outside a browser cannot set
cookies. The conventional workaround is to attach a short-lived token as a URL
query parameter:

```
wss://api.example.com/ws/dispatch/?token=<jwt>
```

Write an ASGI middleware that reads the token from `scope["query_string"]` and
authenticates the user before the consumer runs:

```python
# myapp/middleware.py
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

import jwt  # PyJWT


@database_sync_to_async
def get_user_from_token(token: str):
    """Decode a JWT and return the Django user, or AnonymousUser on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.get(pk=payload["user_id"])
    except Exception:
        return AnonymousUser()


class QueryTokenAuthMiddleware:
    """
    Reads `?token=<jwt>` from the WebSocket URL and populates scope["user"].

    Falls back to AnonymousUser when the parameter is absent or the token
    is invalid/expired.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            qs = parse_qs(scope["query_string"].decode())
            token = qs.get("token", [None])[0]
            scope["user"] = (
                await get_user_from_token(token)
                if token
                else AnonymousUser()
            )
        return await self.inner(scope, receive, send)
```

Wire the middleware into your ASGI stack:

```python
# myproject/asgi.py
from myapp.middleware import QueryTokenAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": QueryTokenAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
```

### Combining both schemes

If you need to support both browser users and API clients, stack the middlewares: check the query param first and fall back to the session cookie. This way, browser-based connections authenticate silently through the cookie while API clients pass a token explicitly in the URL:

```python
# myapp/middleware.py  (extended)
from channels.auth import AuthMiddlewareStack

def TokenOrSessionAuthMiddlewareStack(inner):
    """Query-param jwt token auth, with session cookie as fallback."""
    return QueryTokenAuthMiddleware(AuthMiddlewareStack(inner))

def TokenOrSessionAuthMiddlewareStack(inner):
    """Cookie jwt token auth, with session cookie as fallback."""
    return CookieJWTAuthMiddleware(AuthMiddlewareStack(inner))
```

```python
# myproject/asgi.py
from myapp.middleware import TokenOrSessionAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenOrSessionAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

---

## Documenting auth in the spec

Set one or both of these settings and the generator will add the corresponding
`securitySchemes` to the spec's `components` block:

```python
# settings.py
CHANNELS_SPECTACULAR_SETTINGS = {
    # Enables the httpApiKey query-param scheme in the spec.
    # Must match the parameter name your middleware reads.
    "AUTH_QUERY_PARAM": "token",

    # Enables the cookie scheme in the spec.
    # Must match the cookie name your middleware reads (a JWT cookie like
    # "access_token", or "sessionid" for Django session auth).
    "AUTH_COOKIE_NAME": "access_token",
}
```

The generated spec will include:

```yaml
components:
  securitySchemes:
    queryToken:
      type: httpApiKey
      in: query
      name: token
    cookieJWT:
      type: httpApiKey
      in: cookie
      name: access_token
```

```{note}
The schemes are declared under `components.securitySchemes` only and are not attached as a `security` requirement on the `servers` block. AsyncAPI 3.0 requires server `security` entries to be full security-scheme objects rather than the AsyncAPI 2.x `{schemeName: []}` shorthand, and including them on the server block tends to trip up strict spec validators in the viewer. Keeping the declarations in `components` documents the available auth methods without breaking validation.
```

---

## Try-it-out panel

When `TRY_IT_OUT_ENABLED` is `True`, the panel shows an **Auth method**
selector with three options:

| Option | Behaviour |
|--------|-----------|
| **Session cookie (auto)** | Shows a note that the browser forwards the session cookie automatically. No action needed just make sure you are logged in on the same origin. |
| **Cookie JWT** | Shows a cookie-name input (prefilled from `AUTH_COOKIE_NAME`) and a token input. Clicking **Apply** sets `<cookie name>=<token>` as a same-origin cookie so the browser forwards it on the next Connect; **Clear** deletes it. |
| **Query param** | Shows a token input. The token is appended as `?<AUTH_QUERY_PARAM>=<token>` to the WebSocket URL when you click Connect. |

The param and cookie names in the dropdown labels are read from
`AUTH_QUERY_PARAM` and `AUTH_COOKIE_NAME` in `CHANNELS_SPECTACULAR_SETTINGS`
(defaults: `"token"` and `"access_token"`).
