"""Tests for AsyncAPISpecView and AsyncAPIDocView."""

from __future__ import annotations

import pytest
import yaml
from django.test import Client, RequestFactory
from django.urls import reverse

from channels_spectacular.views import AsyncAPIDocView, AsyncAPISpecView
from tests.fixtures.sample_consumer import NotificationConsumer, SampleConsumer


# ---------------------------------------------------------------------------
# AsyncAPISpecView
# ---------------------------------------------------------------------------
class TestAsyncAPISpecView:
    @pytest.fixture
    def client(self):
        return Client()

    def test_returns_200(self, client):
        resp = client.get(reverse("asyncapi-spec"))
        assert resp.status_code == 200

    def test_content_type_is_yaml(self, client):
        resp = client.get(reverse("asyncapi-spec"))
        assert "yaml" in resp["Content-Type"]

    def test_response_body_is_valid_yaml(self, client):
        resp = client.get(reverse("asyncapi-spec"))
        parsed = yaml.safe_load(resp.content)
        assert "asyncapi" in parsed

    def test_spec_contains_operations(self, client):
        resp = client.get(reverse("asyncapi-spec"))
        parsed = yaml.safe_load(resp.content)
        assert "operations" in parsed
        assert "request_ride" in parsed["operations"]

    def test_channel_path_from_view(self, client):
        resp = client.get(reverse("asyncapi-spec"))
        parsed = yaml.safe_load(resp.content)
        assert "/ws/sample/" in parsed["channels"]

    def test_servers_built_from_request(self, client):
        resp = client.get(reverse("asyncapi-spec"))
        parsed = yaml.safe_load(resp.content)
        assert "servers" in parsed
        server = list(parsed["servers"].values())[0]
        assert "host" in server
        assert server["protocol"] in ("ws", "wss")

    def test_ws_host_from_settings(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "WS_HOST": "myapi.example.com",
            "WS_PROTOCOL": "wss",
        }
        resp = client.get(reverse("asyncapi-spec"))
        parsed = yaml.safe_load(resp.content)
        server = list(parsed["servers"].values())[0]
        assert server["host"] == "myapi.example.com"
        assert server["protocol"] == "wss"

    def test_static_servers_from_settings(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "SERVERS": {
                "prod": {"host": "prod.example.com", "protocol": "wss"},
                "dev": {"host": "localhost:8000", "protocol": "ws"},
            }
        }
        resp = client.get(reverse("asyncapi-spec"))
        parsed = yaml.safe_load(resp.content)
        assert "prod" in parsed["servers"]
        assert "dev" in parsed["servers"]

    def test_missing_consumer_raises(self):
        factory = RequestFactory()
        request = factory.get("/")
        view = AsyncAPISpecView.as_view()
        with pytest.raises(ValueError, match="consumer"):
            view(request)

    def test_view_level_servers_override_settings(self, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "WS_HOST": "settings.example.com",
        }
        factory = RequestFactory()
        request = factory.get("/")
        view = AsyncAPISpecView.as_view(
            consumer=SampleConsumer,
            servers={
                "custom": {"host": "custom.example.com", "protocol": "ws"}
            },
            channel_path="/ws/",
        )
        resp = view(request)
        parsed = yaml.safe_load(resp.content)
        assert "custom" in parsed["servers"]
        assert parsed["servers"]["custom"]["host"] == "custom.example.com"


# ---------------------------------------------------------------------------
# AsyncAPISpecView — multi-consumer
# ---------------------------------------------------------------------------

class TestMultiConsumerSpecView:
    @pytest.fixture
    def client(self):
        return Client()

    def test_returns_200(self, client):
        resp = client.get(reverse("asyncapi-spec-multi"))
        assert resp.status_code == 200

    def test_content_type_is_yaml(self, client):
        resp = client.get(reverse("asyncapi-spec-multi"))
        assert "yaml" in resp["Content-Type"]

    def test_both_channels_in_spec(self, client):
        resp = client.get(reverse("asyncapi-spec-multi"))
        parsed = yaml.safe_load(resp.content)
        assert "/ws/sample/" in parsed["channels"]
        assert "/ws/notifications/" in parsed["channels"]

    def test_prefixed_operations(self, client):
        resp = client.get(reverse("asyncapi-spec-multi"))
        parsed = yaml.safe_load(resp.content)
        ops = parsed["operations"]
        assert "sample_request_ride" in ops
        assert "notifications_subscribe" in ops

    def test_consumers_kwarg_via_as_view(self):
        factory = RequestFactory()
        request = factory.get("/")
        view = AsyncAPISpecView.as_view(
            consumers=[
                (SampleConsumer, "/ws/rides/"),
                (NotificationConsumer, "/ws/notify/"),
            ],
        )
        resp = view(request)
        parsed = yaml.safe_load(resp.content)
        assert "/ws/rides/" in parsed["channels"]
        assert "/ws/notify/" in parsed["channels"]

    def test_missing_both_consumer_and_consumers_raises(self):
        factory = RequestFactory()
        request = factory.get("/")
        view = AsyncAPISpecView.as_view()
        with pytest.raises(ValueError, match="consumer"):
            view(request)


# ---------------------------------------------------------------------------
# AsyncAPIDocView
# ---------------------------------------------------------------------------

