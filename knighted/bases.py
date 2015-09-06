import asyncio
import logging
from abc import ABCMeta
from collections import defaultdict, namedtuple, OrderedDict
from itertools import chain
from weakref import WeakKeyDictionary, WeakSet
from functools import wraps

logger = logging.getLogger(__name__)


class Factory:

    def __init__(self, target):
        self.target = target

    def __call__(self, note, func=None):
        def decorate(func):
            self.target.factories[note] = asyncio.coroutine(func)
            return func
        if func:
            return decorate(func)
        return decorate


class FactoryMethod:
    """Decorator for func
    """

    def __get__(self, obj, objtype):
        target = obj or objtype
        return Factory(target)


class DataProxy:

    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __get__(self, obj, objtype):
        target = obj or objtype
        if not hasattr(target, self.name):
            setattr(target, self.name, self.type())
        return getattr(target, self.name)


class CloseHandler:
    """Closes mounted services
    """

    def __init__(self, injector):
        self.injector = injector
        self.registry = WeakKeyDictionary()

    def register(self, obj, reaction=None):
        """Register callbacks that should be thrown on close.
        """
        reaction = reaction or close_reaction
        reactions = self.registry.setdefault(obj, WeakSet())
        reactions.add(reaction)

    def unregister(self, obj, reaction=None):
        """Unregister callbacks that should not be thrown on close.
        """
        if reaction:
            reactions = self.registry.setdefault(obj, WeakSet())
            reactions.remove(reaction)
            if not reactions:
                self.registry.pop(obj, None)
        else:
            self.registry.pop(obj, None)

    @asyncio.coroutine
    def __call__(self):
        for obj, reactions in self.registry.items():
            for reaction in reactions:
                if asyncio.iscoroutinefunction(reaction):
                    yield from reaction(obj)
                else:
                    reaction(obj)
        self.injector.services.clear()


class Injector(metaclass=ABCMeta):
    """Collects dependencies and reads annotations to inject them.
    """

    factory = FactoryMethod()
    services = DataProxy('_services', OrderedDict)
    factories = DataProxy('_factories', OrderedDict)

    def __init__(self):
        self.services = self.__class__.services.copy()
        self.factories = self.__class__.factories.copy()
        self.reactions = defaultdict(WeakKeyDictionary)
        self.close = CloseHandler(self)

    @asyncio.coroutine
    def get(self, note):
        if note in self.services:
            return self.services[note]

        for fact, args in note_loop(note):
            if fact in self.factories:
                instance = yield from self.factories[fact](*args)
                logger.info('loaded service %s' % note)
                self.services[note] = instance
                return instance
        raise ValueError('%r is not defined' % note)

    @asyncio.coroutine
    def apply(self, *args, **kwargs):
        func, *args = args
        response = yield from self.partial(func)(*args, **kwargs)
        return response

    def partial(self, func):
        """Resolves lately dependancies.

        Returns:
            callable: the service partially resolved
        """

        @wraps(func)
        @asyncio.coroutine
        def wrapper(*args, **kwargs):
            if func in ANNOTATIONS:
                annotated = ANNOTATIONS[func]
                service_args, service_kwargs = [], {}
                for note in annotated.pos_notes:
                    service = yield from self.get(note)
                    service_args.append(service)
                for key, note in annotated.kw_notes.items():
                    service = yield from self.get(note)
                    service_kwargs[key] = service
                service_args.extend(args)
                service_kwargs.update(kwargs)
                return func(*service_args, **service_kwargs)
            logger.warn('%r is not annoted' % func)
            return func(*args, **kwargs)
        return wrapper


ANNOTATIONS = WeakKeyDictionary()

Annotation = namedtuple('Annotation', 'pos_notes kw_notes')


def close_reaction(obj):
    obj.close()


def annotate(*args, **kwargs):

    def decorate(func):
        ANNOTATIONS[func] = Annotation(args, kwargs)
        return func

    for arg in chain(args, kwargs.values()):
        if not isinstance(arg, str):
            raise ValueError('Notes must be strings')

    return decorate


def note_loop(note):
    args = note.split(':')
    results = []
    fact, *args = args
    results.append((fact, args))
    while args:
        suffix, *args = args
        fact = '%s:%s' % (fact, suffix)
        results.append((fact, args))
    for fact, args in sorted(results, reverse=True):
        yield fact, args
