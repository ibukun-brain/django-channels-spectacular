from django.urls import path

from channels_spectacular.views import AsyncAPIDocView, AsyncAPISpecView
from tests.fixtures.sample_consumer import NotificationConsumer, SampleConsumer

urlpatterns = [
    path(
        "ws-docs/",
        AsyncAPIDocView.as_view(),
        name="asyncapi-doc",
    ),
    path(
        "ws-docs/asyncapi.yaml",
        AsyncAPISpecView.as_view(
            consumer=SampleConsumer,
            channel_path="/ws/sample/",
        ),
        name="asyncapi-spec",
    ),
    path(
        "ws-docs/multi.yaml",
        AsyncAPISpecView.as_view(
            consumers=[
                (SampleConsumer, "/ws/sample/"),
                (NotificationConsumer, "/ws/notifications/"),
            ],
        ),
        name="asyncapi-spec-multi",
    ),
]