class TestAsyncAPIDocView:
    @pytest.fixture
    def client(self):
        return Client()

    def test_returns_200(self, client):
        resp = client.get(reverse("asyncapi-doc"))
        assert resp.status_code == 200

    def test_content_type_is_html(self, client):
        resp = client.get(reverse("asyncapi-doc"))
        assert "text/html" in resp["Content-Type"]

    def test_spec_url_auto_derived(self, client):
        resp = client.get("/ws-docs/")
        assert b"asyncapi.yaml" in resp.content

    def test_explicit_spec_url(self):
        factory = RequestFactory()
        request = factory.get("/docs/")
        view = AsyncAPIDocView.as_view(spec_url="/api/my-spec.yaml")
        resp = view(request)
        resp.render()  # TemplateResponse is lazy; force render before .content
        assert b"/api/my-spec.yaml" in resp.content

    def test_try_it_out_hidden_by_default(self, client):
        # CSS always contains the selector; check for the HTML element instead.
        resp = client.get(reverse("asyncapi-doc"))
        assert b'id="try-it-out"' not in resp.content

    def test_try_it_out_shown_when_enabled(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "TRY_IT_OUT_ENABLED": True,
        }
        resp = client.get(reverse("asyncapi-doc"))
        assert b'id="try-it-out"' in resp.content

    def test_title_in_page(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {"TITLE": "My Dispatch API"}
        resp = client.get(reverse("asyncapi-doc"))
        assert b"My Dispatch API" in resp.content

    def test_inline_code_override_shipped(self, client):
        # AsyncAPI's default theme renders inline `code` as plain bold text
        # with a literal backtick glyph (code:before { content: "`" }). The
        # viewer ships a CSS override that restores a monospace chip and
        # clears those glyphs — guard it so a template edit can't drop it.
        resp = client.get(reverse("asyncapi-doc"))
        assert b".aui-root .prose :not(pre) > code" in resp.content
        assert b'content: "" !important' in resp.content

    def test_specs_renders_switcher_dropdown(self):
        factory = RequestFactory()
        request = factory.get("/ws-docs/")
        view = AsyncAPIDocView.as_view(
            specs=[
                ("Rides /ws/rides/", "/api/v1/ws-docs/rides/asyncapi.yaml"),
                (
                    "Notifications /ws/notifications/",
                    "/api/v1/ws-docs/notif/asyncapi.yaml",
                ),
            ]
        )
        resp = view(request)
        resp.render()
        assert b'id="consumer-select"' in resp.content
        assert b"Rides /ws/rides/" in resp.content
        assert b"Notifications /ws/notifications/" in resp.content
        assert b"/api/v1/ws-docs/rides/asyncapi.yaml" in resp.content
        assert b"/api/v1/ws-docs/notif/asyncapi.yaml" in resp.content

    def test_specs_initial_spec_url_is_first_entry(self):
        factory = RequestFactory()
        request = factory.get("/ws-docs/")
        view = AsyncAPIDocView.as_view(
            specs=[
                ("Rides /ws/rides/", "/api/v1/ws-docs/rides/asyncapi.yaml"),
                (
                    "Notifications /ws/notifications/",
                    "/api/v1/ws-docs/notif/asyncapi.yaml",
                ),
            ]
        )
        resp = view(request)
        resp.render()
        # The first spec URL is used for the initial
        # AsyncApiStandalone.render call.
        assert b"rides/asyncapi.yaml" in resp.content

    def test_no_switcher_when_single_consumer(self, client):
        resp = client.get(reverse("asyncapi-doc"))
        assert b'id="consumer-select"' not in resp.content


# ---------------------------------------------------------------------------
# Auth context — AsyncAPIDocView
# ---------------------------------------------------------------------------

class TestAuthContext:
    @pytest.fixture
    def client(self):
        return Client()

    def test_default_jwt_cookie_name_in_page(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {"TRY_IT_OUT_ENABLED": True}
        resp = client.get(reverse("asyncapi-doc"))
        # Default JWT cookie name must appear in the cookie name input value.
        assert b"access_token" in resp.content

    def test_session_cookie_name_in_page(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {"TRY_IT_OUT_ENABLED": True}
        resp = client.get(reverse("asyncapi-doc"))
        # Django's SESSION_COOKIE_NAME ("sessionid") must appear in the auth
        # description so users know which cookie is forwarded automatically.
        assert b"sessionid" in resp.content

    def test_panel_starts_collapsed_by_default(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {"TRY_IT_OUT_ENABLED": True}
        resp = client.get(reverse("asyncapi-doc"))
        # Panel must not carry class="open" unless TRY_IT_OUT_EXPANDED is True.
        assert b'class="open"' not in resp.content

    def test_custom_auth_cookie_name(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "AUTH_COOKIE_NAME": "my_session",
            "TRY_IT_OUT_ENABLED": True,
        }
        resp = client.get(reverse("asyncapi-doc"))
        assert b"my_session" in resp.content

    def test_security_schemes_in_spec(self, client, settings):
        settings.CHANNELS_SPECTACULAR_SETTINGS = {
            "AUTH_QUERY_PARAM": "token",
            "AUTH_COOKIE_NAME": "access_token",
        }
        resp = client.get(reverse("asyncapi-spec"))
        import yaml as _yaml
        parsed = _yaml.safe_load(resp.content)
        schemes = parsed["components"]["securitySchemes"]
        assert "queryToken" in schemes
        assert "cookieJWT" in schemes
