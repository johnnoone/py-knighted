from .bases import Injector, annotate
from ._version import get_versions

__all__ = ['Injector', 'annotate']
__version__ = get_versions()['version']
del get_versions

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
