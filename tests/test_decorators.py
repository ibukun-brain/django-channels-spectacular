"""Tests for @document_action and @document_event decorators."""

from channels_spectacular.decorators import (ASYNCAPI_ACTION_ATTR,
                                             ASYNCAPI_EVENT_ATTR,
                                             document_action, document_event)


class TestDocumentAction:
    def test_metadata_stored_on_function(self):
        @document_action(summary="Test action")
        async def handle_do_thing(self, content):
            pass

        meta = getattr(handle_do_thing, ASYNCAPI_ACTION_ATTR)
        assert meta is not None

    def test_action_inferred_from_handle_prefix(self):
        @document_action()
        async def handle_request_ride(self, content):
            pass

        meta = getattr(handle_request_ride, ASYNCAPI_ACTION_ATTR)
        assert meta["action"] == "request_ride"

    def test_action_inferred_without_handle_prefix(self):
        @document_action()
        async def do_something(self, content):
            pass

        meta = getattr(do_something, ASYNCAPI_ACTION_ATTR)
        assert meta["action"] == "do_something"

    def test_explicit_action_overrides_inference(self):
        @document_action(action="my_action")
        async def any_method_name(self, content):
            pass

        meta = getattr(any_method_name, ASYNCAPI_ACTION_ATTR)
        assert meta["action"] == "my_action"

    def test_default_values(self):
        @document_action()
        async def handle_ping(self, content):
            pass

        meta = getattr(handle_ping, ASYNCAPI_ACTION_ATTR)
        assert meta["summary"] == ""
        assert meta["description"] == ""
        assert meta["payload"] is None
        assert meta["responses"] == {}
        assert meta["examples"] == []
        assert meta["deprecated"] is False
        assert meta["tags"] == []

    def test_all_fields_stored(self):
        payload = {"type": "object"}
        examples = [{"name": "Ex", "payload": {"action": "test"}}]

        @document_action(
            action="test",
            summary="A summary",
            description="A description",
            payload=payload,
            responses={"event.done": {}},
            examples=examples,
            deprecated=True,
            tags=["foo", "bar"],
        )
        async def handle_test(self, content):
            pass

        meta = getattr(handle_test, ASYNCAPI_ACTION_ATTR)
        assert meta["summary"] == "A summary"
        assert meta["description"] == "A description"
        assert meta["payload"] is payload
        assert meta["responses"] == {"event.done": {}}
        assert meta["examples"] == examples
        assert meta["deprecated"] is True
        assert meta["tags"] == ["foo", "bar"]

    def test_examples_stored_on_action(self):
        examples = [
            {"name": "A", "payload": {"action": "go", "x": 1}},
            {"name": "B", "payload": {"action": "go", "x": 2}},
        ]

        @document_action(examples=examples)
        async def handle_go(self, content):
            pass

        meta = getattr(handle_go, ASYNCAPI_ACTION_ATTR)
        assert meta["examples"] == examples

    def test_none_examples_defaults_to_empty_list(self):
        @document_action(examples=None)
        async def handle_go(self, content):
            pass

        meta = getattr(handle_go, ASYNCAPI_ACTION_ATTR)
        assert meta["examples"] == []

    def test_decorator_returns_original_function(self):
        @document_action()
        async def handle_test(self, content):
            pass

        assert callable(handle_test)
        assert handle_test.__name__ == "handle_test"

    def test_no_handle_prefix_strips_nothing(self):
        """A method named exactly 'handle_' keeps the empty trailing name."""
        @document_action()
        async def handle_(self, content):
            pass

        meta = getattr(handle_, ASYNCAPI_ACTION_ATTR)
        # strips "handle_" leaving ""
        assert meta["action"] == ""


class TestDocumentEvent:
    def test_metadata_stored_on_function(self):
        @document_event("ride.offer")
        async def ride_offer(self, event):
            pass

        meta = getattr(ride_offer, ASYNCAPI_EVENT_ATTR)
        assert meta is not None

    def test_event_type_stored(self):
        @document_event("ride.offer")
        async def ride_offer(self, event):
            pass

        meta = getattr(ride_offer, ASYNCAPI_EVENT_ATTR)
        assert meta["event_type"] == "ride.offer"

    def test_default_values(self):
        @document_event("some.event")
        async def handler(self, event):
            pass

        meta = getattr(handler, ASYNCAPI_EVENT_ATTR)
        assert meta["summary"] == ""
        assert meta["description"] == ""
        assert meta["payload"] is None
        assert meta["examples"] == []
        assert meta["deprecated"] is False
        assert meta["tags"] == []

    def test_all_fields_stored(self):
        payload = {"type": "object"}
        examples = [{"name": "Ex", "payload": {"type": "ride.offer"}}]

        @document_event(
            "ride.offer",
            summary="Offer sent",
            description="Long desc",
            payload=payload,
            examples=examples,
            deprecated=True,
            tags=["rides"],
        )
        async def ride_offer(self, event):
            pass

        meta = getattr(ride_offer, ASYNCAPI_EVENT_ATTR)
        assert meta["summary"] == "Offer sent"
        assert meta["description"] == "Long desc"
        assert meta["payload"] is payload
        assert meta["examples"] == examples
        assert meta["deprecated"] is True
        assert meta["tags"] == ["rides"]

    def test_examples_stored_on_event(self):
        examples = [
            {
                "name": "Standard offer",
                "payload": {"type": "ride.offer", "ride_id": "abc"},
            }
        ]

        @document_event("ride.offer", examples=examples)
        async def ride_offer(self, event):
            pass

        meta = getattr(ride_offer, ASYNCAPI_EVENT_ATTR)
        assert meta["examples"] == examples

    def test_none_examples_defaults_to_empty_list(self):
        @document_event("x.y", examples=None)
        async def handler(self, event):
            pass

        meta = getattr(handler, ASYNCAPI_EVENT_ATTR)
        assert meta["examples"] == []

    def test_decorator_returns_original_function(self):
        @document_event("x.y")
        async def handler(self, event):
            pass

        assert callable(handler)
        assert handler.__name__ == "handler"
