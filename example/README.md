# Chat example

A minimal real-time group chat app that shows `django-channels-spectacular`
in action. Join a named room, send messages, and receive live broadcasts from
other connected users — all documented with an auto-generated AsyncAPI 3.0 spec.

## Quick start

```bash
# 1. From the repo root, install the package in development mode
pip install -e ..

# 2. Install example dependencies
pip install -r requirements.txt

# 3. Run migrations (creates db.sqlite3)
python manage.py migrate

# 4. Start the ASGI server
daphne -p 8000 chat_project.asgi:application
```

Then open:

| URL | What it is |
|-----|-----------|
| `http://localhost:8000/` | Chat UI |
| `http://localhost:8000/ws-docs/` | AsyncAPI docs viewer (spec-switcher dropdown) |
| `http://localhost:8000/ws-docs/chat/asyncapi.yaml` | Raw Chat spec |
| `http://localhost:8000/ws-docs/notifications/asyncapi.yaml` | Raw Notifications spec |
| `http://localhost:8000/ws-docs/merged/asyncapi.yaml` | Both consumers merged into one spec |

## Testing multi-user chat

Open two browser tabs at `http://localhost:8000/`, pick different usernames,
join the same room, and send messages. You can also use the try-it-out panel
in the docs viewer to send raw JSON payloads.

## How it maps to channels-spectacular

The `ChatConsumer` in `chat/consumers.py` uses three decorators:

```python
@document_action(summary="Join a chat room", payload=JoinPayload, ...)
async def handle_join(self, content): ...

@document_action(summary="Send a message to the room", payload=SendMessagePayload, ...)
async def handle_send_message(self, content): ...

@document_event("message.new", summary="A message was posted", payload=MessageNewPayload, ...)
async def message_new(self, event): ...
```

`AsyncAPISpecView` reads those annotations at request time and builds the spec —
no YAML to write by hand.
