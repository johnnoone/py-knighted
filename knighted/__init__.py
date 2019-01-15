from .bases import (
    Injector,
    annotate,
    attr,
    current_injector,
    AnnotationError,
    attr_lazy,
)
from ._version import get_versions


__version__ = get_versions()["version"]
del get_versions

__all__ = ["__version__", "Injector", "annotate", "attr", "current_injector"]
