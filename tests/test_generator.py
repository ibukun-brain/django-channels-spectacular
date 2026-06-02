"""Tests for AsyncAPIGenerator spec assembly."""

from __future__ import annotations

import pytest
import yaml

from channels_spectacular.decorators import (ASYNCAPI_ACTION_ATTR,
                                             ASYNCAPI_EVENT_ATTR,
                                             document_action, document_event)
from channels_spectacular.generator import (AsyncAPIGenerator, _channel_prefix,
                                            _collect_annotated,
                                            _inject_discriminator, _to_camel)
from tests.fixtures.sample_consumer import NotificationConsumer, SampleConsumer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class TestToCamel:
    @pytest.mark.parametrize("inp,expected", [
        ("request_ride", "RequestRide"),
        ("ride.offer", "RideOffer"),
        ("ride-cancelled", "RideCancelled"),
        ("ping", "Ping"),
        ("accept_delivery_offer", "AcceptDeliveryOffer"),
    ])
    def test_conversion(self, inp, expected):
        assert _to_camel(inp) == expected


class TestInjectDiscriminator:
    def test_adds_field_to_existing_schema(self):
        schema = {
            "type": "object",
            "properties": {"fare": {"type": "string"}},
        }
        result = _inject_discriminator(schema, "action", "request_ride")
        assert result["properties"]["action"] == {
            "type": "string",
            "const": "request_ride",
        }
        assert "fare" in result["properties"]

    def test_discriminator_is_first_property(self):
        schema = {"type": "object", "properties": {"b": {}, "a": {}}}
        result = _inject_discriminator(schema, "action", "ping")
        keys = list(result["properties"].keys())
        assert keys[0] == "action"

    def test_empty_schema_becomes_object(self):
        result = _inject_discriminator({}, "type", "ride.offer")
        assert result["type"] == "object"
        assert result["properties"]["type"]["const"] == "ride.offer"

    def test_does_not_mutate_input(self):
        schema = {"type": "object", "properties": {"x": {}}}
        original_keys = list(schema["properties"].keys())
        _inject_discriminator(schema, "action", "test")
        assert list(schema["properties"].keys()) == original_keys


# ---------------------------------------------------------------------------
# _collect_annotated
# ---------------------------------------------------------------------------

class TestCollectAnnotated:
    def test_collects_actions_in_definition_order(self):
        metas = _collect_annotated(SampleConsumer, ASYNCAPI_ACTION_ATTR)
        actions = [m["action"] for m in metas]
        assert "request_ride" in actions
        assert "accept_offer" in actions
        assert "ping" in actions

    def test_collects_events(self):
        metas = _collect_annotated(SampleConsumer, ASYNCAPI_EVENT_ATTR)
        event_types = [m["event_type"] for m in metas]
        assert "ride.offer" in event_types
        assert "ride.accepted" in event_types

    def test_no_duplicates(self):
        metas = _collect_annotated(SampleConsumer, ASYNCAPI_ACTION_ATTR)
        actions = [m["action"] for m in metas]
        assert len(actions) == len(set(actions))

    def test_subclass_overrides_parent(self):
        class Parent:
            @document_action(summary="Original")
            async def handle_ping(self, content):
                pass

        class Child(Parent):
            @document_action(summary="Override")
            async def handle_ping(self, content):
                pass

        metas = _collect_annotated(Child, ASYNCAPI_ACTION_ATTR)
        assert len([m for m in metas if m["action"] == "ping"]) == 1
        # Child definition wins
        ping_meta = next(m for m in metas if m["action"] == "ping")
        assert ping_meta["summary"] == "Override"

    def test_inherited_actions_included(self):
        class Base:
            @document_action(summary="Base action")
            async def handle_base_action(self, content):
                pass

        class Child(Base):
            @document_action(summary="Child action")
            async def handle_child_action(self, content):
                pass

        metas = _collect_annotated(Child, ASYNCAPI_ACTION_ATTR)
        actions = [m["action"] for m in metas]
        assert "base_action" in actions
        assert "child_action" in actions


# ---------------------------------------------------------------------------
# AsyncAPIGenerator.get_spec()
# ---------------------------------------------------------------------------

