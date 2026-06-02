#!/usr/bin/env python
"""Django's command-line utility for the chat example app."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it is installed and that you "
            "have activated the right virtual environment."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
