# Export command

`manage.py export_asyncapi` writes the AsyncAPI spec to a YAML file. It has
two mutually exclusive modes.

## Generator mode from annotated consumers

```bash
# Single consumer
python manage.py export_asyncapi \
    --consumer myapp.consumers.DispatchConsumer:/ws/dispatch/ \
    --output docs/asyncapi.yaml

# Multiple consumers merged into one spec
python manage.py export_asyncapi \
    --consumer myapp.consumers.RideConsumer:/ws/rides/ \
    --consumer myapp.consumers.NotifConsumer:/ws/notifications/ \
    --output docs/asyncapi.yaml
```

The `--consumer` flag accepts a `dotted.import.path` optionally followed by `:/ws/channel/path/`. When the channel path is omitted, it falls back to `CHANNELS_SPECTACULAR_SETTINGS["CHANNEL_PATH"]`. The flag is repeatable, so each additional `--consumer` merges another consumer into the same spec.

## Template mode from a hand-written YAML

```bash
python manage.py export_asyncapi \
    --template rides/templates/rides/asyncapi.yaml \
    --output docs/asyncapi.yaml \
    --host localhost:8000 \
    --protocol ws
```

The command:
1. Reads the source file and substitutes `{{ WS_HOST }}` / `{{ WS_PROTOCOL }}`
   (and their uppercase `{{ WS_HOST }}` / `{{ WS_PROTOCOL }}` variants).
2. Parses the substituted YAML.
3. Walks `components.messages` and injects a `title` into any payload schema
   that has a message `name` but no explicit `title`. This prevents
   `@asyncapi/generator` (Modelina) from naming TypeScript types
   `AnonymousSchema_N`.
4. Writes the final YAML to `--output`.

## Flag reference

| Flag | Default | Description |
|------|---------|-------------|
| `--consumer DOTTED.PATH[:/ws/path/]` | - | Annotated consumer. Repeatable. Mutually exclusive with `--template`. |
| `--template FILE` | - | Hand-written YAML template. Mutually exclusive with `--consumer`. |
| `-o / --output FILE` | `asyncapi.yaml` | Destination path. Parent dirs are created automatically. |
| `--host HOST` | settings / `localhost:8000` | WS host for the `servers` block. |
| `--protocol {ws,wss}` | settings / `ws` | WS protocol. |

## Consuming the spec from a React app

The exported `asyncapi.yaml` is the contract your frontend builds against. Generate TypeScript models from it using the [AsyncAPI CLI](https://www.asyncapi.com/tools/cli), which wraps [Modelina](https://github.com/asyncapi/modelina) under the hood, then drive a typed WebSocket hook with those models. Regenerate whenever your consumers change and any breaking changes will surface at compile time rather than at runtime.

### 1. Generate the TypeScript models

```bash
# Check the spec into your frontend repo, or pull it from the running server:
#   curl http://localhost:8000/ws-docs/chat/asyncapi.yaml -o asyncapi.yaml

npx @asyncapi/cli generate models typescript ./asyncapi.yaml \
    --output ./src/api/models \
    --tsModelType interface
```

Because the generator injects a `title` into every message payload (see step 3 of template mode above) along with a discriminator field (`action` for client-to-server messages, `type` for server-to-client), the output is a set of cleanly named interfaces with literal discriminators, ready to drop into a discriminated union.

```ts
// src/api/models/MessageNew.ts  (generated)
export interface MessageNew {
  type: "message.new";
  username: string;
  text: string;
  room: string;
}
```

### 2. A typed WebSocket hook

Wrap the browser `WebSocket` in a small hook. The generated interfaces type
both the events you receive and the actions you send, so the compiler catches
a misspelled action or a missing field before it ships:

```tsx
// src/api/useChatSocket.ts
import { useCallback, useEffect, useRef, useState } from "react";

import type { MessageNew } from "./models/MessageNew";
import type { UserJoined } from "./models/UserJoined";
import type { UserLeft } from "./models/UserLeft";

// Server → client events, discriminated on `type`.
type ServerEvent = MessageNew | UserJoined | UserLeft;

// Client → server actions, discriminated on `action`.
type ClientAction =
  | { action: "join"; username: string; room: string }
  | { action: "send_message"; text: string }
  | { action: "leave" };

export function useChatSocket(url: string, token?: string) {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<ServerEvent[]>([]);

  useEffect(() => {
    // Query-param JWT auth — matches AUTH_QUERY_PARAM in your settings.
    const fullUrl = token
      ? `${url}?token=${encodeURIComponent(token)}`
      : url;

    const socket = new WebSocket(fullUrl);
    ws.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (e) => {
      const event = JSON.parse(e.data) as ServerEvent;
      setEvents((prev) => [...prev, event]);
    };

    return () => socket.close();
  }, [url, token]);

  const send = useCallback((action: ClientAction) => {
    ws.current?.send(JSON.stringify(action));
  }, []);

  return { connected, events, send };
}
```

### 3. Use it in a component

The `type` discriminator lets TypeScript narrow each event inside the
`switch`, so `evt.text` is only reachable on a `message.new` event:

```tsx
// src/ChatRoom.tsx
import { useChatSocket } from "./api/useChatSocket";

export function ChatRoom({ token }: { token: string }) {
  const { connected, events, send } = useChatSocket(
    "ws://localhost:8000/ws/chat/",
    token,
  );

  return (
    <div>
      <p>{connected ? "● connected" : "○ disconnected"}</p>

      <button
        onClick={() =>
          send({ action: "join", username: "Alice", room: "general" })
        }
      >
        Join
      </button>
      <button onClick={() => send({ action: "send_message", text: "Hello!" })}>
        Send
      </button>

      <ul>
        {events.map((evt, i) => {
          switch (evt.type) {
            case "message.new":
              return <li key={i}>{evt.username}: {evt.text}</li>;
            case "user.joined":
              return <li key={i}>{evt.username} joined {evt.room}</li>;
            case "user.left":
              return <li key={i}>{evt.username} left {evt.room}</li>;
          }
        })}
      </ul>
    </div>
  );
}
```

Wire the model-generation step into your build (a `predev` / `prebuild` npm
script, or CI) so the frontend types always track the latest exported spec.