class TestGetSpec:
    @pytest.fixture
    def generator(self):
        return AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "Test API", "version": "0.1.0"},
            servers={"default": {"host": "localhost", "protocol": "ws"}},
            channel_path="/ws/test/",
        )

    @pytest.fixture
    def spec(self, generator):
        return generator.get_spec()

    def test_asyncapi_version_present(self, spec):
        assert spec["asyncapi"] == "3.0.0"

    def test_info_present(self, spec):
        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "0.1.0"

    def test_servers_present(self, spec):
        assert "default" in spec["servers"]

    def test_channel_address(self, spec):
        assert "/ws/test/" in spec["channels"]
        assert spec["channels"]["/ws/test/"]["address"] == "/ws/test/"

    def test_send_operations_present(self, spec):
        ops = spec["operations"]
        assert "request_ride" in ops
        assert ops["request_ride"]["action"] == "send"

    def test_receive_operations_present(self, spec):
        ops = spec["operations"]
        assert "ride_offer" in ops
        assert ops["ride_offer"]["action"] == "receive"

    def test_operation_has_channel_ref(self, spec):
        op = spec["operations"]["request_ride"]
        assert "$ref" in op["channel"]
        ref = op["channel"]["$ref"]
        assert "/ws/test/" in ref or "~1ws~1test~1" in ref

    def test_operation_has_message_ref(self, spec):
        op = spec["operations"]["request_ride"]
        assert len(op["messages"]) == 1
        assert "$ref" in op["messages"][0]

    def test_component_messages_present(self, spec):
        assert "components" in spec
        assert "RequestRide" in spec["components"]["messages"]
        assert "RideOffer" in spec["components"]["messages"]

    def test_action_discriminator_injected(self, spec):
        msg = spec["components"]["messages"]["RequestRide"]
        props = msg["payload"]["properties"]
        assert props["action"]["const"] == "request_ride"

    def test_event_discriminator_injected(self, spec):
        msg = spec["components"]["messages"]["RideOffer"]
        props = msg["payload"]["properties"]
        assert props["type"]["const"] == "ride.offer"

    def test_summary_included(self, spec):
        msg = spec["components"]["messages"]["RequestRide"]
        assert msg["summary"] == "Request a ride"

    def test_deprecated_flag_propagated(self, spec):
        msg = spec["components"]["messages"]["CancelRide"]
        assert msg.get("deprecated") is True

    def test_tags_included(self, spec):
        msg = spec["components"]["messages"]["RequestRide"]
        assert {"name": "rides"} in msg["tags"]

    def test_channel_messages_are_refs(self, spec):
        ch_msgs = spec["channels"]["/ws/test/"]["messages"]
        for name, val in ch_msgs.items():
            assert val == {"$ref": f"#/components/messages/{name}"}

    def test_no_servers_key_when_empty(self):
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={},
            channel_path="/",
        )
        spec = gen.get_spec()
        assert "servers" not in spec

    def test_description_not_included_when_blank(self):
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            channel_path="/",
        )
        spec = gen.get_spec()
        assert "description" not in spec["info"]


# ---------------------------------------------------------------------------
# AsyncAPIGenerator.get_yaml()
# ---------------------------------------------------------------------------

class TestGetYaml:
    def test_returns_valid_yaml(self):
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            channel_path="/ws/",
        )
        yaml_str = gen.get_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["asyncapi"] == "3.0.0"

    def test_content_type_hint(self):
        gen = AsyncAPIGenerator(SampleConsumer, channel_path="/ws/")
        yaml_str = gen.get_yaml()
        assert "asyncapi:" in yaml_str
        assert "operations:" in yaml_str


# ---------------------------------------------------------------------------
# Settings-driven defaults
# ---------------------------------------------------------------------------

class TestSettingsDefaults:
    def test_channel_path_from_settings(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "CHANNEL_PATH": "/ws/from-settings/",
        }
        gen = AsyncAPIGenerator(SampleConsumer)
        assert gen.channel_path == "/ws/from-settings/"

    def test_info_from_settings(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "TITLE": "Settings Title",
            "VERSION": "9.9.9",
            "DESCRIPTION": "From settings",
        }
        gen = AsyncAPIGenerator(SampleConsumer)
        assert gen.info["title"] == "Settings Title"
        assert gen.info["version"] == "9.9.9"
        assert gen.info["description"] == "From settings"

    def test_description_omitted_when_blank(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "TITLE": "T",
            "VERSION": "0",
            "DESCRIPTION": "",
        }
        gen = AsyncAPIGenerator(SampleConsumer)
        assert "description" not in gen.info

    def test_servers_from_settings(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "SERVERS": {"prod": {"host": "api.x.com", "protocol": "wss"}},
        }
        gen = AsyncAPIGenerator(SampleConsumer)
        assert gen.servers == {
            "prod": {"host": "api.x.com", "protocol": "wss"}
        }

    def test_explicit_args_override_settings(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "CHANNEL_PATH": "/ws/settings/",
            "TITLE": "Settings Title",
        }
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "Explicit", "version": "1"},
            channel_path="/ws/explicit/",
        )
        assert gen.channel_path == "/ws/explicit/"
        assert gen.info["title"] == "Explicit"


