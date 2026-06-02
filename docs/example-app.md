# Example app

A complete, runnable Django project lives in the
[`example/`](https://github.com/ibukun-brain/django-channels-spectacular/tree/main/example)
directory of the repository. It is the fastest way to see every feature
working together against real consumers.

It ships two annotated consumers:

- **`ChatConsumer`** (`/ws/chat/`) — join rooms, send messages, and receive
  live broadcasts.
- **`NotificationConsumer`** (`/ws/notifications/`) — subscribe to per-user
  push notifications and mark them as read.

Between them they exercise multi-consumer specs, the spec-switcher dropdown,
the try-it-out console, and the query-param / cookie-JWT auth selector.

## Run it

```bash
# From the repo root, install the package in development mode
pip install -e .

# Then set up and start the example project
cd example
pip install -r requirements.txt
python manage.py migrate          # creates db.sqlite3
daphne -p 8000 chat_project.asgi:application
```

## What to open

| URL | What it is |
|-----|-----------|
| `http://localhost:8000/` | Chat UI — open two tabs to chat between users |
| `http://localhost:8000/ws-docs/` | AsyncAPI docs viewer with the spec-switcher dropdown |
| `http://localhost:8000/ws-docs/chat/asyncapi.yaml` | Raw Chat spec |
| `http://localhost:8000/ws-docs/notifications/asyncapi.yaml` | Raw Notifications spec |
| `http://localhost:8000/ws-docs/merged/asyncapi.yaml` | Both consumers merged into one spec |

In the docs viewer, use the **dropdown at the top** to switch between the
Chat, Notifications, and Merged specs — the try-it-out panel's WebSocket URL
updates to match. Open the panel and try the **Auth method** selector to see
the session-cookie, cookie-JWT, and query-param flows.

## How it maps to the library

Each documented method on a consumer carries a decorator:

```python
@document_action(summary="Join a chat room", payload=JoinPayload, ...)
async def handle_join(self, content): ...

@document_event("message.new", summary="A message was posted",
                payload=MessageNewPayload, ...)
async def message_new(self, event): ...
```

The merged spec and switcher are wired in `chat_project/urls.py`:

```python
path(
    "ws-docs/merged/asyncapi.yaml",
    AsyncAPISpecView.as_view(consumers=[
        (ChatConsumer, "/ws/chat/"),
        (NotificationConsumer, "/ws/notifications/"),
    ]),
),
path(
    "ws-docs/",
    AsyncAPIDocView.as_view(specs=[
        ("Chat  /ws/chat/", "/ws-docs/chat/asyncapi.yaml"),
        ("Notifications  /ws/notifications/", "/ws-docs/notifications/asyncapi.yaml"),
        ("Merged (both consumers)", "/ws-docs/merged/asyncapi.yaml"),
    ]),
),
```

See {doc}`multi-consumer` for the full multi-consumer walkthrough,
{doc}`authentication` for the auth schemes, and {doc}`export-command` for
generating a typed TypeScript client from the exported spec.
