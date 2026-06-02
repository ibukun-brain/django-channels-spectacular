"""
Management command: export_asyncapi

Exports the AsyncAPI 3.0 spec to a YAML file.  Two modes:

**Generator mode** (``--consumer``)
    Generates the spec from a consumer class annotated with
    ``@document_action`` / ``@document_event``, then writes it to a file.
    This is the primary use-case for projects that drive their spec from
    decorator annotations.

    Single consumer::

        python manage.py export_asyncapi \\
            --consumer myapp.consumers.DispatchConsumer:/ws/dispatch/ \\
            --output docs/asyncapi.yaml

    Multiple consumers in one spec::

        python manage.py export_asyncapi \\
            --consumer myapp.consumers.RideConsumer:/ws/rides/ \\
            --consumer myapp.consumers.NotifConsumer:/ws/notifications/ \\
            --output docs/asyncapi.yaml

**Template mode** (``--template``)
    Renders an existing hand-written AsyncAPI YAML template.  Django-style
    ``{{ WS_HOST }}`` / ``{{ WS_PROTOCOL }}`` placeholders are substituted
    with values from ``CHANNELS_SPECTACULAR_SETTINGS`` (or ``--host`` /
    ``--protocol`` overrides).  Payload schemas that have a message
    ``name`` but no ``title`` receive one automatically, which prevents
    AsyncAPI SDK generators from falling back to ``AnonymousSchema_N``
    type names.

    Example::

        python manage.py export_asyncapi \\
            --template rides/templates/rides/asyncapi.yaml \\
            --output docs/asyncapi.yaml \\
            --host localhost:8000 \\
            --protocol ws
"""

from __future__ import annotations

import pathlib
import re

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string

from channels_spectacular.generator import AsyncAPIGenerator
from channels_spectacular.settings import spectacular_settings


