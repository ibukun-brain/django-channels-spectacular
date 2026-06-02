__version__ = "0.1.0"

from channels_spectacular.decorators import document_action, document_event
from channels_spectacular.generator import AsyncAPIGenerator

__all__ = [
    "document_action",
    "document_event",
    "AsyncAPIGenerator",
]
