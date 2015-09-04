import asyncio
import logging
from abc import ABCMeta
from collections import namedtuple, OrderedDict
from itertools import chain

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


class DataStore:

    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __get__(self, obj, objtype):
        target = obj or objtype
        if not hasattr(target, self.name):
            setattr(target, self.name, self.type())
        return getattr(target, self.name)


class Injector(metaclass=ABCMeta):
    """Collects dependencies and reads annotations to inject them.
    """

    factory = FactoryMethod()
    services = DataStore('_services', OrderedDict)
    factories = DataStore('_factories', OrderedDict)

    def __init__(self):
        self.services = self.__class__.services.copy()
        self.factories = self.__class__.factories.copy()

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
    def inject(self, *args, **kwargs):
        func, *args = args
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
        logger.warn('%r is not annoted' % callable)
        return callable(*args, **kwargs)

    @staticmethod
    def close_on_exit(obj):
        """Mark object should be closed on exit
        """
        EXIT_OBJECTS.add(obj)

    def close(self):
        """Closes mounted services
        """
        flush = []
        for name, service in self.services.items():
            if service in EXIT_OBJECTS:
                service.close()
                logger.info('closed service %s', name)
                flush.append(name)
        for name in flush:
            self.services.pop(name, None)
            logger.info('flushed service %s', name)

ANNOTATIONS = {}

Annotation = namedtuple('Annotation', 'pos_notes kw_notes')


def annotate(*args, **kwargs):

    def decorate(func):
        ANNOTATIONS[func] = Annotation(args, kwargs)
        return func

    for arg in chain(args, kwargs.values()):
        if not isinstance(arg, str):
            raise ValueError('Notes must be strings')

    return decorate


EXIT_OBJECTS = set()


def close_all():
    for obj in EXIT_OBJECTS:
        logger.info('close %s', obj)
        obj.close()


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
