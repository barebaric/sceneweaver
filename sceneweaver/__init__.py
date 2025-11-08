"""SceneWeaver: A tool for creating videos from YAML specification files."""

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

from .app import main

__all__ = [
    "__version__",
    "main",
]