# ---------------------------------------------------------------------------
# _channel_prefix
# ---------------------------------------------------------------------------

class TestChannelPrefix:
    @pytest.mark.parametrize("path,expected", [
        ("/ws/rides/", "Rides"),
        ("/ws/notifications/", "Notifications"),
        ("/ws/v1/chat/", "Chat"),
        ("/ws/", "Ws"),
        ("/", "Root"),
        ("/ws/ride_dispatch/", "RideDispatch"),
    ])
    def test_prefix_from_path(self, path, expected):
        assert _channel_prefix(path) == expected


# ---------------------------------------------------------------------------
# Multi-consumer spec
# ---------------------------------------------------------------------------

class TestMultiConsumerSpec:
    @pytest.fixture
    def spec(self):
        gen = AsyncAPIGenerator(
            consumers=[
                (SampleConsumer, "/ws/sample/"),
                (NotificationConsumer, "/ws/notifications/"),
            ],
            info={"title": "Multi API", "version": "0.1.0"},
            servers={"default": {"host": "localhost", "protocol": "ws"}},
        )
        return gen.get_spec()

    def test_both_channels_present(self, spec):
        assert "/ws/sample/" in spec["channels"]
        assert "/ws/notifications/" in spec["channels"]

    def test_channel_addresses(self, spec):
        assert spec["channels"]["/ws/sample/"]["address"] == "/ws/sample/"
        assert (
            spec["channels"]["/ws/notifications/"]["address"]
            == "/ws/notifications/"
        )

    def test_messages_prefixed_by_channel(self, spec):
        msgs = spec["components"]["messages"]
        # SampleConsumer messages prefixed with "Sample"
        assert "SampleRequestRide" in msgs
        assert "SampleRideOffer" in msgs
        # NotificationConsumer messages prefixed with "Notifications"
        assert "NotificationsSubscribe" in msgs
        assert "NotificationsNotificationNew" in msgs

    def test_operations_prefixed_by_channel(self, spec):
        ops = spec["operations"]
        assert "sample_request_ride" in ops
        assert "notifications_subscribe" in ops
        assert "notifications_notification_new" in ops

    def test_operations_reference_correct_channel(self, spec):
        op = spec["operations"]["sample_request_ride"]
        assert "~1ws~1sample~1" in op["channel"]["$ref"]

        op = spec["operations"]["notifications_subscribe"]
        assert "~1ws~1notifications~1" in op["channel"]["$ref"]

    def test_channel_messages_are_refs_to_components(self, spec):
        ch_msgs = spec["channels"]["/ws/notifications/"]["messages"]
        for name, val in ch_msgs.items():
            assert val == {"$ref": f"#/components/messages/{name}"}

    def test_no_cross_consumer_name_collisions(self, spec):
        ops = spec["operations"]
        msgs = spec["components"]["messages"]
        assert len(ops) == len(set(ops))
        assert len(msgs) == len(set(msgs))

    def test_no_consumer_kwarg_raises(self):
        with pytest.raises(ValueError, match="consumer"):
            AsyncAPIGenerator()

    def test_single_consumer_mode_unchanged(self):
        """Single-consumer output matches pre-multi-consumer behaviour."""
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={},
            channel_path="/ws/test/",
        )
        spec = gen.get_spec()
        # No prefix on names in single-consumer mode
        assert "RequestRide" in spec["components"]["messages"]
        assert "request_ride" in spec["operations"]
        assert "SampleRequestRide" not in spec["components"]["messages"]


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