class Command(BaseCommand):
    help = "Export the AsyncAPI 3.0 spec to a YAML file."

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument(
            "--consumer",
            action="append",
            dest="consumers",
            metavar="DOTTED.PATH[:/ws/path/]",
            help=(
                "Dotted import path to an annotated consumer class, "
                "optionally followed by a colon and the WebSocket channel "
                "path (e.g. myapp.consumers.DispatchConsumer:/ws/dispatch/). "
                "Repeat for multiple consumers in one spec: "
                "--consumer A:/ws/a/ --consumer B:/ws/b/. "
                "When the channel path is omitted it falls back to "
                "CHANNELS_SPECTACULAR_SETTINGS['CHANNEL_PATH']."
            ),
        )
        source.add_argument(
            "--template",
            metavar="FILE",
            help=(
                "Path to a hand-written AsyncAPI YAML template.  "
                "{{ WS_HOST }} and {{ WS_PROTOCOL }} are resolved from "
                "settings (or --host / --protocol overrides).  "
                "Payload schemas without a title receive one derived from "
                "the message name so SDK generators produce readable types."
            ),
        )

        parser.add_argument(
            "--output",
            "-o",
            default="asyncapi.yaml",
            metavar="FILE",
            help="Destination file path (default: asyncapi.yaml).",
        )
        parser.add_argument(
            "--host",
            default=None,
            metavar="HOST",
            help=(
                "WebSocket host for the servers block "
                "(overrides CHANNELS_SPECTACULAR_SETTINGS['WS_HOST'])."
            ),
        )
        parser.add_argument(
            "--protocol",
            default=None,
            choices=["ws", "wss"],
            help=(
                "WebSocket protocol for the servers block "
                "(overrides CHANNELS_SPECTACULAR_SETTINGS['WS_PROTOCOL'])."
            ),
        )

    def handle(self, *args, **options):
        host = (
            options["host"]
            or spectacular_settings.WS_HOST
            or "localhost:8000"
        )
        protocol = (
            options["protocol"]
            or spectacular_settings.WS_PROTOCOL
            or "ws"
        )

        if options["template"]:
            yaml_text = self._render_template(
                options["template"], host, protocol
            )
        else:
            yaml_text = self._generate_from_consumers(
                options["consumers"],
                host=host,
                protocol=protocol,
            )

        output = pathlib.Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml_text)
        self.stdout.write(self.style.SUCCESS(f"Written {output}"))

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _render_template(
        self, template_path: str, host: str, protocol: str
    ) -> str:
        """
        Render a hand-written AsyncAPI YAML template.

        Resolves ``{{ WS_HOST }}`` / ``{{ WS_PROTOCOL }}`` placeholders,
        then injects a ``title`` into any payload schema that has a message
        ``name`` but no explicit title, so SDK generators produce readable
        TypeScript / Python type names instead of
        ``AnonymousSchema_N``.
        """
        src = pathlib.Path(template_path).read_text()
        src = (
            src
            .replace("{{ WS_HOST }}", host)
            .replace("{{ WS_PROTOCOL }}", protocol)
            .replace("{{ ws_host }}", host)
            .replace("{{ ws_protocol }}", protocol)
        )
        spec = yaml.safe_load(src)
        _inject_payload_titles(spec)
        return yaml.dump(spec, allow_unicode=True, sort_keys=False)

    def _generate_from_consumers(
        self,
        consumer_specs: list[str],
        *,
        host: str,
        protocol: str,
    ) -> str:
        """Generate the spec from one or more decorated consumer classes.

        Args:
            consumer_specs: List of strings in the form
                ``"dotted.path"`` or ``"dotted.path:/ws/channel/"``.
            host: WebSocket host for the servers block.
            protocol: WebSocket protocol (``"ws"`` or ``"wss"``).

        Returns:
            YAML string of the generated AsyncAPI spec.
        """
        pairs = [self._parse_consumer_spec(s) for s in consumer_specs]
        servers = {"default": {"host": host, "protocol": protocol}}

        if len(pairs) == 1:
            consumer_cls, channel_path = pairs[0]
            generator = AsyncAPIGenerator(
                consumer_cls,
                servers=servers,
                channel_path=channel_path,
            )
        else:
            generator = AsyncAPIGenerator(
                consumers=pairs,
                servers=servers,
            )
        return generator.get_yaml()

    def _parse_consumer_spec(
        self, spec: str
    ) -> tuple[type, str]:
        """Parse ``"dotted.path:/ws/channel/"`` into ``(class, path)``.

        The channel path part is optional; it falls back to
        ``CHANNELS_SPECTACULAR_SETTINGS['CHANNEL_PATH']``.

        Args:
            spec: A string like ``myapp.consumers.MyConsumer`` or
                ``myapp.consumers.MyConsumer:/ws/dispatch/``.

        Returns:
            A ``(consumer_class, channel_path)`` tuple.
        """
        if ":" in spec:
            dotted_path, channel_path = spec.split(":", 1)
        else:
            dotted_path = spec
            channel_path = spectacular_settings.CHANNEL_PATH

        try:
            consumer_cls = import_string(dotted_path)
        except ImportError as exc:
            raise CommandError(
                f"Could not import consumer {dotted_path!r}: {exc}"
            ) from exc

        return consumer_cls, channel_path


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _to_title_case(name: str) -> str:
    """Convert a dotted/snake_case identifier to TitleCase.

    Args:
        name: A string like ``ride.offer`` or ``request_ride``.

    Returns:
        TitleCase string, e.g. ``RideOffer`` or ``RequestRide``.
    """
    return "".join(word.capitalize() for word in re.split(r"[_.]", name))


def _inject_payload_titles(spec: dict) -> None:
    """Add a ``title`` to each message payload schema that lacks one.

    Modelina (used by ``@asyncapi/generator``) names a TypeScript
    interface after the schema's ``title``.  Hand-written specs often
    define payload schemas inline without a title, which causes modelina
    to fall back to ``AnonymousSchema_N``.  This function derives a title
    from the message's ``name`` field so every generated type has a
    meaningful name.

    Args:
        spec: Parsed AsyncAPI spec dict, mutated in-place.
    """
    messages = spec.get("components", {}).get("messages", {})
    for _key, msg in messages.items():
        if not isinstance(msg, dict):
            continue
        msg_name = msg.get("name", "")
        payload = msg.get("payload")
        if isinstance(payload, dict) and "title" not in payload and msg_name:
            payload["title"] = _to_title_case(msg_name)
