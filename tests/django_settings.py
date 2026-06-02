"""Minimal Django settings for running the test suite."""

SECRET_KEY = "test-secret-key-not-for-production"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "channels_spectacular",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
ROOT_URLCONF = "tests.urls"
