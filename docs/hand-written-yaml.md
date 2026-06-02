# Hand-written YAML support

If your project already has a hand-maintained AsyncAPI YAML file (or a
Django template that outputs one), you can use `export_asyncapi --template`
to post-process it instead of annotating the consumer with decorators.

## When to use this approach

- You have an existing asyncapi.yaml that you want to keep as the canonical
  source rather than migrating to decorators.
- Your WS protocol is too dynamic or polymorphic to express cleanly via
  `@document_action` / `@document_event`.
- You want human-authored narrative (examples, markdown descriptions) that
  are hard to embed in Python annotations.

## Django template variables

The command substitutes these placeholders before parsing the YAML:

| Placeholder | Replaced with |
|-------------|--------------|
| `{{ WS_HOST }}` | `--host` value or `CHANNELS_SPECTACULAR_SETTINGS["WS_HOST"]` |
| `{{ WS_PROTOCOL }}` | `--protocol` value or `CHANNELS_SPECTACULAR_SETTINGS["WS_PROTOCOL"]` |
| `{{ ws_host }}` | same (lowercase variant) |
| `{{ ws_protocol }}` | same (lowercase variant) |

Example template snippet:

```yaml
servers:
  default:
    host: "{{ WS_HOST }}"
    protocol: "{{ WS_PROTOCOL }}"
    pathname: /ws/dispatch/
```

Rendered with `--host localhost:8000 --protocol ws`:

```yaml
servers:
  default:
    host: "localhost:8000"
    protocol: "ws"
    pathname: /ws/dispatch/
```

## Payload title injection

`@asyncapi/generator` (Modelina) names a TypeScript interface after the
schema's `title` field. Hand-written specs often define payload schemas
inline without a `title`, which causes Modelina to fall back to
`AnonymousSchema_N`.

`export_asyncapi --template` walks every entry in `components.messages`
and injects a `title` derived from the message `name` field, for any
payload that doesn't already have one.

For example, if a message is named `request_ride` and its payload has no explicit `title`, the command injects `title: RequestRide` automatically, so the generated TypeScript interface comes out as `RequestRide` instead of `AnonymousSchema_12`.

To set an explicit title (and prevent auto-injection), add it directly in
the source YAML:

```yaml
components:
  messages:
    request_ride:
      name: request_ride
      payload:
        title: RequestRide   # explicit — won't be overwritten
        type: object
        properties:
          ...
```

## Example

```bash
python manage.py export_asyncapi \
    --template rides/templates/rides/asyncapi.yaml \
    --output docs/asyncapi.yaml \
    --host localhost:8000 \
    --protocol ws
```

The `docs/asyncapi.yaml` output can then be fed to `@asyncapi/cli` for
SDK generation or served directly by `AsyncAPIDocView(spec_url=...)`.
