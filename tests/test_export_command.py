"""Tests for the ``export_asyncapi`` management command."""

from __future__ import annotations

import textwrap

import pytest
import yaml
from django.core.management import call_command
from django.core.management.base import CommandError

from channels_spectacular.management.commands.export_asyncapi import (
    _inject_payload_titles, _to_title_case)

SAMPLE = "tests.fixtures.sample_consumer.SampleConsumer"
NOTIF = "tests.fixtures.sample_consumer.NotificationConsumer"


def _run(*args, **kwargs):
    call_command("export_asyncapi", *args, **kwargs)


def _load(path):
    return yaml.safe_load(path.read_text())


# ---------------------------------------------------------------------------
# Generator mode
# ---------------------------------------------------------------------------

class TestGeneratorMode:
    def test_single_consumer_writes_valid_spec(self, tmp_path):
        out = tmp_path / "asyncapi.yaml"
        _run("--consumer", f"{SAMPLE}:/ws/sample/", "--output", str(out))

        assert out.exists()
        spec = _load(out)
        assert spec["asyncapi"] == "3.0.0"
        assert "request_ride" in spec["operations"]
        assert "/ws/sample/" in spec["channels"]

    def test_explicit_channel_path(self, tmp_path):
        out = tmp_path / "spec.yaml"
        _run("--consumer", f"{SAMPLE}:/ws/explicit/", "--output", str(out))

        spec = _load(out)
        assert "/ws/explicit/" in spec["channels"]

    def test_channel_path_falls_back_to_setting(self, tmp_path, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "CHANNEL_PATH": "/ws/fallback/",
        }
        out = tmp_path / "spec.yaml"
        # No ":/path/" suffix — should use CHANNEL_PATH.
        _run("--consumer", SAMPLE, "--output", str(out))

        spec = _load(out)
        assert "/ws/fallback/" in spec["channels"]

    def test_multiple_consumers_merged(self, tmp_path):
        out = tmp_path / "spec.yaml"
        _run(
            "--consumer", f"{SAMPLE}:/ws/sample/",
            "--consumer", f"{NOTIF}:/ws/notifications/",
            "--output", str(out),
        )

        spec = _load(out)
        assert "/ws/sample/" in spec["channels"]
        assert "/ws/notifications/" in spec["channels"]
        # Multi-consumer mode namespaces operation IDs by channel prefix.
        assert "sample_request_ride" in spec["operations"]
        assert "notifications_subscribe" in spec["operations"]

    def test_host_and_protocol_overrides(self, tmp_path):
        out = tmp_path / "spec.yaml"
        _run(
            "--consumer", f"{SAMPLE}:/ws/sample/",
            "--output", str(out),
            "--host", "api.example.com",
            "--protocol", "wss",
        )

        server = _load(out)["servers"]["default"]
        assert server["host"] == "api.example.com"
        assert server["protocol"] == "wss"

    def test_host_protocol_default_when_unset(self, tmp_path, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {}
        out = tmp_path / "spec.yaml"
        _run("--consumer", f"{SAMPLE}:/ws/sample/", "--output", str(out))

        server = _load(out)["servers"]["default"]
        assert server["host"] == "localhost:8000"
        assert server["protocol"] == "ws"

    def test_host_protocol_fall_back_to_settings(self, tmp_path, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "WS_HOST": "settings.example.com",
            "WS_PROTOCOL": "wss",
        }
        out = tmp_path / "spec.yaml"
        _run("--consumer", f"{SAMPLE}:/ws/sample/", "--output", str(out))

        server = _load(out)["servers"]["default"]
        assert server["host"] == "settings.example.com"
        assert server["protocol"] == "wss"

    def test_flag_overrides_settings(self, tmp_path, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "WS_HOST": "settings.example.com",
        }
        out = tmp_path / "spec.yaml"
        _run(
            "--consumer", f"{SAMPLE}:/ws/sample/",
            "--output", str(out),
            "--host", "flag.example.com",
        )

        assert _load(out)["servers"]["default"]["host"] == "flag.example.com"

    def test_creates_parent_directories(self, tmp_path):
        out = tmp_path / "nested" / "deeper" / "asyncapi.yaml"
        _run("--consumer", f"{SAMPLE}:/ws/sample/", "--output", str(out))

        assert out.exists()

    def test_invalid_consumer_raises_command_error(self, tmp_path):
        out = tmp_path / "spec.yaml"
        with pytest.raises(CommandError, match="Could not import consumer"):
            _run(
                "--consumer", "tests.fixtures.does_not.Exist",
                "--output", str(out),
            )

    def test_requires_a_source(self, tmp_path):
        # Neither --consumer nor --template — the mutually exclusive group
        # is required, so argparse errors out.
        with pytest.raises(CommandError):
            _run("--output", str(tmp_path / "spec.yaml"))


# ---------------------------------------------------------------------------
# Template mode
# ---------------------------------------------------------------------------

TEMPLATE = textwrap.dedent(
    """\
    asyncapi: 3.0.0
    info:
      title: Hand-written API
      version: 1.0.0
    servers:
      default:
        host: "{{ WS_HOST }}"
        protocol: "{{ WS_PROTOCOL }}"
    channels:
      /ws/x/:
        address: /ws/x/
    operations: {}
    components:
      messages:
        PingMessage:
          name: ping.event
          payload:
            type: object
            properties:
              foo:
                type: string
        TitledMessage:
          name: pong.event
          payload:
            title: AlreadyTitled
            type: object
            properties:
              bar:
                type: string
    """
)


class TestTemplateMode:
    def _write_template(self, tmp_path, body=TEMPLATE):
        tpl = tmp_path / "template.yaml"
        tpl.write_text(body)
        return tpl

    def test_substitutes_host_and_protocol(self, tmp_path):
        tpl = self._write_template(tmp_path)
        out = tmp_path / "spec.yaml"
        _run(
            "--template", str(tpl),
            "--output", str(out),
            "--host", "tmpl.example.com",
            "--protocol", "wss",
        )

        server = _load(out)["servers"]["default"]
        assert server["host"] == "tmpl.example.com"
        assert server["protocol"] == "wss"

    def test_substitutes_lowercase_placeholders(self, tmp_path):
        body = TEMPLATE.replace("{{ WS_HOST }}", "{{ ws_host }}").replace(
            "{{ WS_PROTOCOL }}", "{{ ws_protocol }}"
        )
        tpl = self._write_template(tmp_path, body)
        out = tmp_path / "spec.yaml"
        _run(
            "--template", str(tpl),
            "--output", str(out),
            "--host", "lower.example.com",
            "--protocol", "ws",
        )

        assert _load(out)["servers"]["default"]["host"] == "lower.example.com"

    def test_injects_title_from_message_name(self, tmp_path):
        tpl = self._write_template(tmp_path)
        out = tmp_path / "spec.yaml"
        _run("--template", str(tpl), "--output", str(out))

        messages = _load(out)["components"]["messages"]
        # "ping.event" -> "PingEvent"
        assert messages["PingMessage"]["payload"]["title"] == "PingEvent"

    def test_does_not_overwrite_existing_title(self, tmp_path):
        tpl = self._write_template(tmp_path)
        out = tmp_path / "spec.yaml"
        _run("--template", str(tpl), "--output", str(out))

        messages = _load(out)["components"]["messages"]
        assert messages["TitledMessage"]["payload"]["title"] == "AlreadyTitled"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("ride.offer", "RideOffer"),
            ("request_ride", "RequestRide"),
            ("message.new", "MessageNew"),
            ("single", "Single"),
        ],
    )
    def test_to_title_case(self, name, expected):
        assert _to_title_case(name) == expected

    def test_inject_payload_titles_skips_missing_name(self):
        spec = {
            "components": {
                "messages": {
                    "NoName": {"payload": {"type": "object"}},
                }
            }
        }
        _inject_payload_titles(spec)
        payload = spec["components"]["messages"]["NoName"]["payload"]
        assert "title" not in payload

    def test_inject_payload_titles_handles_no_messages(self):
        spec = {"components": {}}
        _inject_payload_titles(spec)  # must not raise
        assert spec == {"components": {}}

    def test_inject_payload_titles_skips_non_dict_message(self):
        # A malformed message entry that isn't a dict must be skipped.
        spec = {"components": {"messages": {"Weird": "not-a-dict"}}}
        _inject_payload_titles(spec)  # must not raise
        assert spec["components"]["messages"]["Weird"] == "not-a-dict"
