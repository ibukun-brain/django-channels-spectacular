# Installation

## Requirements

- Python 3.11+
- Django 4.2+
- Django Channels 4.0+
- PyYAML 6.0+

## Install

```bash
pip install django-channels-spectacular
# or
uv add django-channels-spectacular
```

### Optional: DRF serializer support

If you want to pass DRF `Serializer` subclasses as payload types, install
the `drf` extra:

```bash
pip install "django-channels-spectacular[drf]"
uv add "django-channels-spectacular[drf]"
```

### Optional: Pydantic support

Pydantic models are supported out of the box when `pydantic` is already
installed in your project no extra dependency is needed.

## Register the app

Add `channels_spectacular` to `INSTALLED_APPS` so Django can discover its
templates and management commands:

```python
INSTALLED_APPS = [
    "daphne" # make sure to add daphne at the very top
    ...
    "channels",
    "channels_spectacular",
]
```
