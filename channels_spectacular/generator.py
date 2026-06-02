"""
AsyncAPI 3.0 spec generator.

Given one or more Django Channels consumer classes whose methods are
annotated with :func:`~channels_spectacular.decorators.document_action`
and :func:`~channels_spectacular.decorators.document_event`, builds a
complete AsyncAPI 3.0 specification as a Python dict (and optionally
as YAML).

All configuration has a sensible default in ``CHANNELS_SPECTACULAR_SETTINGS``
so that passing arguments to the generator is optional.

Example — single consumer (all config from settings)::

    generator = AsyncAPIGenerator(DispatchConsumer)
    yaml_text = generator.get_yaml()

Example — single consumer with explicit overrides::

    generator = AsyncAPIGenerator(
        DispatchConsumer,
        info={"title": "Dispatch API", "version": "2.0.0"},
        servers={"prod": {"host": "api.example.com", "protocol": "wss"}},
        channel_path="/ws/dispatch/",
    )

Example — multiple consumers in one spec::

    generator = AsyncAPIGenerator(
        consumers=[
            (RideConsumer, "/ws/rides/"),
            (NotificationConsumer, "/ws/notifications/"),
        ],
        info={"title": "My API", "version": "1.0.0"},
        servers={"prod": {"host": "api.example.com", "protocol": "wss"}},
    )

In multi-consumer mode every message name and operation ID is prefixed
with a short CamelCase label derived from the last path segment of each
consumer's channel (e.g. ``/ws/rides/`` → ``Rides``), so
``request_ride`` becomes ``rides_request_ride`` and ``RequestRide``
becomes ``RidesRequestRide``.

Definition order
----------------
Operations appear in the spec in the order the methods are defined on
the consumer class.  ``inspect.getmembers`` sorts alphabetically, so
we walk ``cls.__dict__`` through the MRO (subclass methods first) to
preserve declaration order.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from channels_spectacular.decorators import (ASYNCAPI_ACTION_ATTR,
                                             ASYNCAPI_EVENT_ATTR)
from channels_spectacular.plumbing.schema_utils import extract_schema
from channels_spectacular.settings import spectacular_settings


def _to_camel(name: str) -> str:
    """``request_ride`` → ``RequestRide``.  ``ride.offer`` → ``RideOffer``."""
    return "".join(w.capitalize() for w in re.split(r"[_.\-]", name))


def _json_ptr_encode(path: str) -> str:
    """Encode a path for use inside a JSON Pointer ``$ref`` string."""
    return path.replace("~", "~0").replace("/", "~1")


def _channel_ref(channel_path: str) -> str:
    return f"#/channels/{_json_ptr_encode(channel_path)}"


def _channel_prefix(channel_path: str) -> str:
    """CamelCase prefix from the last non-empty segment of *channel_path*.

    Used in multi-consumer mode to namespace message names and operation IDs
    so they remain unique across channels.

    Examples::

        /ws/rides/          -> "Rides"
        /ws/notifications/  -> "Notifications"
        /ws/v1/chat/        -> "Chat"
        /ws/                -> "Ws"
        /                   -> "Root"
    """
    parts = [p for p in channel_path.split("/") if p]
    return _to_camel(parts[-1]) if parts else "Root"


def _collect_annotated(consumer: type, attr: str) -> list[dict]:
    """
    Walk the MRO in definition order and collect metadata dicts stored
    under *attr* on each method.

    Uses ``cls.__dict__`` (ordered dict in CPython 3.7+) rather than
    ``inspect.getmembers`` so that operations appear in the spec in the
    same order they were written in the source file.

    Args:
        consumer: The consumer class to introspect.
        attr: Private sentinel attribute name to look for.

    Returns:
        Metadata dicts, deduplicated by primary key (``action`` for
        actions, ``event_type`` for events), in definition order.
    """
    # Pass 1 (forward MRO — subclass first): resolve which meta wins per key.
    # The first class encountered owns the key; because MRO is subclass-first,
    # subclass overrides shadow parent definitions.
    winning: dict[str, dict] = {}
    for cls in consumer.__mro__:
        for _name, obj in cls.__dict__.items():
            meta = getattr(obj, attr, None)
            if meta is None:
                continue
            key = meta.get("action") or meta.get("event_type", "")
            if key and key not in winning:
                winning[key] = meta

    # Pass 2 (reversed MRO — base class first): emit in definition order,
    # but use the winning (subclass) metadata so summaries/payloads reflect
    # overrides even when ordering follows the parent's declaration position.
    seen: set[str] = set()
    results: list[dict] = []
    for cls in reversed(consumer.__mro__):
        for _name, obj in cls.__dict__.items():
            meta = getattr(obj, attr, None)
            if meta is None:
                continue
            key = meta.get("action") or meta.get("event_type", "")
            if key and key not in seen:
                seen.add(key)
                results.append(winning[key])

    return results


class AsyncAPIGenerator:
    """
    Generates an AsyncAPI 3.0 specification from one or more annotated
    consumers.

    All constructor arguments are optional and fall back to
    ``CHANNELS_SPECTACULAR_SETTINGS`` when omitted.

    Single-consumer form (backwards-compatible)::

        AsyncAPIGenerator(MyConsumer, channel_path="/ws/my/")

    Multi-consumer form::

        AsyncAPIGenerator(
            consumers=[
                (RideConsumer, "/ws/rides/"),
                (NotificationConsumer, "/ws/notifications/"),
            ],
        )

    Args:
        consumer: Single consumer class.  Mutually exclusive with
            ``consumers``.
        consumers: List of ``(consumer_class, channel_path)`` pairs for
            a multi-channel spec.  Mutually exclusive with ``consumer``.
        info: AsyncAPI ``info`` object dict.  Defaults to
            ``{"title": TITLE, "version": VERSION,
            "description": DESCRIPTION}`` from settings.
        servers: AsyncAPI ``servers`` mapping.  Defaults to
            ``SERVERS`` from settings (``None`` means the caller —
            typically the view — should supply request-derived values).
        channel_path: WebSocket URL path for the single consumer.
            Ignored when ``consumers`` is provided.
            Defaults to ``CHANNEL_PATH`` from settings.
    """

    def __init__(
        self,
        consumer: type | None = None,
        *,
        consumers: list[tuple[type, str]] | None = None,
        info: dict | None = None,
        servers: dict | None = None,
        channel_path: str | None = None,
    ) -> None:
        if consumers is not None:
            self._consumers: list[tuple[type, str]] = list(consumers)
        elif consumer is not None:
            resolved_path = (
                channel_path
                if channel_path is not None
                else spectacular_settings.CHANNEL_PATH
            )
            self._consumers = [(consumer, resolved_path)]
        else:
            raise ValueError("Provide either `consumer` or `consumers`.")

        # Expose single-consumer attrs for backwards compatibility.
        if len(self._consumers) == 1:
            self.consumer, self.channel_path = self._consumers[0]

        self.info = info or self._default_info()
        self.servers = (
            servers
            if servers is not None
            else (spectacular_settings.SERVERS or {})
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_spec(self) -> dict:
        """Return the full AsyncAPI 3.0 spec as a Python dict."""
        use_prefix = len(self._consumers) > 1

        all_channels: dict[str, Any] = {}
        all_operations: dict[str, Any] = {}
        all_messages: dict[str, Any] = {}

        for consumer, channel_path in self._consumers:
            prefix = _channel_prefix(channel_path) if use_prefix else None
            actions = _collect_annotated(consumer, ASYNCAPI_ACTION_ATTR)
            events = _collect_annotated(consumer, ASYNCAPI_EVENT_ATTR)

            messages = self._build_component_messages(
                actions, events, prefix=prefix
            )
            channel_msgs = {
                name: {"$ref": f"#/components/messages/{name}"}
                for name in messages
            }
            operations = self._build_operations(
                actions, events, channel_path, prefix=prefix
            )

            all_channels[channel_path] = {
                "address": channel_path,
                "messages": channel_msgs,
            }
            all_messages.update(messages)
            all_operations.update(operations)

        spec: dict[str, Any] = {
            "asyncapi": "3.0.0",
            "info": self.info,
        }
        if self.servers:
            spec["servers"] = self.servers
        spec["channels"] = all_channels
        spec["operations"] = all_operations

        # Merge messages and security schemes under components.
        components: dict[str, Any] = {}
        if all_messages:
            components["messages"] = all_messages
        sec_schemes = self._build_security_schemes()
        if sec_schemes:
            components["securitySchemes"] = sec_schemes
        if components:
            spec["components"] = components

        return spec

    def get_yaml(self) -> str:
        """Return the spec as a YAML string."""
        dumper = yaml.Dumper
        # Use literal block scalars (|) for multiline strings so that blank
        # lines inside descriptions don't produce invalid single-quoted flow
        # scalars that break strict YAML parsers.
        dumper.add_representer(str, _literal_str_representer)
        return yaml.dump(
            self.get_spec(),
            Dumper=dumper,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    # ------------------------------------------------------------------
    # Spec assembly
    # ------------------------------------------------------------------

    def _build_component_messages(
        self,
        actions: list[dict],
        events: list[dict],
        *,
        prefix: str | None = None,
    ) -> dict[str, dict]:
        messages: dict[str, dict] = {}

        for meta in actions:
            name = _to_camel(meta["action"])
            if prefix:
                name = f"{prefix}{name}"
            payload = extract_schema(meta["payload"])
            payload = _inject_discriminator(payload, "action", meta["action"])
            messages[name] = _message_entry(meta, payload)

        for meta in events:
            name = _to_camel(meta["event_type"])
            if prefix:
                name = f"{prefix}{name}"
            payload = extract_schema(meta["payload"])
            payload = _inject_discriminator(
                payload, "type", meta["event_type"]
            )
            messages[name] = _message_entry(meta, payload)

        return messages

    def _build_operations(
        self,
        actions: list[dict],
        events: list[dict],
        channel_path: str,
        *,
        prefix: str | None = None,
    ) -> dict[str, dict]:
        ch_ref = _channel_ref(channel_path)
        encoded = _json_ptr_encode(channel_path)
        ops: dict[str, dict] = {}

        for meta in actions:
            op_id = meta["action"]
            msg_name = _to_camel(op_id)
            if prefix:
                op_id = f"{prefix.lower()}_{op_id}"
                msg_name = f"{prefix}{msg_name}"
            msg_ref = f"#/channels/{encoded}/messages/{msg_name}"
            ops[op_id] = _operation_entry(
                direction="send",
                channel_ref=ch_ref,
                msg_ref=msg_ref,
                meta=meta,
            )

        for meta in events:
            op_id = meta["event_type"].replace(".", "_")
            msg_name = _to_camel(meta["event_type"])
            if prefix:
                op_id = f"{prefix.lower()}_{op_id}"
                msg_name = f"{prefix}{msg_name}"
            msg_ref = f"#/channels/{encoded}/messages/{msg_name}"
            ops[op_id] = _operation_entry(
                direction="receive",
                channel_ref=ch_ref,
                msg_ref=msg_ref,
                meta=meta,
            )

        return ops

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_security_schemes() -> dict[str, dict]:
        """Build AsyncAPI ``securitySchemes`` from auth settings.

        Returns an empty dict when neither ``AUTH_QUERY_PARAM`` nor
        ``AUTH_COOKIE_NAME`` is configured, so no ``securitySchemes``
        key appears in the spec.
        """
        schemes: dict[str, dict] = {}
        if spectacular_settings.AUTH_QUERY_PARAM:
            schemes["queryToken"] = {
                "type": "httpApiKey",
                "in": "query",
                "name": spectacular_settings.AUTH_QUERY_PARAM,
            }
        if spectacular_settings.AUTH_COOKIE_NAME:
            # Keyed ``cookieJWT`` because AUTH_COOKIE_NAME carries a token
            # cookie (e.g. ``access_token``), distinct from Django's
            # automatic ``sessionid`` session cookie.  AsyncAPI models both
            # as ``httpApiKey`` ``in: cookie``; only the name differs.
            schemes["cookieJWT"] = {
                "type": "httpApiKey",
                "in": "cookie",
                "name": spectacular_settings.AUTH_COOKIE_NAME,
            }
        return schemes

    @staticmethod
    def _default_info() -> dict:
        info: dict[str, str] = {
            "title": spectacular_settings.TITLE,
            "version": spectacular_settings.VERSION,
        }
        if spectacular_settings.DESCRIPTION:
            info["description"] = spectacular_settings.DESCRIPTION
        return info


# ---------------------------------------------------------------------------
# Module-level helpers (also used by tests)
# ---------------------------------------------------------------------------

def _literal_str_representer(dumper: yaml.Dumper, data: str):
    """Use literal block style (|) for multiline strings.

    PyYAML's default single-quoted flow scalar puts blank lines *inside*
    the quoted block, which strict YAML 1.2 parsers (including the
    AsyncAPI viewer) reject with "multiple documents" errors.
    """
    if "\n" in data:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style="|"
        )
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def _message_entry(meta: dict, payload: dict) -> dict:
    entry: dict[str, Any] = {"payload": payload}
    if meta.get("summary"):
        entry["summary"] = meta["summary"]
    if meta.get("description"):
        entry["description"] = meta["description"]
    if meta.get("deprecated"):
        entry["deprecated"] = True
    if meta.get("tags"):
        entry["tags"] = [{"name": t} for t in meta["tags"]]
    if meta.get("examples"):
        entry["examples"] = meta["examples"]
    return entry


def _operation_entry(
    *,
    direction: str,
    channel_ref: str,
    msg_ref: str,
    meta: dict,
) -> dict:
    op: dict[str, Any] = {
        "action": direction,
        "channel": {"$ref": channel_ref},
        "messages": [{"$ref": msg_ref}],
    }
    if meta.get("summary"):
        op["summary"] = meta["summary"]
    if meta.get("description"):
        op["description"] = meta["description"]
    if meta.get("deprecated"):
        op["deprecated"] = True
    if meta.get("tags"):
        op["tags"] = [{"name": t} for t in meta["tags"]]
    return op


def _inject_discriminator(schema: dict, field: str, value: str) -> dict:
    """
    Ensure the payload schema has a ``field`` property with
    ``const: value`` as its first property.

    Always returns a new dict; never mutates the input.
    """
    if not schema:
        schema = {"type": "object", "properties": {}}

    schema = dict(schema)
    discriminator = {field: {"type": "string", "const": value}}
    discriminator.update(schema.get("properties", {}))
    schema["properties"] = discriminator

    if "type" not in schema:
        schema["type"] = "object"

    return schema
