"""Django settings for the chat example app."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "example-insecure-key-do-not-use-in-production"  # noqa: S105

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "channels",
    "channels_spectacular",
    "chat",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "chat_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

ASGI_APPLICATION = "chat_project.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# No Redis needed — in-memory layer is fine for a single-process example.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

CHANNELS_SPECTACULAR_SETTINGS = {
    "TITLE": "Chat & Notifications API",
    "VERSION": "1.0.0",
    "DESCRIPTION": (
        "Real-time WebSocket API.\n\n"
        "**Chat** — join rooms, send messages, and receive live broadcasts.\n\n"
        "**Notifications** — subscribe to per-user push notifications and "
        "mark them as read."
    ),
    "CHANNEL_PATH": "/ws/chat/",
    "SERVERS": None,
    "WS_HOST": None,
    "WS_PROTOCOL": None,
    "AUTH_QUERY_PARAM": "token",
    "AUTH_COOKIE_NAME": "access_token",
    "TRY_IT_OUT_ENABLED": True,
    "TRY_IT_OUT_EXPANDED": False,
}