class TestExamples:
    """Examples appear verbatim in the message entry under 'examples'."""

    def _gen(self):
        return AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={},
            channel_path="/ws/sample/",
        )

    def test_action_examples_in_spec(self):
        spec = self._gen().get_spec()
        msg = spec["components"]["messages"]["RequestRide"]
        assert "examples" in msg
        assert len(msg["examples"]) == 2
        assert msg["examples"][0]["name"] == "Cash payment"
        assert msg["examples"][1]["name"] == "Card payment"

    def test_action_example_payload_values(self):
        spec = self._gen().get_spec()
        ex = spec["components"]["messages"]["RequestRide"]["examples"][0]
        assert ex["payload"]["action"] == "request_ride"
        assert ex["payload"]["fare"] == "1500.00"

    def test_event_examples_in_spec(self):
        spec = self._gen().get_spec()
        msg = spec["components"]["messages"]["RideOffer"]
        assert "examples" in msg
        assert len(msg["examples"]) == 1
        assert msg["examples"][0]["name"] == "Standard offer"

    def test_event_example_payload_values(self):
        spec = self._gen().get_spec()
        ex = spec["components"]["messages"]["RideOffer"]["examples"][0]
        assert ex["payload"]["type"] == "ride.offer"
        assert "ride_id" in ex["payload"]

    def test_no_examples_key_when_empty(self):
        """Messages without examples must not emit an 'examples' key."""
        spec = self._gen().get_spec()
        # AcceptOffer has no examples= on its decorator
        msg = spec["components"]["messages"]["AcceptOffer"]
        assert "examples" not in msg

    def test_examples_roundtrip_yaml(self):
        """Examples survive YAML serialisation and deserialisation."""
        import yaml as _yaml
        raw = self._gen().get_yaml()
        spec = _yaml.safe_load(raw)
        msg = spec["components"]["messages"]["RequestRide"]
        assert msg["examples"][0]["name"] == "Cash payment"

    def test_inline_examples_on_action(self):
        """Examples passed inline to document_action appear in the spec."""
        examples = [{"name": "X", "payload": {"action": "go", "v": 1}}]

        class QuickConsumer:
            @document_action(summary="Go", examples=examples)
            async def handle_go(self, content):
                pass

        gen = AsyncAPIGenerator(
            QuickConsumer,
            info={"title": "T", "version": "0"},
            servers={},
            channel_path="/ws/q/",
        )
        msg = gen.get_spec()["components"]["messages"]["Go"]
        assert msg["examples"] == examples

    def test_inline_examples_on_event(self):
        """Examples passed inline to document_event appear in the spec."""
        examples = [{"name": "Y", "payload": {"type": "x.y", "v": 2}}]

        class QuickConsumer:
            @document_event("x.y", summary="XY", examples=examples)
            async def x_y(self, event):
                pass

        gen = AsyncAPIGenerator(
            QuickConsumer,
            info={"title": "T", "version": "0"},
            servers={},
            channel_path="/ws/q/",
        )
        msg = gen.get_spec()["components"]["messages"]["XY"]
        assert msg["examples"] == examples


# ---------------------------------------------------------------------------
# Security schemes
# ---------------------------------------------------------------------------

class TestSecuritySchemes:
    def test_no_schemes_by_default(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {}
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={"default": {"host": "localhost", "protocol": "ws"}},
            channel_path="/ws/",
        )
        spec = gen.get_spec()
        components = spec.get("components", {})
        assert "securitySchemes" not in components

    def test_query_param_scheme(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "AUTH_QUERY_PARAM": "token",
        }
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={"default": {"host": "localhost", "protocol": "ws"}},
            channel_path="/ws/",
        )
        spec = gen.get_spec()
        scheme = spec["components"]["securitySchemes"]["queryToken"]
        assert scheme["type"] == "httpApiKey"
        assert scheme["in"] == "query"
        assert scheme["name"] == "token"

    def test_cookie_scheme(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "AUTH_COOKIE_NAME": "access_token",
        }
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={"default": {"host": "localhost", "protocol": "ws"}},
            channel_path="/ws/",
        )
        spec = gen.get_spec()
        scheme = spec["components"]["securitySchemes"]["cookieJWT"]
        assert scheme["type"] == "httpApiKey"
        assert scheme["in"] == "cookie"
        assert scheme["name"] == "access_token"

    def test_both_schemes(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "AUTH_QUERY_PARAM": "token",
            "AUTH_COOKIE_NAME": "access_token",
        }
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={"default": {"host": "localhost", "protocol": "ws"}},
            channel_path="/ws/",
        )
        spec = gen.get_spec()
        schemes = spec["components"]["securitySchemes"]
        assert "queryToken" in schemes
        assert "cookieJWT" in schemes

    def test_security_not_attached_to_servers(self, settings):
        # AsyncAPI 3.0 server.security takes full scheme objects, not the
        # 2.x {name: []} shorthand, and the viewer's validator rejects it.
        # Schemes are declared under components only — never on the server.
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "AUTH_QUERY_PARAM": "token",
        }
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={"default": {"host": "localhost", "protocol": "ws"}},
            channel_path="/ws/",
        )
        spec = gen.get_spec()
        assert "security" not in spec["servers"]["default"]
        assert "queryToken" in spec["components"]["securitySchemes"]

    def test_no_security_on_servers_when_no_schemes(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {}
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={"default": {"host": "localhost", "protocol": "ws"}},
            channel_path="/ws/",
        )
        spec = gen.get_spec()
        assert "security" not in spec["servers"]["default"]

    def test_messages_and_schemes_coexist_in_components(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "AUTH_QUERY_PARAM": "token",
        }
        gen = AsyncAPIGenerator(
            SampleConsumer,
            info={"title": "T", "version": "0"},
            servers={},
            channel_path="/ws/",
        )
        spec = gen.get_spec()
        assert "messages" in spec["components"]
        assert "securitySchemes" in spec["components"]
